"""Market structure detection: swing highs/lows and break-of-structure (BOS).

A swing high is a candle whose high is strictly the maximum within
`lookback` candles on each side (ties are not swings — an unambiguous peak
is required); a swing low is the mirror. BOS v1 is a simple rule: the
latest close breaking above the most recent swing high is bullish, below
the most recent swing low is bearish, otherwise the range holds (neutral).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.constants import Direction

DEFAULT_SWING_LOOKBACK = 2


class SwingKind(str, Enum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    timestamp: datetime
    price: float
    kind: SwingKind


def detect_swing_points(
    highs: list[float],
    lows: list[float],
    timestamps: list[datetime],
    lookback: int = DEFAULT_SWING_LOOKBACK,
) -> list[SwingPoint]:
    swings: list[SwingPoint] = []
    for i in range(lookback, len(highs) - lookback):
        window_highs = highs[i - lookback : i + lookback + 1]
        if highs[i] == max(window_highs) and window_highs.count(highs[i]) == 1:
            swings.append(SwingPoint(index=i, timestamp=timestamps[i], price=highs[i], kind=SwingKind.HIGH))

        window_lows = lows[i - lookback : i + lookback + 1]
        if lows[i] == min(window_lows) and window_lows.count(lows[i]) == 1:
            swings.append(SwingPoint(index=i, timestamp=timestamps[i], price=lows[i], kind=SwingKind.LOW))

    return swings


def detect_break_of_structure(swing_points: list[SwingPoint], latest_close: float) -> Direction:
    last_high = next((s for s in reversed(swing_points) if s.kind == SwingKind.HIGH), None)
    last_low = next((s for s in reversed(swing_points) if s.kind == SwingKind.LOW), None)

    if last_high is not None and latest_close > last_high.price:
        return Direction.BULLISH
    if last_low is not None and latest_close < last_low.price:
        return Direction.BEARISH
    return Direction.NEUTRAL


# --- ICT-style structure: sweeps, CHoCH/BOS, and derived "weak" liquidity ---
#
# A swing point starts as untested ("weak" — resting liquidity). It is
# resolved the first time a later candle interacts with it, one of two ways:
#   - Sweep: a candle's wick passes the level but its CLOSE stays on the near
#     side ("no close through it") — the classic liquidity grab/rejection.
#   - Structure break: a candle CLOSES beyond the level — a genuine BOS
#     (continuation of the prevailing trend) or CHoCH (the first break
#     against it, signaling a possible reversal).
# "Weak" points are derived (points touched by neither event yet), not
# stored as mutable state, to stay consistent with this module's pure,
# recomputed-from-window style.


@dataclass(frozen=True, slots=True)
class Sweep:
    swept_point: SwingPoint
    sweep_index: int
    sweep_timestamp: datetime


class StructureEvent(str, Enum):
    BOS = "bos"
    CHOCH = "choch"


@dataclass(frozen=True, slots=True)
class StructureBreak:
    event: StructureEvent
    direction: Direction
    broken_point: SwingPoint
    break_index: int
    break_timestamp: datetime


def detect_sweeps(
    swing_points: list[SwingPoint],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    timestamps: list[datetime],
) -> list[Sweep]:
    """The first candle after each swing point that wicks through it without
    closing through it. A candle that closes through instead is a structure
    break, not a sweep — scanning for this point stops there either way,
    since only its first interaction matters."""
    sweeps: list[Sweep] = []
    for point in swing_points:
        for i in range(point.index + 1, len(highs)):
            if point.kind == SwingKind.HIGH:
                if closes[i] > point.price:
                    break
                if highs[i] > point.price:
                    sweeps.append(Sweep(point, i, timestamps[i]))
                    break
            else:
                if closes[i] < point.price:
                    break
                if lows[i] < point.price:
                    sweeps.append(Sweep(point, i, timestamps[i]))
                    break

    return sweeps


def detect_structure_breaks(
    swing_points: list[SwingPoint],
    closes: list[float],
    timestamps: list[datetime],
) -> list[StructureBreak]:
    """Walks swing points in open_time order, tracking the prevailing trend.
    A close beyond a swing point in the same direction as the current trend
    is a BOS (continuation); the first close beyond it against the current
    trend is a CHoCH (reversal trigger, which becomes the new trend)."""
    breaks: list[StructureBreak] = []
    trend: Direction = Direction.NEUTRAL

    for point in swing_points:
        for i in range(point.index + 1, len(closes)):
            if point.kind == SwingKind.HIGH and closes[i] > point.price:
                event = StructureEvent.BOS if trend == Direction.BULLISH else StructureEvent.CHOCH
                breaks.append(StructureBreak(event, Direction.BULLISH, point, i, timestamps[i]))
                trend = Direction.BULLISH
                break
            if point.kind == SwingKind.LOW and closes[i] < point.price:
                event = StructureEvent.BOS if trend == Direction.BEARISH else StructureEvent.CHOCH
                breaks.append(StructureBreak(event, Direction.BEARISH, point, i, timestamps[i]))
                trend = Direction.BEARISH
                break

    return breaks


def weak_points(
    swing_points: list[SwingPoint],
    sweeps: list[Sweep],
    breaks: list[StructureBreak],
) -> list[SwingPoint]:
    """Swing points touched by neither a sweep nor a structure break yet —
    still-resting, untested liquidity."""
    tested_indices = {sweep.swept_point.index for sweep in sweeps}
    tested_indices |= {structure_break.broken_point.index for structure_break in breaks}
    return [point for point in swing_points if point.index not in tested_indices]
