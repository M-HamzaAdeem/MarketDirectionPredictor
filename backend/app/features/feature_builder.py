"""Assembles the full feature set for one symbol/timeframe from a window of
closed candles: indicator values as of the latest candle, plus market
structure. This is the only module the Phase 3 prediction engine needs to
import from app.features.
"""

from dataclasses import dataclass

import pandas as pd

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.features import indicators
from app.features.structure import detect_break_of_structure, detect_swing_points


@dataclass(frozen=True, slots=True)
class FeatureSet:
    symbol: Symbol
    timeframe: Timeframe
    latest_close: float
    sma_fast: float | None
    sma_slow: float | None
    rsi: float | None
    atr: float | None
    momentum: float | None
    volatility: float | None
    structure: Direction


def build_feature_set(symbol: Symbol, timeframe: Timeframe, candles: list[Candle]) -> FeatureSet:
    """`candles` must be closed candles in ascending open_time order."""
    if not candles:
        raise ValueError("build_feature_set requires at least one candle")

    frame = pd.DataFrame(
        {
            "high": [candle.high for candle in candles],
            "low": [candle.low for candle in candles],
            "close": [candle.close for candle in candles],
        }
    )
    timestamps = [candle.open_time for candle in candles]
    swings = detect_swing_points(list(frame["high"]), list(frame["low"]), timestamps)
    structure = detect_break_of_structure(swings, candles[-1].close)

    return FeatureSet(
        symbol=symbol,
        timeframe=timeframe,
        latest_close=candles[-1].close,
        sma_fast=_last_valid(indicators.simple_moving_average(frame["close"], indicators.DEFAULT_SMA_FAST_PERIOD)),
        sma_slow=_last_valid(indicators.simple_moving_average(frame["close"], indicators.DEFAULT_SMA_SLOW_PERIOD)),
        rsi=_last_valid(indicators.relative_strength_index(frame["close"])),
        atr=_last_valid(indicators.average_true_range(frame["high"], frame["low"], frame["close"])),
        momentum=_last_valid(indicators.momentum(frame["close"])),
        volatility=_last_valid(indicators.volatility(frame["close"])),
        structure=structure,
    )


def _last_valid(series: pd.Series) -> float | None:
    value = series.iloc[-1]
    return None if pd.isna(value) else float(value)
