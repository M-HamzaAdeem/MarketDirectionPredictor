"""Owns the feed lifecycle: connects the configured provider, routes ticks
to the candle aggregator, persists closed candles, keeps an in-memory
latest-price cache for fast reads, broadcasts every tick, and — after
persisting a closed candle — runs it through each registered
CandleCloseHandler (PredictionService, SignalTracker, SignalService today;
adding a fourth reaction to a candle close means adding it to the handler
list at composition time in main.py, not touching this class).

Thin orchestration only — the aggregation rules live in CandleAggregator,
persistence lives in CandleRepository; each handler is tested independently.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.constants import FeedStatus, Symbol
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.services.broadcast_service import BroadcastService
from app.services.candle_aggregator import CandleAggregator
from app.services.candle_close_handler import CandleCloseHandler
from app.storage.repositories.candle_repository import CandleRepository

logger = logging.getLogger(__name__)


class FeedService:
    def __init__(
        self,
        provider: MarketDataProvider,
        settings: Settings,
        broadcaster: BroadcastService,
        session_factory: async_sessionmaker[AsyncSession],
        candle_close_handlers: list[CandleCloseHandler],
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._broadcaster = broadcaster
        self._session_factory = session_factory
        self._candle_close_handlers = candle_close_handlers
        self._aggregator = CandleAggregator(settings.timeframes)
        self._latest_prices: dict[Symbol, Tick] = {}
        self._task: asyncio.Task[None] | None = None
        # Only MockMarketDataProvider exists today, so status is fixed;
        # revisit once a provider that can actually degrade/disconnect exists.
        self.status: FeedStatus = FeedStatus.MOCK

    async def start(self) -> None:
        await self._provider.connect()
        self._task = asyncio.create_task(self._run())
        await self._broadcaster.broadcast_feed_status(self.status)

    async def stop(self) -> None:
        await self._provider.disconnect()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def latest_price(self, symbol: Symbol) -> Tick | None:
        return self._latest_prices.get(symbol)

    async def _run(self) -> None:
        try:
            async for tick in self._provider.stream_ticks(self._settings.symbols):
                self._latest_prices[tick.symbol] = tick
                await self._broadcaster.broadcast_price(tick)
                for candle in self._aggregator.ingest(tick):
                    await self._handle_closed_candle(candle)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Feed loop terminated unexpectedly")

    async def _handle_closed_candle(self, candle: Candle) -> None:
        # Isolated from _run's loop: a persistence or handler failure on one
        # candle must not take down tick ingestion/price broadcasting.
        try:
            await self._persist(candle)
            for handler in self._candle_close_handlers:
                await handler.on_candle_closed(candle)
        except Exception:
            logger.exception("Failed handling closed candle %s/%s", candle.symbol, candle.timeframe)

    async def _persist(self, candle: Candle) -> None:
        async with self._session_factory() as session:
            await CandleRepository(session).save(candle)
