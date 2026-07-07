"""Owns the feed lifecycle: connects the configured provider, routes ticks
to the candle aggregator, persists closed candles, keeps an in-memory
latest-price cache for fast reads, broadcasts every tick, and — after
persisting a closed candle — runs it through each registered
CandleCloseHandler (PredictionService, SignalTracker, SignalService today;
adding a fourth reaction to a candle close means adding it to the handler
list at composition time in main.py, not touching this class).

Thin orchestration only — the aggregation rules live in CandleAggregator,
persistence lives in CandleRepository; each handler is tested independently.

If the provider's tick stream ends or raises (connection drop, transient
provider failure), `_run` doesn't give up — it reconnects with exponential
backoff, broadcasting FeedStatus.DISCONNECTED for the duration and back to
the provider's nominal status once ticks resume. `MockMarketDataProvider`
never actually fails today, but a real feed adapter will, and this is the
seam that handles it without every provider needing its own retry logic.
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

_INITIAL_RECONNECT_DELAY_SECONDS = 1.0
_MAX_RECONNECT_DELAY_SECONDS = 30.0
_RECONNECT_BACKOFF_MULTIPLIER = 2.0


class FeedService:
    def __init__(
        self,
        provider: MarketDataProvider,
        settings: Settings,
        broadcaster: BroadcastService,
        session_factory: async_sessionmaker[AsyncSession],
        candle_close_handlers: list[CandleCloseHandler],
        nominal_status: FeedStatus = FeedStatus.MOCK,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._broadcaster = broadcaster
        self._session_factory = session_factory
        self._candle_close_handlers = candle_close_handlers
        self._aggregator = CandleAggregator(settings.timeframes)
        self._latest_prices: dict[Symbol, Tick] = {}
        self._task: asyncio.Task[None] | None = None
        # The status the feed reports when the provider is streaming
        # normally — MOCK for MockMarketDataProvider, LIVE for a real feed.
        # `status` itself moves to DISCONNECTED while reconnecting and back
        # to this once the stream recovers.
        self._nominal_status = nominal_status
        self.status: FeedStatus = nominal_status

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
        delay = _INITIAL_RECONNECT_DELAY_SECONDS
        reconnecting = False

        while True:
            try:
                if reconnecting:
                    await self._provider.disconnect()
                    await self._provider.connect()

                async for tick in self._provider.stream_ticks(self._settings.symbols):
                    # Backoff only resets once a tick actually arrives, not
                    # as soon as connect() succeeds — a provider that
                    # reconnects but yields no data isn't actually healthy
                    # from this pipeline's perspective (no ticks means no
                    # candles), so it's correct for backoff to keep growing
                    # (up to the cap) through repeated empty sessions.
                    if reconnecting:
                        reconnecting = False
                        delay = _INITIAL_RECONNECT_DELAY_SECONDS
                        await self._set_status(self._nominal_status)

                    self._latest_prices[tick.symbol] = tick
                    await self._broadcaster.broadcast_price(tick)
                    for candle in self._aggregator.ingest(tick):
                        await self._handle_closed_candle(candle)

                # The provider's contract is to stream until disconnected;
                # the generator ending on its own is an unexpected
                # disruption too, not a clean shutdown (stop() cancels the
                # task instead of waiting for the generator to return).
                # Caught immediately below like any other stream failure.
                raise RuntimeError("Tick stream ended unexpectedly")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Feed stream failed; reconnecting in %.1fs", delay)
                reconnecting = True
                await self._set_status(FeedStatus.DISCONNECTED)
                await asyncio.sleep(delay)
                delay = min(delay * _RECONNECT_BACKOFF_MULTIPLIER, _MAX_RECONNECT_DELAY_SECONDS)

    async def _set_status(self, status: FeedStatus) -> None:
        if status == self.status:
            return
        self.status = status
        await self._broadcaster.broadcast_feed_status(status)

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
