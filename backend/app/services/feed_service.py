"""Owns the feed lifecycle: connects the configured provider, routes ticks
to the candle aggregator, persists closed candles, and keeps an in-memory
latest-price cache for fast reads.

Thin orchestration only — the aggregation rules live in CandleAggregator
and persistence lives in CandleRepository, both tested independently.
"""

import asyncio
import logging

from app.core.config import Settings
from app.core.constants import Symbol
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.services.candle_aggregator import CandleAggregator
from app.storage.database import get_session_factory
from app.storage.repositories.candle_repository import CandleRepository

logger = logging.getLogger(__name__)


class FeedService:
    def __init__(self, provider: MarketDataProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._aggregator = CandleAggregator(settings.timeframes)
        self._latest_prices: dict[Symbol, Tick] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await self._provider.connect()
        self._task = asyncio.create_task(self._run())

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
                for candle in self._aggregator.ingest(tick):
                    await self._persist(candle)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Feed loop terminated unexpectedly")

    async def _persist(self, candle: Candle) -> None:
        async with get_session_factory()() as session:
            await CandleRepository(session).save(candle)
