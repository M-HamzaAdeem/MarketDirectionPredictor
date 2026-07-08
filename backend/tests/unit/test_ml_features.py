import pytest

from app.core.constants import Direction, Symbol, Timeframe
from app.features.feature_builder import FeatureSet
from app.ml.features import feature_vector


def _features(**overrides: object) -> FeatureSet:
    defaults: dict[str, object] = {
        "symbol": Symbol.XAUUSD,
        "timeframe": Timeframe.M1,
        "latest_close": 2350.0,
        "sma_fast": 2360.0,
        "sma_slow": 2350.0,
        "rsi": 65.0,
        "atr": 11.75,
        "momentum": 23.5,
        "volatility": 4.7,
        "structure": Direction.BULLISH,
    }
    defaults.update(overrides)
    return FeatureSet(**defaults)  # type: ignore[arg-type]


def test_feature_vector_normalizes_price_dependent_indicators() -> None:
    vector = feature_vector(_features())

    assert vector is not None
    sma_spread_pct, rsi, atr_pct, momentum_pct, volatility_pct, structure = vector
    assert sma_spread_pct == pytest.approx((2360.0 - 2350.0) / 2350.0)
    assert rsi == 65.0
    assert atr_pct == pytest.approx(11.75 / 2350.0)
    assert momentum_pct == pytest.approx(23.5 / 2350.0)
    assert volatility_pct == pytest.approx(4.7 / 2350.0)
    assert structure == 1.0


@pytest.mark.parametrize(
    "direction,expected",
    [(Direction.BULLISH, 1.0), (Direction.BEARISH, -1.0), (Direction.NEUTRAL, 0.0)],
)
def test_structure_encoding(direction: Direction, expected: float) -> None:
    vector = feature_vector(_features(structure=direction))
    assert vector is not None
    assert vector[-1] == expected


@pytest.mark.parametrize(
    "missing_field", ["sma_fast", "sma_slow", "rsi", "atr", "momentum", "volatility"]
)
def test_returns_none_when_any_required_indicator_is_missing(missing_field: str) -> None:
    assert feature_vector(_features(**{missing_field: None})) is None


def test_returns_none_when_latest_close_is_zero() -> None:
    assert feature_vector(_features(latest_close=0.0)) is None


def test_returns_none_when_sma_slow_is_zero() -> None:
    assert feature_vector(_features(sma_slow=0.0)) is None
