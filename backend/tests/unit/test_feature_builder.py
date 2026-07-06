from datetime import UTC, datetime, timedelta

import pytest

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.features.feature_builder import build_feature_set


def _make_candles(closes: list[float]) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=Timeframe.M1,
            open_time=base + timedelta(minutes=i),
            close_time=base + timedelta(minutes=i + 1),
            open=close,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=0.0,
        )
        for i, close in enumerate(closes)
    ]


def test_build_feature_set_with_few_candles_leaves_slow_indicators_none() -> None:
    candles = _make_candles([100.0, 101.0, 102.0])
    features = build_feature_set(Symbol.XAUUSD, Timeframe.M1, candles)

    assert features.latest_close == 102.0
    assert features.sma_slow is None


def test_build_feature_set_with_enough_candles_computes_every_indicator() -> None:
    closes = [100.0 + i for i in range(40)]  # steady uptrend, long enough for every indicator
    candles = _make_candles(closes)

    features = build_feature_set(Symbol.XAUUSD, Timeframe.M1, candles)

    assert features.latest_close == closes[-1]
    assert features.sma_fast is not None
    assert features.sma_slow is not None
    assert features.rsi == pytest.approx(100.0)
    assert features.atr is not None
    assert features.momentum is not None
    assert features.volatility is not None


def test_build_feature_set_raises_on_an_empty_candle_list() -> None:
    with pytest.raises(ValueError):
        build_feature_set(Symbol.XAUUSD, Timeframe.M1, [])
