"""Watches OPEN signals forward in time against incoming candles of their
own entry_timeframe, resolving each to WIN/LOSS/EXPIRED via
`prediction/signal_resolution.py`'s pure `resolve_signal` — the live path
here just fetches OPEN signals, calls that shared function, and persists +
broadcasts the outcome. This is what turns a Signal from a plan into a
graded, auditable outcome — the "end result" PROJECT.md requires alongside
every signal's reasoning. The backtest engine (`app/backtesting/`) calls
the same `resolve_signal` against historical candles, so backtested
outcomes are graded identically to live ones."""

import logging
from dataclasses import replace
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.feeds.base import Candle
from app.prediction.signal import Signal
from app.prediction.signal_resolution import resolve_signal
from app.services.broadcast_service import BroadcastService
from app.storage.models import SignalColumns, SignalORM
from app.storage.repositories.signal_repository import SignalRepository

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY = timedelta(days=5)


class SignalTracker:
    """`signal_model` defaults to the Twelve Data pipeline's table; pass
    `signal_model=TradingViewSignalORM` to run this same logic against
    that fully separate pipeline instead."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        broadcaster: BroadcastService,
        expiry: timedelta = DEFAULT_EXPIRY,
        signal_model: type[SignalColumns] = SignalORM,
    ) -> None:
        self._session_factory = session_factory
        self._broadcaster = broadcaster
        self._expiry = expiry
        self._signal_model = signal_model

    async def on_candle_closed(self, candle: Candle) -> None:
        resolved: list[Signal] = []

        async with self._session_factory() as session:
            repository = SignalRepository(session, model=self._signal_model)
            open_signals = await repository.get_open(candle.symbol)
            for signal in open_signals:
                if signal.entry_timeframe != candle.timeframe:
                    continue
                outcome = resolve_signal(signal, candle, self._expiry)
                if outcome is not None:
                    status, realized_rr = outcome
                    await repository.update_outcome(signal.id, status, candle.close_time, realized_rr)
                    resolved.append(
                        replace(signal, status=status, closed_at=candle.close_time, realized_rr=realized_rr)
                    )

        for signal in resolved:
            # Each broadcast is isolated: a failure on one resolved signal
            # (already persisted) must not cost the rest their notification.
            try:
                await self._broadcaster.broadcast_signal(signal)
            except Exception:
                logger.exception("Failed to broadcast resolution for signal %s", signal.id)
