from datetime import UTC, datetime, timedelta

from app.core.constants import Direction
from app.features.structure import (
    StructureBreak,
    StructureEvent,
    Sweep,
    SwingKind,
    SwingPoint,
    detect_break_of_structure,
    detect_structure_breaks,
    detect_sweeps,
    detect_swing_points,
    weak_points,
)


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


# --- detect_sweeps ---


def test_detect_sweeps_finds_a_wick_through_with_no_close_beyond() -> None:
    point = SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)
    highs = [0, 0, 15, 16, 0]
    lows = [0, 0, 0, 0, 0]
    closes = [0, 0, 0, 14, 0]  # wicks to 16 but closes back below 15
    timestamps = _timestamps(5)

    sweeps = detect_sweeps([point], highs, lows, closes, timestamps)

    assert len(sweeps) == 1
    assert sweeps[0].swept_point == point
    assert sweeps[0].sweep_index == 3


def test_detect_sweeps_excludes_a_genuine_close_through_breakout() -> None:
    point = SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)
    highs = [0, 0, 15, 16, 0]
    lows = [0, 0, 0, 0, 0]
    closes = [0, 0, 0, 16, 0]  # closes beyond 15 -> a breakout, not a sweep
    timestamps = _timestamps(5)

    assert detect_sweeps([point], highs, lows, closes, timestamps) == []


def test_detect_sweeps_finds_nothing_for_an_untouched_point() -> None:
    point = SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)
    highs = [0, 0, 15, 10, 12]
    lows = [0, 0, 0, 5, 6]
    closes = [0, 0, 0, 9, 11]
    timestamps = _timestamps(5)

    assert detect_sweeps([point], highs, lows, closes, timestamps) == []


def test_detect_sweeps_mirrors_for_a_swing_low() -> None:
    point = SwingPoint(index=2, timestamp=_timestamps(1)[0], price=5.0, kind=SwingKind.LOW)
    highs = [0, 0, 0, 0, 0]
    lows = [0, 0, 5, 4, 0]
    closes = [0, 0, 0, 6, 0]  # wicks to 4 but closes back above 5
    timestamps = _timestamps(5)

    sweeps = detect_sweeps([point], highs, lows, closes, timestamps)

    assert len(sweeps) == 1
    assert sweeps[0].sweep_index == 3


# --- detect_structure_breaks ---


def test_detect_structure_breaks_tracks_choch_then_bos_then_choch() -> None:
    swing_points = [
        SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH),
        SwingPoint(index=5, timestamp=_timestamps(1)[0], price=20.0, kind=SwingKind.HIGH),
        SwingPoint(index=8, timestamp=_timestamps(1)[0], price=10.0, kind=SwingKind.LOW),
    ]
    closes = [14, 14, 14, 16, 14, 14, 21, 14, 14, 9]
    timestamps = _timestamps(10)

    breaks = detect_structure_breaks(swing_points, closes, timestamps)

    assert len(breaks) == 3
    assert breaks[0].event == StructureEvent.CHOCH
    assert breaks[0].direction == Direction.BULLISH
    assert breaks[0].break_index == 3

    assert breaks[1].event == StructureEvent.BOS
    assert breaks[1].direction == Direction.BULLISH
    assert breaks[1].break_index == 6

    assert breaks[2].event == StructureEvent.CHOCH
    assert breaks[2].direction == Direction.BEARISH
    assert breaks[2].break_index == 9


def test_detect_structure_breaks_ignores_a_point_never_closed_through() -> None:
    swing_points = [SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)]
    closes = [14, 14, 14, 10, 12]
    timestamps = _timestamps(5)

    assert detect_structure_breaks(swing_points, closes, timestamps) == []


# --- weak_points ---


def test_weak_points_excludes_swept_and_broken_points_only() -> None:
    swept = SwingPoint(index=2, timestamp=_timestamps(1)[0], price=15.0, kind=SwingKind.HIGH)
    broken = SwingPoint(index=5, timestamp=_timestamps(1)[0], price=20.0, kind=SwingKind.HIGH)
    untouched = SwingPoint(index=8, timestamp=_timestamps(1)[0], price=10.0, kind=SwingKind.LOW)

    sweep_records = [Sweep(swept_point=swept, sweep_index=3, sweep_timestamp=_timestamps(1)[0])]
    break_records = [
        StructureBreak(
            event=StructureEvent.CHOCH,
            direction=Direction.BULLISH,
            broken_point=broken,
            break_index=6,
            break_timestamp=_timestamps(1)[0],
        )
    ]

    result = weak_points([swept, broken, untouched], sweep_records, break_records)

    assert result == [untouched]
