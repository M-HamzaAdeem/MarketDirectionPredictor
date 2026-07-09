"""Owns the TradingView pipeline's lifecycle: the poll-based sibling of
FeedService. Polls TradingViewClient on an interval instead of consuming a
persistent tick stream (TradingView's unofficial protocol has no such
thing — see tradingview_client.py), diffs the returned bars against what's
already stored, persists any genuinely new closed candles, and runs each
through the same CandleCloseHandler protocol FeedService uses — but with
its own, fully separate handler instances (own PredictionService,
SignalTracker, SignalService, pointed at the TradingView tables) so this
pipeline never touches Twelve Data's data.

Does NOT use CandleAggregator: TradingView already hands back
pre-aggregated OHLC bars per poll, so there are no raw ticks to bucket.

Two gotchas specific to polling (absent from the tick-driven path):

1. `CandleRepository.save_many_if_missing` doesn't report which rows were
   actually new, but this service needs exactly that (to know which bars
   are genuine "candle closed" events worth running handlers for) — so
   each poll diffs the fetched batch against `get_recent`'s known
   open_times *before* persisting, rather than relying on the repository.

2. A single poll cycle can discover newly-closed 4H, 1H, and 15m bars
   simultaneously (e.g. after downtime, or at a genuine 4H boundary).
   SignalService reads the 4H/1H windows the moment a 15m candle closes,
   so those coarser candles must already be persisted first, or it builds
   against stale data — a hazard the tick-driven path never has, since
   CandleAggregator only ever emits one tick's worth of closes at a time.
   Fixed by always polling coarsest-to-finest per symbol (_ordered_timeframes).
"""

import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from websockets.exceptions import WebSocketException

from app.core.config import Settings
from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, Tick
from app.feeds.tradingview_client import TradingViewClient
from app.services.broadcast_service import BroadcastService
from app.services.candle_close_handler import CandleCloseHandler
from app.storage.models import CandleColumns, TradingViewCandleORM
from app.storage.repositories.candle_repository import CandleRepository

logger = logging.getLogger(__name__)

# The expected external-failure surface for a TradingView fetch: OSError
# covers low-level connection failures (refused, DNS), WebSocketException
# covers the handshake/protocol layer, TimeoutError is TradingViewClient's
# own explicit read-timeout, SQLAlchemyError covers a transient SQLite
# lock. Mirrors FeedService's _EXPECTED_BACKFILL_ERRORS convention.
_EXPECTED_BACKFILL_ERRORS = (OSError, WebSocketException, TimeoutError, SQLAlchemyError)

_BACKFILL_CANDLE_COUNT = 100
# Small relative to _BACKFILL_CANDLE_COUNT on purpose: polling only needs
# enough overlap to catch bars closed since the last cycle, not the full
# history — re-fetching 100 bars every cycle for every symbol/timeframe
# against an unofficial, rate-limit-unknown endpoint would be needlessly
# heavy. 20 gives comfortable headroom for a short outage/backoff spell on
# the finest configured timeframe (M1: ~20 minutes of gap coverage)
# without going that heavy. KNOWN LIMITATION, accepted for v1: since each
# poll only ever asks for the most recent _POLL_FETCH_COUNT bars (no
# gap-detection against elapsed wall-clock time, unlike the one-time
# startup backfill), a genuine outage longer than this window silently
# loses the bars that closed during the excess — they are never
# re-fetched until the next full app restart re-runs backfill(). See
# TD-9 in tech-debt.md for the documented remediation (compute the count
# needed from elapsed time since the last successful poll, mirroring the
# handover doc's own "fetch only the missing gap" guidance).
_POLL_FETCH_COUNT = 20

_INITIAL_BACKOFF_DELAY_SECONDS = 1.0
_MAX_BACKOFF_DELAY_SECONDS = 30.0
_BACKOFF_MULTIPLIER = 2.0

# Coarsest-to-finest: see gotcha #2 in the module docstring.
_TIMEFRAME_ORDER = [Timeframe.H4, Timeframe.H1, Timeframe.M15, Timeframe.M5, Timeframe.M1]


def _ordered_timeframes(configured: list[Timeframe]) -> list[Timeframe]:
    configured_set = set(configured)
    return [timeframe for timeframe in _TIMEFRAME_ORDER if timeframe in configured_set]


def _split_forming(candles: list[Candle]) -> tuple[list[Candle], Candle | None]:
    """TradingView's last returned bar is always still-forming/provisional
    — never persisted as closed history. See tradingview_client.py."""
    if not candles:
        return [], None
    return candles[:-1], candles[-1]


class TradingViewFeedService:
    def __init__(
        self,
        client: TradingViewClient,
        settings: Settings,
        broadcaster: BroadcastService,
        session_factory: async_sessionmaker[AsyncSession],
        candle_close_handlers: list[CandleCloseHandler],
        poll_interval_seconds: float,
        candle_model: type[CandleColumns] = TradingViewCandleORM,
    ) -> None:
        self._client = client
        self._settings = settings
        self._broadcaster = broadcaster
        self._session_factory = session_factory
        self._candle_close_handlers = candle_close_handlers
        self._poll_interval_seconds = poll_interval_seconds
        self._candle_model = candle_model
        self._latest_prices: dict[Symbol, Tick] = {}
        self._task: asyncio.Task[None] | None = None
        self.status: FeedStatus = FeedStatus.LIVE

    async def backfill(self) -> None:
        async with self._session_factory() as session:
            repository = CandleRepository(session, model=self._candle_model)
            for symbol in self._settings.symbols:
                for timeframe in self._settings.timeframes:
                    await self._backfill_one(repository, symbol, timeframe)

    async def _backfill_one(self, repository: CandleRepository, symbol: Symbol, timeframe: Timeframe) -> None:
        try:
            existing = await repository.get_recent(symbol, timeframe, limit=_BACKFILL_CANDLE_COUNT)
            if len(existing) >= _BACKFILL_CANDLE_COUNT:
                return
            fetched = await self._client.fetch_candles(symbol, timeframe, _BACKFILL_CANDLE_COUNT)
            closed, _forming = _split_forming(fetched)
            await repository.save_many_if_missing(closed)
        except _EXPECTED_BACKFILL_ERRORS:
            logger.exception("TradingView historical backfill failed for %s/%s", symbol.value, timeframe.value)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        await self._broadcaster.broadcast_feed_status(self.status)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def latest_price(self, symbol: Symbol) -> Tick | None:
        return self._latest_prices.get(symbol)

    async def _run(self) -> None:
        delay = _INITIAL_BACKOFF_DELAY_SECONDS
        backing_off = False

        while True:
            try:
                for symbol in self._settings.symbols:
                    for timeframe in _ordered_timeframes(self._settings.timeframes):
                        await self._poll_one(symbol, timeframe)

                if backing_off:
                    backing_off = False
                    delay = _INITIAL_BACKOFF_DELAY_SECONDS
                    await self._set_status(FeedStatus.LIVE)

                await asyncio.sleep(self._poll_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("TradingView poll cycle failed; retrying in %.1fs", delay)
                backing_off = True
                await self._set_status(FeedStatus.DISCONNECTED)
                await asyncio.sleep(delay)
                delay = min(delay * _BACKOFF_MULTIPLIER, _MAX_BACKOFF_DELAY_SECONDS)

    async def _set_status(self, status: FeedStatus) -> None:
        if status == self.status:
            return
        self.status = status
        await self._broadcaster.broadcast_feed_status(status)

    async def _poll_one(self, symbol: Symbol, timeframe: Timeframe) -> None:
        fetched = await self._client.fetch_candles(symbol, timeframe, _POLL_FETCH_COUNT)
        if not fetched:
            return

        closed, forming = _split_forming(fetched)

        if forming is not None:
            tick = Tick(symbol=symbol, price=forming.close, timestamp=forming.close_time, volume=0.0)
            self._latest_prices[symbol] = tick
            await self._broadcaster.broadcast_price(tick)

        if not closed:
            return

        async with self._session_factory() as session:
            repository = CandleRepository(session, model=self._candle_model)
            existing = await repository.get_recent(symbol, timeframe, limit=_POLL_FETCH_COUNT)
            known_open_times = {candle.open_time for candle in existing}
            newly_closed = sorted(
                (candle for candle in closed if candle.open_time not in known_open_times),
                key=lambda candle: candle.open_time,
            )
            # Persists the whole fetched window (closed), not just
            # newly_closed -- save_many_if_missing's ON CONFLICT DO NOTHING
            # makes re-inserting already-known rows a harmless no-op, so
            # this also self-heals any row that (for whatever reason)
            # exists in `closed` but wasn't caught by known_open_times.
            await repository.save_many_if_missing(closed)

        for candle in newly_closed:
            await self._handle_closed_candle(candle)

    async def _handle_closed_candle(self, candle: Candle) -> None:
        # Isolated per candle: one handler's failure on one candle must not
        # stop the rest of this cycle's newly-closed candles from being
        # processed (mirrors FeedService._handle_closed_candle).
        try:
            for handler in self._candle_close_handlers:
                await handler.on_candle_closed(candle)
        except Exception:
            logger.exception("Failed handling closed TradingView candle %s/%s", candle.symbol, candle.timeframe)
