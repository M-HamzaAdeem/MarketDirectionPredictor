from datetime import UTC, datetime, timedelta

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.signal import SignalStatus
from app.backtesting.signal_backtest import run_signal_backtest


def _bullish_1h_candles() -> list[Candle]:
    """Same fixture as test_signal_builder.py's `_bullish_1h_candles` — a
    weak low swept at index 9, CHoCH at index 13, fresh swing high (~120.6)
    at index 15 serving as the target. Proven (via test_signal_builder.py
    and manual REPL verification) to produce a real bullish signal once
    all 18 candles are visible and price taps [97.5, 98.322]."""
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


def _m15_candle(low: float, high: float, close_time: datetime) -> Candle:
    return Candle(
        symbol=Symbol.XAUUSD,
        timeframe=Timeframe.M15,
        open_time=close_time - timedelta(minutes=15),
        close_time=close_time,
        open=(low + high) / 2,
        high=high,
        low=low,
        close=(low + high) / 2,
        volume=0.0,
    )


def test_produces_and_resolves_a_win() -> None:
    candles_1h = _bullish_1h_candles()
    candles_4h = candles_1h  # same pattern serves as the HTF bias source, matching test_signal_builder.py
    hour_18 = datetime(2026, 1, 1, 18, tzinfo=UTC)
    candles_15m = [
        _m15_candle(150.0, 155.0, hour_18 + timedelta(minutes=15)),  # far from entry zone: no signal
        _m15_candle(97.0, 99.0, hour_18 + timedelta(minutes=30)),  # taps [97.5, 98.322]: signal fires
        _m15_candle(110.0, 121.0, hour_18 + timedelta(minutes=45)),  # hits the 120.6 target: WIN
    ]

    summary = run_signal_backtest(
        Symbol.XAUUSD, candles_4h, candles_1h, candles_15m, window_4h=18, window_1h=18, window_15m=1
    )

    assert summary.total_signals == 1
    assert summary.wins == 1
    assert summary.losses == 0
    assert summary.win_rate == 1.0
    assert summary.avg_realized_rr > 0


def test_signal_left_unresolved_by_the_end_of_history_counts_as_still_open() -> None:
    candles_1h = _bullish_1h_candles()
    hour_18 = datetime(2026, 1, 1, 18, tzinfo=UTC)
    candles_15m = [
        _m15_candle(97.0, 99.0, hour_18 + timedelta(minutes=15)),  # signal fires
        # Above the entry zone (so it doesn't tap and produce a second
        # signal) but below the 120.6 target and above the 88.911 stop.
        _m15_candle(105.0, 106.0, hour_18 + timedelta(minutes=30)),
    ]

    summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, candles_15m, window_4h=18, window_1h=18, window_15m=1
    )

    assert summary.total_signals == 1
    assert summary.still_open == 1
    assert summary.wins == 0
    assert summary.losses == 0
    assert summary.win_rate == 0.0  # no decided (win/loss) outcomes yet


def test_not_enough_warmup_history_produces_no_signals() -> None:
    candles_1h = _bullish_1h_candles()
    candles_15m = [_m15_candle(97.0, 99.0, datetime(2026, 1, 1, 18, 15, tzinfo=UTC))]

    # window_1h=19 is one more candle than the fixture provides, so warmup
    # is never satisfied regardless of how good the setup looks.
    summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, candles_15m, window_4h=18, window_1h=19, window_15m=1
    )

    assert summary.total_signals == 0


def test_does_not_leak_future_1h_candles_into_an_earlier_15m_step() -> None:
    """The critical regression test: a 15m step earlier in time than the
    18th 1h candle's close must only ever see the 1h candles that would
    genuinely have closed by then. Without correct as-of windowing, the
    same price tap would incorrectly produce a signal using the full,
    not-yet-closed 1h history (proven bullish once the CHoCH at index 13
    is visible) instead of the true, still-neutral partial history."""
    candles_1h = _bullish_1h_candles()

    early_tap = _m15_candle(97.0, 99.0, datetime(2026, 1, 1, 10, 15, tzinfo=UTC))  # only ~10 1h candles closed
    late_tap = _m15_candle(97.0, 99.0, datetime(2026, 1, 1, 18, 15, tzinfo=UTC))  # all 18 1h candles closed

    early_summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, [early_tap], window_4h=10, window_1h=10, window_15m=1
    )
    late_summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, [late_tap], window_4h=18, window_1h=18, window_15m=1
    )

    assert early_summary.total_signals == 0  # CHoCH at index 13 must not be visible yet
    assert late_summary.total_signals == 1  # same tap, full history now visible -> real signal


def test_does_not_create_a_duplicate_signal_while_one_is_already_open() -> None:
    """Regression for the exact live bug this fix addresses: with a
    rolling 15m window wider than 1, the same historical tap candle can
    stay "in view" across multiple consecutive steps and get rediscovered
    by _check_entry every time, even though nothing new has happened.
    Without the open-signal guard, each rediscovery would be appended as
    a separate "signal" for the same still-open setup."""
    candles_1h = _bullish_1h_candles()
    hour_18 = datetime(2026, 1, 1, 18, tzinfo=UTC)
    candles_15m = [
        _m15_candle(150.0, 155.0, hour_18 + timedelta(minutes=15)),  # out of zone
        _m15_candle(97.0, 99.0, hour_18 + timedelta(minutes=30)),  # taps [97.5, 98.322]: signal fires
        # Out of the entry zone itself, and — critically — between the
        # ~88.911 stop and ~120.6 target, so it doesn't resolve the open
        # signal either. With window_15m=2 the tap candle above is still
        # inside this step's rolling window — the exact condition that
        # produced a duplicate signal live before this fix.
        _m15_candle(105.0, 106.0, hour_18 + timedelta(minutes=45)),
    ]

    summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, candles_15m, window_4h=18, window_1h=18, window_15m=2
    )

    assert summary.total_signals == 1
    assert summary.still_open == 1


def test_summary_reports_none_for_range_bounds_on_empty_input() -> None:
    summary = run_signal_backtest(Symbol.XAUUSD, [], [], [])

    assert summary.total_signals == 0
    assert summary.range_start is None
    assert summary.range_end is None
    assert summary.win_rate == 0.0
    assert summary.avg_realized_rr == 0.0


def test_expired_signals_are_excluded_from_win_rate() -> None:
    candles_1h = _bullish_1h_candles()
    hour_18 = datetime(2026, 1, 1, 18, tzinfo=UTC)
    # After the entry tap, price sits neutral for long enough to expire
    # (DEFAULT_EXPIRY is 5 days) rather than hitting stop or target.
    candles_15m = [_m15_candle(97.0, 99.0, hour_18 + timedelta(minutes=15))]
    # Above the entry zone (no second tap) and short of both stop/target,
    # 6 days later — past DEFAULT_EXPIRY (5 days) with neither level hit.
    candles_15m.append(_m15_candle(105.0, 106.0, hour_18 + timedelta(minutes=15) + timedelta(days=6)))

    summary = run_signal_backtest(
        Symbol.XAUUSD, candles_1h, candles_1h, candles_15m, window_4h=18, window_1h=18, window_15m=1
    )

    assert summary.total_signals == 1
    assert summary.expired == 1
    assert summary.wins == 0
    assert summary.losses == 0
    assert summary.win_rate == 0.0
    assert summary.avg_realized_rr == 0.0  # expired isn't a realized R:R outcome
