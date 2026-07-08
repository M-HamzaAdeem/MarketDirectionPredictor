from datetime import UTC, datetime, timedelta

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.features.fibonacci import OteZone, compute_ote_zone
from app.features.structure import StructureBreak, StructureEvent, Sweep, SwingKind, SwingPoint
from app.prediction.signal_builder import (
    MIN_RISK_REWARD,
    _Setup,
    _build_reason,
    _check_entry,
    _compute_stop,
    _find_leg_end,
    _find_target,
    _intersect,
    _pick_best_zone,
    build_signal,
)


def _timestamps(n: int) -> list[datetime]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [base + timedelta(hours=i) for i in range(n)]


def _candle(
    low: float,
    high: float,
    timeframe: Timeframe = Timeframe.M15,
    close_time: datetime = datetime(2026, 1, 1, 0, 15, tzinfo=UTC),
) -> Candle:
    return Candle(
        symbol=Symbol.XAUUSD,
        timeframe=timeframe,
        open_time=close_time - timedelta(minutes=15),
        close_time=close_time,
        open=(low + high) / 2,
        high=high,
        low=low,
        close=(low + high) / 2,
        volume=0.0,
    )


_EPOCH = datetime(2020, 1, 1, tzinfo=UTC)  # before every fixture candle; imposes no boundary


# --- _find_leg_end ---


def test_find_leg_end_picks_the_highest_high_for_a_bullish_leg() -> None:
    highs = [10.0, 12.0, 9.0, 15.0, 11.0]
    lows = [9.0, 11.0, 8.0, 14.0, 10.0]

    index, price = _find_leg_end(Direction.BULLISH, highs, lows, break_index=1)

    assert index == 3
    assert price == 15.0


def test_find_leg_end_picks_the_lowest_low_for_a_bearish_leg() -> None:
    highs = [10.0, 8.0, 11.0, 5.0, 9.0]
    lows = [9.0, 7.0, 10.0, 4.0, 8.0]

    index, price = _find_leg_end(Direction.BEARISH, highs, lows, break_index=1)

    assert index == 3
    assert price == 4.0


# --- _intersect ---


def test_intersect_returns_the_overlapping_range() -> None:
    poi = (10.0, 20.0, "order_block")
    ote = OteZone(low=15.0, high=25.0)

    result = _intersect(poi, ote)

    assert result == (15.0, 20.0, "order_block")


def test_intersect_returns_none_when_ranges_do_not_overlap() -> None:
    poi = (10.0, 12.0, "order_block")
    ote = OteZone(low=15.0, high=25.0)

    assert _intersect(poi, ote) is None


# --- _pick_best_zone ---


def test_pick_best_zone_returns_the_only_zone_with_no_volume_profile() -> None:
    zones = [(10.0, 12.0, "order_block")]
    assert _pick_best_zone(zones, None) == (10.0, 12.0, "order_block")


# --- _compute_stop ---


def test_compute_stop_places_a_bullish_stop_below_the_swept_level() -> None:
    stop = _compute_stop(Direction.BULLISH, swept_level=100.0, atr=2.0)
    assert stop == 100.0 - 2.0 * 0.25


def test_compute_stop_places_a_bearish_stop_above_the_swept_level() -> None:
    stop = _compute_stop(Direction.BEARISH, swept_level=100.0, atr=2.0)
    assert stop == 100.0 + 2.0 * 0.25


def test_compute_stop_falls_back_to_a_price_ratio_buffer_without_atr() -> None:
    stop = _compute_stop(Direction.BULLISH, swept_level=100.0, atr=None)
    assert stop == 100.0 - 100.0 * 0.001


# --- _find_target ---


def test_find_target_finds_the_nearest_opposing_weak_high_for_a_bullish_setup() -> None:
    ts = _timestamps(3)
    swings = [
        SwingPoint(index=0, timestamp=ts[0], price=110.0, kind=SwingKind.HIGH),
        SwingPoint(index=1, timestamp=ts[1], price=130.0, kind=SwingKind.HIGH),
    ]
    target = _find_target(Direction.BULLISH, entry_low=100.0, entry_high=101.0, swings=swings, sweeps=[], breaks=[])
    assert target == 110.0


def test_find_target_excludes_swept_or_broken_points() -> None:
    ts = _timestamps(3)
    near = SwingPoint(index=0, timestamp=ts[0], price=110.0, kind=SwingKind.HIGH)
    far = SwingPoint(index=1, timestamp=ts[1], price=130.0, kind=SwingKind.HIGH)
    swings = [near, far]
    breaks = [
        StructureBreak(
            event=StructureEvent.BOS, direction=Direction.BULLISH, broken_point=near, break_index=2, break_timestamp=ts[2]
        )
    ]

    target = _find_target(Direction.BULLISH, entry_low=100.0, entry_high=101.0, swings=swings, sweeps=[], breaks=breaks)

    assert target == 130.0


def test_find_target_returns_none_when_no_opposing_liquidity_exists() -> None:
    target = _find_target(Direction.BULLISH, entry_low=100.0, entry_high=101.0, swings=[], sweeps=[], breaks=[])
    assert target is None


# --- _check_entry ---


def test_check_entry_finds_the_most_recent_candle_that_taps_the_zone() -> None:
    candles = [_candle(90.0, 95.0), _candle(98.0, 102.0), _candle(105.0, 110.0)]
    tap = _check_entry(entry_low=99.0, entry_high=101.0, candles=candles, earliest_entry_time=_EPOCH)
    assert tap is candles[1]


def test_check_entry_returns_none_when_no_candle_taps_the_zone() -> None:
    candles = [_candle(90.0, 95.0), _candle(105.0, 110.0)]
    assert _check_entry(entry_low=99.0, entry_high=101.0, candles=candles, earliest_entry_time=_EPOCH) is None


def test_check_entry_ignores_a_tap_that_closed_before_the_zone_was_valid() -> None:
    # The zone (an OTE/POI retracement level) only becomes meaningful once
    # the leg that defines it has finished forming — a candle passing
    # through that price range before then is the original impulsive move,
    # not a genuine return to a level that didn't exist yet.
    zone_confirmed_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    stale_tap = _candle(99.0, 101.0, close_time=datetime(2026, 1, 1, 0, 15, tzinfo=UTC))

    tap = _check_entry(entry_low=99.0, entry_high=101.0, candles=[stale_tap], earliest_entry_time=zone_confirmed_at)

    assert tap is None


def test_check_entry_accepts_a_tap_after_the_zone_was_confirmed() -> None:
    zone_confirmed_at = datetime(2026, 1, 1, tzinfo=UTC)
    valid_tap = _candle(99.0, 101.0, close_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC))

    tap = _check_entry(entry_low=99.0, entry_high=101.0, candles=[valid_tap], earliest_entry_time=zone_confirmed_at)

    assert tap is valid_tap


# --- build_signal (full pipeline, end to end) ---
#
# Fixture: a bullish setup hand-verified stage-by-stage (bias -> sweep -> CHoCH
# -> POI/OTE confluence -> target) via the private helpers above, before being
# wired into candles here. See the sweep at index 9 (wicks below the swing low
# at index 3 formed near index 3, closes back above it), the CHoCH at index 13
# (closes above the swing high at index 7), and a fresh, untested swing high
# at index 15 (price ~120.6) serving as the target.


def _bullish_1h_candles() -> list[Candle]:
    opens = [100, 100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118]
    closes = [100, 97, 94, 98, 102, 106, 110, 106, 102, 95, 97, 102, 107, 115, 120, 116, 118, 117]
    wicks = [0.3 + 0.02 * i for i in range(len(opens))]
    highs = [max(o, c) + w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows = [min(o, c) - w for o, c, w in zip(opens, closes, wicks, strict=True)]
    lows[9] = 89.0  # force a deep wick sweeping the swing low near index 3

    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=Timeframe.H1,
            open_time=base + timedelta(hours=i),
            close_time=base + timedelta(hours=i + 1),
            open=opens[i],
            high=highs[i],
            low=lows[i],
            close=closes[i],
            volume=10.0 + i,
        )
        for i in range(len(closes))
    ]


def test_build_signal_produces_a_bullish_signal_meeting_the_rr_floor() -> None:
    candles_1h = _bullish_1h_candles()
    candles_4h = candles_1h  # same directional pattern serves as the HTF bias source
    # Taps the [97.5, 98.322] entry zone, closing well after the last 1h
    # candle (hour 18) so the tap postdates the leg that defines the zone.
    candles_15m = [_candle(97.0, 99.0, timeframe=Timeframe.M15, close_time=datetime(2026, 1, 1, 19, 0, tzinfo=UTC))]

    signal = build_signal(Symbol.XAUUSD, candles_4h, candles_1h, candles_15m)

    assert signal is not None
    assert signal.symbol == Symbol.XAUUSD
    assert signal.direction == Direction.BULLISH
    assert signal.stop < signal.entry < signal.target
    assert signal.risk_reward >= MIN_RISK_REWARD
    assert "swept" in signal.reason
    assert signal.details["swept_level"] == 89.0
    assert signal.details["confirming_event"] == "choch"


def test_build_reason_reflects_bos_not_hardcoded_choch() -> None:
    setup = _Setup(
        direction=Direction.BULLISH,
        entry_low=95.0,
        entry_high=97.0,
        poi_type="order_block",
        stop=90.0,
        target=110.0,
        swept_level=91.0,
        ote=compute_ote_zone(89.0, 100.0, Direction.BULLISH),
        volume_profile_poc=None,
        confirming_event=StructureEvent.BOS,
        earliest_entry_time=_EPOCH,
    )

    reason = _build_reason(setup, risk_reward=2.0)

    assert "BOS" in reason
    assert "CHoCH" not in reason


def test_build_signal_returns_none_when_price_never_taps_the_entry_zone() -> None:
    candles_1h = _bullish_1h_candles()
    candles_4h = candles_1h
    candles_15m = [_candle(150.0, 155.0, timeframe=Timeframe.M15)]  # far from the entry zone

    assert build_signal(Symbol.XAUUSD, candles_4h, candles_1h, candles_15m) is None


def test_build_signal_returns_none_with_no_bias() -> None:
    flat_candles = [_candle(100.0, 101.0, timeframe=Timeframe.H4) for _ in range(10)]
    assert build_signal(Symbol.XAUUSD, flat_candles, flat_candles, flat_candles) is None


def test_build_signal_rejects_a_tap_that_closed_before_the_leg_completed() -> None:
    # Regression for the stale-entry-tap bug: a 15m candle whose price range
    # overlaps the entry zone but that closed hours before the sweep/break/
    # leg-end that defines the zone (hour 2, well before the sweep at hour
    # 9-10) must not count as a valid tap, even though its range overlaps
    # [97.5, 98.322] — that zone didn't exist yet when this candle closed.
    candles_1h = _bullish_1h_candles()
    candles_4h = candles_1h
    early_tap = _candle(97.0, 99.0, timeframe=Timeframe.M15, close_time=datetime(2026, 1, 1, 2, 0, tzinfo=UTC))

    assert build_signal(Symbol.XAUUSD, candles_4h, candles_1h, [early_tap]) is None
