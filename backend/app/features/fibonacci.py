"""Optimal Trade Entry (OTE): the Fibonacci retracement zone of an impulse
leg considered the ideal continuation/reversal entry.

Locked to 70.5%-79% retracement per project convention (a tighter, deeper
variant than the standard 61.8%-79% OTE zone).
"""

from dataclasses import dataclass

from app.core.constants import Direction

DEFAULT_OTE_SHALLOW_RATIO = 0.705
DEFAULT_OTE_DEEP_RATIO = 0.79


@dataclass(frozen=True, slots=True)
class OteZone:
    low: float
    high: float


def compute_ote_zone(
    leg_start: float,
    leg_end: float,
    direction: Direction,
    shallow_ratio: float = DEFAULT_OTE_SHALLOW_RATIO,
    deep_ratio: float = DEFAULT_OTE_DEEP_RATIO,
) -> OteZone:
    """`leg_start` -> `leg_end` is the impulse leg (e.g. the swept low up to
    the swing high, for a bullish leg). Returns the retracement zone
    measured back from `leg_end` toward `leg_start`."""
    leg_range = abs(leg_end - leg_start)

    if direction == Direction.BULLISH:
        return OteZone(low=leg_end - deep_ratio * leg_range, high=leg_end - shallow_ratio * leg_range)
    return OteZone(low=leg_end + shallow_ratio * leg_range, high=leg_end + deep_ratio * leg_range)
