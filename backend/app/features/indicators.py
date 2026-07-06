"""Vectorized technical indicators over a closed-candle price series.

Every function takes pandas Series of already-closed candles and returns an
aligned Series; callers read the latest (last) value when they need a
scalar for a live prediction. Periods below are conventional TA defaults
(RSI/ATR: 14) or reasonable choices for 1m-15m timeframes (SMA/momentum/
volatility) — not tuned yet, revisit once backtesting (Phase 9) can score
them against outcomes.
"""

import numpy as np
import pandas as pd

DEFAULT_SMA_FAST_PERIOD = 10
DEFAULT_SMA_SLOW_PERIOD = 30
DEFAULT_RSI_PERIOD = 14
DEFAULT_ATR_PERIOD = 14
DEFAULT_MOMENTUM_PERIOD = 10
DEFAULT_VOLATILITY_PERIOD = 20


def simple_moving_average(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period, min_periods=period).mean()


def relative_strength_index(close: pd.Series, period: int = DEFAULT_RSI_PERIOD) -> pd.Series:
    """RSI on a 0-100 scale. A perfectly flat window scores 50 (no momentum
    either way); an all-gains window scores 100; an all-losses window scores 0.
    """
    delta = close.diff()
    avg_gain = delta.clip(lower=0.0).rolling(window=period, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0.0)).rolling(window=period, min_periods=period).mean()

    with np.errstate(divide="ignore", invalid="ignore"):
        relative_strength = avg_gain / avg_loss
        formula = 100 - (100 / (1 + relative_strength))

    conditions = [
        (avg_gain == 0) & (avg_loss == 0),
        avg_loss == 0,
        avg_gain == 0,
    ]
    choices = [50.0, 100.0, 0.0]
    return pd.Series(np.select(conditions, choices, default=formula), index=close.index)


def average_true_range(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = DEFAULT_ATR_PERIOD
) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def momentum(close: pd.Series, period: int = DEFAULT_MOMENTUM_PERIOD) -> pd.Series:
    """Price change over `period` candles, in price units (not percent)."""
    return close.diff(periods=period)


def volatility(close: pd.Series, period: int = DEFAULT_VOLATILITY_PERIOD) -> pd.Series:
    return close.rolling(window=period, min_periods=period).std()
