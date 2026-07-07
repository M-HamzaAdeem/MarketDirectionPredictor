from datetime import UTC, datetime, timedelta

from app.core.constants import Direction
from app.features.poi import detect_fair_value_gaps, detect_order_blocks


def _timestamps(n: int) -> list[datetime]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [base + timedelta(minutes=i) for i in range(n)]


# --- detect_order_blocks ---


def test_detect_order_blocks_finds_the_last_bearish_candle_before_a_bullish_impulse() -> None:
    # index 0: filler, index 1: bearish candle (the OB, not itself impulsive),
    # index 2: bullish impulse (range >> ATR)
    opens = [10.0, 10.5, 9.0]
    closes = [10.4, 10.0, 15.0]
    highs = [10.5, 10.6, 15.2]
    lows = [9.9, 9.9, 8.9]
    atr = [None, 1.0, 1.0]
    timestamps = _timestamps(3)

    order_blocks = detect_order_blocks(opens, highs, lows, closes, atr, timestamps, impulse_atr_multiplier=1.5)

    assert len(order_blocks) == 1
    ob = order_blocks[0]
    assert ob.index == 1
    assert ob.direction == Direction.BULLISH
    assert ob.low == 9.9
    assert ob.high == 10.6
    assert ob.impulse_index == 2


def test_detect_order_blocks_finds_the_last_bullish_candle_before_a_bearish_impulse() -> None:
    opens = [10.0, 9.5, 15.0]
    closes = [10.4, 10.0, 9.0]
    highs = [10.5, 10.6, 15.2]
    lows = [9.9, 9.4, 8.8]
    atr = [None, 1.0, 1.0]
    timestamps = _timestamps(3)

    order_blocks = detect_order_blocks(opens, highs, lows, closes, atr, timestamps, impulse_atr_multiplier=1.5)

    assert len(order_blocks) == 1
    assert order_blocks[0].direction == Direction.BEARISH
    assert order_blocks[0].index == 1


def test_detect_order_blocks_ignores_a_move_that_is_not_impulsive() -> None:
    opens = [10.0, 9.0, 9.5]
    closes = [10.5, 9.5, 10.0]  # small move, well within ATR
    highs = [10.6, 9.6, 10.1]
    lows = [9.9, 8.9, 9.4]
    atr = [None, 1.0, 1.0]
    timestamps = _timestamps(3)

    assert detect_order_blocks(opens, highs, lows, closes, atr, timestamps, impulse_atr_multiplier=1.5) == []


def test_detect_order_blocks_skips_candles_with_no_atr_yet() -> None:
    opens = [10.0, 9.0]
    closes = [10.5, 15.0]
    highs = [10.6, 15.2]
    lows = [9.9, 8.9]
    atr = [None, None]  # not enough history for ATR
    timestamps = _timestamps(2)

    assert detect_order_blocks(opens, highs, lows, closes, atr, timestamps) == []


# --- detect_fair_value_gaps ---


def test_detect_fair_value_gaps_finds_a_bullish_gap() -> None:
    highs = [10.0, 11.0, 13.0]
    lows = [9.5, 10.5, 12.5]  # candle0.high (10.0) < candle2.low (12.5)
    timestamps = _timestamps(3)

    gaps = detect_fair_value_gaps(highs, lows, timestamps)

    assert len(gaps) == 1
    assert gaps[0].direction == Direction.BULLISH
    assert gaps[0].low == 10.0
    assert gaps[0].high == 12.5
    assert gaps[0].index == 2


def test_detect_fair_value_gaps_finds_a_bearish_gap() -> None:
    highs = [10.0, 9.0, 7.5]
    lows = [9.5, 8.5, 7.0]  # candle0.low (9.5) > candle2.high (7.5)
    timestamps = _timestamps(3)

    gaps = detect_fair_value_gaps(highs, lows, timestamps)

    assert len(gaps) == 1
    assert gaps[0].direction == Direction.BEARISH
    assert gaps[0].low == 7.5
    assert gaps[0].high == 9.5


def test_detect_fair_value_gaps_finds_nothing_when_candles_overlap() -> None:
    highs = [10.0, 10.5, 11.0]
    lows = [9.5, 9.8, 9.9]
    timestamps = _timestamps(3)

    assert detect_fair_value_gaps(highs, lows, timestamps) == []
