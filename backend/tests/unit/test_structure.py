from datetime import UTC, datetime, timedelta

from app.core.constants import Direction
from app.features.structure import SwingKind, SwingPoint, detect_break_of_structure, detect_swing_points


def _timestamps(n: int) -> list[datetime]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [base + timedelta(minutes=i) for i in range(n)]


def test_detect_swing_points_finds_a_clear_high_and_low() -> None:
    highs = [10, 11, 15, 11, 10, 9, 8]
    lows = [9, 8, 7, 6, 5, 6, 7]
    timestamps = _timestamps(len(highs))

    swings = detect_swing_points(highs, lows, timestamps, lookback=2)

    swing_highs = [s for s in swings if s.kind == SwingKind.HIGH]
    swing_lows = [s for s in swings if s.kind == SwingKind.LOW]
    assert any(s.index == 2 and s.price == 15 for s in swing_highs)
    assert any(s.index == 4 and s.price == 5 for s in swing_lows)


def test_detect_swing_points_ignores_flat_ties() -> None:
    highs = [10, 10, 10, 10, 10]
    lows = [5, 5, 5, 5, 5]
    timestamps = _timestamps(5)

    assert detect_swing_points(highs, lows, timestamps, lookback=2) == []


def test_detect_swing_points_returns_nothing_when_shorter_than_two_lookbacks() -> None:
    highs = [10, 11, 12]
    lows = [9, 8, 7]
    timestamps = _timestamps(3)

    assert detect_swing_points(highs, lows, timestamps, lookback=2) == []


def test_break_of_structure_is_bullish_above_last_swing_high() -> None:
    swing_points = [SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)]
    assert detect_break_of_structure(swing_points, latest_close=16.0) == Direction.BULLISH


def test_break_of_structure_is_bearish_below_last_swing_low() -> None:
    swing_points = [SwingPoint(index=4, timestamp=_timestamps(1)[0], price=5.0, kind=SwingKind.LOW)]
    assert detect_break_of_structure(swing_points, latest_close=4.0) == Direction.BEARISH


def test_break_of_structure_is_neutral_inside_the_range() -> None:
    swing_points = [
        SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH),
        SwingPoint(index=4, timestamp=_timestamps(1)[0], price=5.0, kind=SwingKind.LOW),
    ]
    assert detect_break_of_structure(swing_points, latest_close=10.0) == Direction.NEUTRAL


def test_break_of_structure_is_neutral_with_no_swing_points() -> None:
    assert detect_break_of_structure([], latest_close=100.0) == Direction.NEUTRAL
