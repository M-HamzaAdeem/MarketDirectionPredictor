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
the provider's nominal status once ticks resume. There is deliberately no
automatic fallback to the mock feed here: a real provider failing must be
loud and visible (surfaced as DISCONNECTED, then reconnected), not
silently masked by synthetic data written into the same candles table as
real history — see [[remove-mock-auto-fallback]] in decisions.md.
`MockMarketDataProvider` never actually fails today, but a real feed
adapter will, and this reconnect loop is the seam that handles it without
every provider needing its own retry logic.

`backfill()` fetches and persists missing historical candles for every
configured symbol/timeframe via the provider's `fetch_history()` before
`start()` begins live streaming — without it, a real feed would need real
hours/days of live candles to accumulate before predictions or ICT signals
could run at all (see decisions.md).
"""

import asyncio
import logging

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.services.broadcast_service import BroadcastService
from app.services.candle_aggregator import CandleAggregator
from app.services.candle_close_handler import CandleCloseHandler
from app.storage.repositories.candle_repository import CandleRepository

logger = logging.getLogger(__name__)

# The expected external-failure surface for a single symbol/timeframe's
# backfill: httpx.HTTPError covers both network-level failures (timeout,
# connection refused) and non-2xx responses; RuntimeError is how
# TwelveDataProvider signals a provider-level API error in its response
# body; KeyError/ValueError cover an unmapped symbol/timeframe or a
# malformed response row (bad datetime format, missing field);
# SQLAlchemyError covers a transient SQLite lock from concurrent access by
# the live feed. Anything outside this set (e.g. an AttributeError from a
# real coding bug) is deliberately allowed to propagate rather than being
# silently absorbed as if it were one of these expected cases.
_EXPECTED_BACKFILL_ERRORS = (httpx.HTTPError, RuntimeError, KeyError, ValueError, SQLAlchemyError)

_INITIAL_RECONNECT_DELAY_SECONDS = 1.0
_MAX_RECONNECT_DELAY_SECONDS = 30.0
_RECONNECT_BACKOFF_MULTIPLIER = 2.0
_BACKFILL_CANDLE_COUNT = 100


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
        # `status` moves to DISCONNECTED while reconnecting and back to
        # `self._provider.nominal_status` (read live, not cached) once the
        # stream recovers.
        self.status: FeedStatus = provider.nominal_status

    async def backfill(self) -> None:
        async with self._session_factory() as session:
            repository = CandleRepository(session)
            for symbol in self._settings.symbols:
                for timeframe in self._settings.timeframes:
                    await self._backfill_one(repository, symbol, timeframe)

    async def _backfill_one(self, repository: CandleRepository, symbol: Symbol, timeframe: Timeframe) -> None:
        try:
            existing = await repository.get_recent(symbol, timeframe, limit=_BACKFILL_CANDLE_COUNT)
            if len(existing) >= _BACKFILL_CANDLE_COUNT:
                return
            candles = await self._provider.fetch_history(symbol, timeframe, _BACKFILL_CANDLE_COUNT)
            await repository.save_many_if_missing(candles)
        except _EXPECTED_BACKFILL_ERRORS:
            # One symbol/timeframe failing to backfill (rate limit, transient
            # network error, unsupported pair) shouldn't stop the rest or
            # abort startup — it just starts that pair cold, same as before
            # this feature existed. A genuine coding bug outside this set
            # (e.g. AttributeError) is deliberately not caught here — see
            # _EXPECTED_BACKFILL_ERRORS.
            logger.exception("Historical backfill failed for %s/%s", symbol.value, timeframe.value)

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
                        await self._set_status(self._provider.nominal_status)

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
