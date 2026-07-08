"""Pure WIN/LOSS/EXPIRED resolution of a Signal against a new candle of its
own entry_timeframe — shared by the live SignalTracker and the backtest
engine, so backtested outcomes are graded by the exact same rule as live
ones, not a separate reimplementation that could quietly drift.

If a single candle's range touches BOTH the stop and the target (only
possible at candle-level granularity, since v1 has no tick-by-tick replay
for already-closed candles), the stop is assumed to have been hit first —
the conservative, worst-case read, consistent with never overstating a win.
"""

from datetime import timedelta

from app.core.constants import Direction
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus


def resolve_signal(signal: Signal, candle: Candle, expiry: timedelta) -> tuple[SignalStatus, float] | None:
    """Returns `(status, realized_rr)` once resolved, or `None` if the
    signal is still open against this candle."""
    if _stop_hit(signal, candle):
        return SignalStatus.LOSS, -1.0
    if _target_hit(signal, candle):
        return SignalStatus.WIN, signal.risk_reward
    if candle.close_time - signal.opened_at > expiry:
        return SignalStatus.EXPIRED, 0.0
    return None


def _stop_hit(signal: Signal, candle: Candle) -> bool:
    if signal.direction == Direction.BULLISH:
        return candle.low <= signal.stop
    return candle.high >= signal.stop


def _target_hit(signal: Signal, candle: Candle) -> bool:
    if signal.direction == Direction.BULLISH:
        return candle.high >= signal.target
    return candle.low <= signal.target
