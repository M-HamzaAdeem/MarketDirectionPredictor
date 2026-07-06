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
