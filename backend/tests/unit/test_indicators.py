import pandas as pd
import pytest

from app.features import indicators


def test_simple_moving_average_computes_rolling_mean() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    sma = indicators.simple_moving_average(close, period=3)

    assert pd.isna(sma.iloc[1])
    assert sma.iloc[2] == pytest.approx(2.0)
    assert sma.iloc[3] == pytest.approx(3.0)
    assert sma.iloc[4] == pytest.approx(4.0)


def test_rsi_is_100_when_only_gains() -> None:
    close = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    rsi = indicators.relative_strength_index(close, period=3)
    assert rsi.iloc[-1] == pytest.approx(100.0)


def test_rsi_is_0_when_only_losses() -> None:
    close = pd.Series([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])
    rsi = indicators.relative_strength_index(close, period=3)
    assert rsi.iloc[-1] == pytest.approx(0.0)


def test_rsi_is_50_on_a_flat_series() -> None:
    close = pd.Series([5.0] * 6)
    rsi = indicators.relative_strength_index(close, period=3)
    assert rsi.iloc[-1] == pytest.approx(50.0)


def test_rsi_formula_path_matches_a_known_value() -> None:
    close = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 13.5])
    rsi = indicators.relative_strength_index(close, period=3)
    assert rsi.iloc[-1] == pytest.approx(80.0)


def test_rsi_of_a_mixed_series_is_strictly_between_0_and_100() -> None:
    close = pd.Series([10.0, 11.0, 10.0, 12.0, 11.0, 13.0])
    rsi = indicators.relative_strength_index(close, period=3)
    assert 0.0 < rsi.iloc[-1] < 100.0


def test_atr_uses_the_widest_of_the_three_true_range_candidates() -> None:
    high = pd.Series([10.0, 12.0, 11.0])
    low = pd.Series([9.0, 9.5, 8.0])
    close = pd.Series([9.5, 11.5, 8.5])
    atr = indicators.average_true_range(high, low, close, period=2)

    # bar 1 TR = max(12-9.5, |12-9.5|, |9.5-9.5|) = 2.5
    # bar 2 TR = max(11-8, |11-11.5|, |8-11.5|)   = 3.5
    assert atr.iloc[2] == pytest.approx((2.5 + 3.5) / 2)


def test_momentum_is_the_price_change_over_the_period() -> None:
    close = pd.Series([10.0, 11.0, 13.0, 16.0])
    mom = indicators.momentum(close, period=2)

    assert mom.iloc[2] == pytest.approx(3.0)
    assert mom.iloc[3] == pytest.approx(5.0)


def test_volatility_is_the_rolling_standard_deviation() -> None:
    close = pd.Series([10.0, 12.0, 8.0, 14.0, 6.0])
    vol = indicators.volatility(close, period=3)

    assert vol.iloc[2] == pytest.approx(close.iloc[0:3].std())
