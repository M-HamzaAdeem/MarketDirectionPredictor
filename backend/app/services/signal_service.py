"""Generates new ICT signals whenever a fresh 15m candle closes: fetches
the 4H/1H/15m candle windows for the candle's symbol, runs them through
build_signal(), and persists + broadcasts anything produced.

Only ever acts on 15m candle closes — that's the signal builder's entry
confirmation timeframe (see prediction/signal_builder.py); a 4H or 1H
close doesn't need to re-trigger this, since bias/setup only matter once
an actual entry tap is confirmed on 15m.

A tap candle already used to open a signal is never reused to open
another one, even after that signal resolves — otherwise the same stale
setup can rapid-fire reopen on every subsequent 15m close for as long as
it remains inside the rolling 15m window, the instant its previous
instance closes. See [[backtest-rapid-reopen-fix]] in decisions.md (found
via the backtest engine, but the same gap applies here).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import Timeframe
from app.feeds.base import Candle
from app.prediction.signal_builder import build_signal, eligible_entry_candles
from app.services.broadcast_service import BroadcastService
from app.storage.models import CandleColumns, CandleORM, SignalColumns, SignalORM
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.signal_repository import SignalRepository

# Public, not underscore-prefixed: app/backtesting/signal_backtest.py is a
# second real reader, replaying build_signal() with these exact windows so
# backtested behavior can't silently diverge from live.
CANDLE_WINDOW_4H = 60
CANDLE_WINDOW_1H = 100
CANDLE_WINDOW_15M = 20


class SignalService:
    """`candle_model`/`signal_model` default to the Twelve Data pipeline's
    tables; pass the TradingView equivalents to run this same logic
    against that fully separate pipeline instead."""

    def __init__(
        self,
        broadcaster: BroadcastService,
        session_factory: async_sessionmaker[AsyncSession],
        candle_model: type[CandleColumns] = CandleORM,
        signal_model: type[SignalColumns] = SignalORM,
    ) -> None:
        self._broadcaster = broadcaster
        self._session_factory = session_factory
        self._candle_model = candle_model
        self._signal_model = signal_model

    async def on_candle_closed(self, candle: Candle) -> None:
        if candle.timeframe != Timeframe.M15:
            return

        async with self._session_factory() as session:
            signal_repository = SignalRepository(session, model=self._signal_model)
            # One open signal per symbol at a time: build_signal() re-derives
            # the same still-open setup on every 15m close for as long as its
            # 1H bias/structure hasn't changed, so without this guard the
            # same setup gets saved again as a "new" duplicate signal.
            if await signal_repository.get_open(candle.symbol):
                return

            candle_repository = CandleRepository(session, model=self._candle_model)
            candles_4h = await candle_repository.get_recent(candle.symbol, Timeframe.H4, limit=CANDLE_WINDOW_4H)
            candles_1h = await candle_repository.get_recent(candle.symbol, Timeframe.H1, limit=CANDLE_WINDOW_1H)
            candles_15m = await candle_repository.get_recent(
                candle.symbol, Timeframe.M15, limit=CANDLE_WINDOW_15M
            )

            # Never let _check_entry rediscover a tap candle that already
            # opened a signal for this symbol, even one that has since
            # resolved — see the module docstring.
            most_recent = await signal_repository.get_recent(candle.symbol, limit=1)
            last_opened_at = most_recent[0].opened_at if most_recent else None
            candles_15m = eligible_entry_candles(candles_15m, last_opened_at)

            signal = build_signal(candle.symbol, candles_4h, candles_1h, candles_15m)
            if signal is None:
                return

            saved = await signal_repository.save(signal)

        await self._broadcaster.broadcast_signal(saved)
