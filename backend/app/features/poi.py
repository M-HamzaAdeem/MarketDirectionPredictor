"""Points of Interest (POI): zones where price is expected to react because
smart money is presumed to have entered orders there.

Two types, per project convention:
  - Order Block: the last opposing-color candle before an impulsive move
    (impulsive = range clearly exceeding recent ATR). A bullish OB is a
    demand zone (support); a bearish OB is a supply zone (resistance).
  - Fair Value Gap (FVG): the classic 3-candle imbalance, where candle 1's
    high/low doesn't overlap candle 3's low/high, leaving a gap price
    often returns to fill.
"""

from dataclasses import dataclass
from datetime import datetime

from app.core.constants import Direction

DEFAULT_IMPULSE_ATR_MULTIPLIER = 1.5


@dataclass(frozen=True, slots=True)
class OrderBlock:
    index: int
    timestamp: datetime
    direction: Direction  # BULLISH = demand zone, BEARISH = supply zone
    low: float
    high: float
    impulse_index: int


@dataclass(frozen=True, slots=True)
class FairValueGap:
    index: int  # index of the third (gap-completing) candle
    timestamp: datetime
    direction: Direction
    low: float
    high: float


def detect_order_blocks(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    atr: list[float | None],
    timestamps: list[datetime],
    impulse_atr_multiplier: float = DEFAULT_IMPULSE_ATR_MULTIPLIER,
) -> list[OrderBlock]:
    order_blocks: list[OrderBlock] = []

    for i in range(1, len(closes)):
        candle_atr = atr[i]
        if candle_atr is None or (highs[i] - lows[i]) < impulse_atr_multiplier * candle_atr:
            continue

        if closes[i] > opens[i]:
            impulse_direction = Direction.BULLISH
        elif closes[i] < opens[i]:
            impulse_direction = Direction.BEARISH
        else:
            continue  # doji: no clear impulse direction

        opposing_index = _find_last_opposing_candle(opens, closes, i, impulse_direction)
        if opposing_index is not None:
            order_blocks.append(
                OrderBlock(
                    index=opposing_index,
                    timestamp=timestamps[opposing_index],
                    direction=impulse_direction,
                    low=lows[opposing_index],
                    high=highs[opposing_index],
                    impulse_index=i,
                )
            )

    return order_blocks


def _find_last_opposing_candle(
    opens: list[float], closes: list[float], impulse_index: int, impulse_direction: Direction
) -> int | None:
    for j in range(impulse_index - 1, -1, -1):
        is_bearish_candle = closes[j] < opens[j]
        is_bullish_candle = closes[j] > opens[j]
        if impulse_direction == Direction.BULLISH and is_bearish_candle:
            return j
        if impulse_direction == Direction.BEARISH and is_bullish_candle:
            return j
    return None


def detect_fair_value_gaps(
    highs: list[float],
    lows: list[float],
    timestamps: list[datetime],
) -> list[FairValueGap]:
    gaps: list[FairValueGap] = []

    for i in range(2, len(highs)):
        if highs[i - 2] < lows[i]:
            gaps.append(
                FairValueGap(
                    index=i, timestamp=timestamps[i], direction=Direction.BULLISH, low=highs[i - 2], high=lows[i]
                )
            )
        elif lows[i - 2] > highs[i]:
            gaps.append(
                FairValueGap(
                    index=i, timestamp=timestamps[i], direction=Direction.BEARISH, low=highs[i], high=lows[i - 2]
                )
            )

    return gaps
