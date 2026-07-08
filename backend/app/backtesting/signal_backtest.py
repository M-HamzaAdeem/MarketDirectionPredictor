"""Walk-forward backtest of the ICT signal pipeline (`build_signal`) over
real historical candles — PROJECT.md's "backtest before trusting signals"
requirement.

Reuses `build_signal()` and `resolve_signal()` completely unmodified, so a
backtested signal is built and graded by the exact same rules a live one
is — this module only supplies the historical windowing.

Avoiding lookahead bias is the entire point of a backtest: at each
simulated 15m candle close, the strategy may only see candles that would
actually have been closed by then. `_advance` maintains a monotonically
advancing pointer per timeframe (candles are ascending by close_time, and
simulated time only moves forward) so this stays O(n) instead of
re-filtering the whole history at every step.

At most one open signal is tracked at a time, mirroring the live ordering
in main.py's `candle_close_handlers` (`SignalTracker` resolves an existing
open signal before `SignalService` considers creating a new one from the
same candle) — see [[backtest-duplicate-signal-fix]] in decisions.md.
Earlier versions called `build_signal()` unconditionally at every step and
fast-forward-resolved each result using all remaining future candles in
one shot, which could append the same still-valid, rediscovered setup as
multiple separate "signals."
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.core.constants import Symbol
from app.feeds.base import Candle
from app.prediction.signal import Signal, SignalStatus
from app.prediction.signal_builder import build_signal
from app.prediction.signal_resolution import resolve_signal
from app.services.signal_service import CANDLE_WINDOW_1H, CANDLE_WINDOW_4H, CANDLE_WINDOW_15M
from app.services.signal_tracker import DEFAULT_EXPIRY


@dataclass(frozen=True, slots=True)
class SignalBacktestSummary:
    symbol: Symbol
    range_start: datetime | None
    range_end: datetime | None
    total_signals: int
    wins: int
    losses: int
    expired: int
    still_open: int
    win_rate: float
    avg_realized_rr: float


def run_signal_backtest(
    symbol: Symbol,
    candles_4h: list[Candle],
    candles_1h: list[Candle],
    candles_15m: list[Candle],
    expiry: timedelta = DEFAULT_EXPIRY,
    window_4h: int = CANDLE_WINDOW_4H,
    window_1h: int = CANDLE_WINDOW_1H,
    window_15m: int = CANDLE_WINDOW_15M,
) -> SignalBacktestSummary:
    """Every candle list must be closed candles in ascending open_time
    order, for the same symbol. Mirrors SignalService.on_candle_closed's
    live trigger: only evaluates at 15m candle closes. `window_*` default
    to the real live windows — overridable so tests can exercise the
    walk-forward/warmup logic with small fixtures instead of needing 60+/
    100+/20+ real candles."""
    resolved_signals: list[Signal] = []
    open_signal: Signal | None = None
    pointer_4h = pointer_1h = 0

    for i, candle in enumerate(candles_15m):
        as_of = candle.close_time
        pointer_4h = _advance(candles_4h, as_of, pointer_4h)
        pointer_1h = _advance(candles_1h, as_of, pointer_1h)

        # Mirrors SignalTracker: resolve a currently-open signal against
        # just this one new candle, exactly like the live path does,
        # rather than fast-forwarding through all remaining history.
        if open_signal is not None:
            outcome = resolve_signal(open_signal, candle, expiry)
            if outcome is not None:
                status, realized_rr = outcome
                resolved_signals.append(
                    replace(open_signal, status=status, closed_at=candle.close_time, realized_rr=realized_rr)
                )
                open_signal = None

        # Mirrors SignalService's get_open() guard: only ever consider
        # creating a new signal once none remains open.
        if open_signal is not None:
            continue

        window_4h_candles = candles_4h[max(0, pointer_4h - window_4h) : pointer_4h]
        window_1h_candles = candles_1h[max(0, pointer_1h - window_1h) : pointer_1h]
        window_15m_candles = candles_15m[max(0, i - window_15m + 1) : i + 1]

        has_warmup = (
            len(window_4h_candles) >= window_4h
            and len(window_1h_candles) >= window_1h
            and len(window_15m_candles) >= window_15m
        )
        if not has_warmup:
            continue  # not enough warmup history yet, same as a fresh live deployment

        open_signal = build_signal(symbol, window_4h_candles, window_1h_candles, window_15m_candles)

    if open_signal is not None:
        resolved_signals.append(open_signal)  # ran out of history before it resolved — still OPEN

    return _summarize(symbol, candles_15m, resolved_signals)


def _advance(candles: list[Candle], as_of: datetime, pointer: int) -> int:
    while pointer < len(candles) and candles[pointer].close_time <= as_of:
        pointer += 1
    return pointer


def _summarize(symbol: Symbol, candles_15m: list[Candle], signals: list[Signal]) -> SignalBacktestSummary:
    wins = sum(1 for s in signals if s.status == SignalStatus.WIN)
    losses = sum(1 for s in signals if s.status == SignalStatus.LOSS)
    expired = sum(1 for s in signals if s.status == SignalStatus.EXPIRED)
    still_open = sum(1 for s in signals if s.status == SignalStatus.OPEN)

    decided = wins + losses
    win_rate = round(wins / decided, 4) if decided else 0.0

    realized_rrs = [s.realized_rr for s in signals if s.status in (SignalStatus.WIN, SignalStatus.LOSS)]
    avg_realized_rr = round(sum(realized_rrs) / len(realized_rrs), 2) if realized_rrs else 0.0

    return SignalBacktestSummary(
        symbol=symbol,
        range_start=candles_15m[0].open_time if candles_15m else None,
        range_end=candles_15m[-1].close_time if candles_15m else None,
        total_signals=len(signals),
        wins=wins,
        losses=losses,
        expired=expired,
        still_open=still_open,
        win_rate=win_rate,
        avg_realized_rr=avg_realized_rr,
    )
