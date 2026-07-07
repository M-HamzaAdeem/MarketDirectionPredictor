"""Watches OPEN signals forward in time against incoming candles of their
own entry_timeframe, resolving each to WIN (target hit first), LOSS (stop
hit first), or EXPIRED (neither hit within the timeout window). This is
what turns a Signal from a plan into a graded, auditable outcome — the
"end result" PROJECT.md requires alongside every signal's reasoning.

If a single candle's range touches BOTH the stop and the target (only
possible at candle-level granularity, since v1 has no tick-by-tick replay
for already-closed candles), the stop is assumed to have been hit first —
the conservative, worst-case read, consistent with never overstating a win.
"""

import logging
from dataclasses import replace
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import Direction
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus
from app.services.broadcast_service import BroadcastService
from app.storage.repositories.signal_repository import SignalRepository

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY = timedelta(days=5)


class SignalTracker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        broadcaster: BroadcastService,
        expiry: timedelta = DEFAULT_EXPIRY,
    ) -> None:
        self._session_factory = session_factory
        self._broadcaster = broadcaster
        self._expiry = expiry

    async def on_candle_closed(self, candle: Candle) -> None:
        resolved: list[Signal] = []

        async with self._session_factory() as session:
            repository = SignalRepository(session)
            open_signals = await repository.get_open(candle.symbol)
            for signal in open_signals:
                if signal.entry_timeframe != candle.timeframe:
                    continue
                outcome = self._resolve(signal, candle)
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

    def _resolve(self, signal: Signal, candle: Candle) -> tuple[SignalStatus, float] | None:
        if self._stop_hit(signal, candle):
            return SignalStatus.LOSS, -1.0
        if self._target_hit(signal, candle):
            return SignalStatus.WIN, signal.risk_reward
        if candle.close_time - signal.opened_at > self._expiry:
            return SignalStatus.EXPIRED, 0.0
        return None

    def _stop_hit(self, signal: Signal, candle: Candle) -> bool:
        if signal.direction == Direction.BULLISH:
            return candle.low <= signal.stop
        return candle.high >= signal.stop

    def _target_hit(self, signal: Signal, candle: Candle) -> bool:
        if signal.direction == Direction.BULLISH:
            return candle.high >= signal.target
        return candle.low <= signal.target
