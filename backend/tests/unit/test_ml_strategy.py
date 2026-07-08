from pathlib import Path

import joblib

from app.core.constants import Direction, Symbol, Timeframe
from app.features.feature_builder import FeatureSet
from app.prediction.ml_strategy import MLStrategy


class _FakeClassifier:
    """Deterministic stand-in for a trained scikit-learn classifier —
    joblib-picklable since it's a plain, module-level class."""

    def __init__(self, proba_up: float, classes: list[int] | None = None) -> None:
        self.proba_up = proba_up
        self.classes_ = classes if classes is not None else [0, 1]
        self.call_count = 0

    def predict_proba(self, X: list[list[float]]) -> list[list[float]]:
        self.call_count += 1
        return [[1 - self.proba_up, self.proba_up]]


def _features(**overrides: object) -> FeatureSet:
    defaults: dict[str, object] = {
        "symbol": Symbol.XAUUSD,
        "timeframe": Timeframe.H1,
        "latest_close": 2350.0,
        "sma_fast": 2360.0,
        "sma_slow": 2350.0,
        "rsi": 55.0,
        "atr": 11.0,
        "momentum": 5.0,
        "volatility": 4.0,
        "structure": Direction.BULLISH,
    }
    defaults.update(overrides)
    return FeatureSet(**defaults)  # type: ignore[arg-type]


def _save_model(model_dir: Path, symbol: Symbol, timeframe: Timeframe, classifier: _FakeClassifier) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(classifier, model_dir / f"{symbol.value}_{timeframe.value}.joblib")


def test_evaluate_returns_neutral_when_no_model_file_exists(tmp_path: Path) -> None:
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features())

    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0
    assert "no trained model" in signal.reason


def test_evaluate_returns_neutral_when_features_are_insufficient(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.9))
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features(rsi=None))

    assert signal.direction == Direction.NEUTRAL
    assert signal.reason == "insufficient data"


def test_evaluate_maps_high_probability_to_bullish(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.9))
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features())

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 80.0  # abs(0.9 - 0.5) * 200


def test_evaluate_maps_low_probability_to_bearish(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.1))
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features())

    assert signal.direction == Direction.BEARISH
    assert signal.confidence == 80.0


def test_evaluate_maps_near_50_50_probability_to_neutral(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.52))
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features())

    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0


def test_evaluate_returns_neutral_when_model_never_saw_the_up_class(tmp_path: Path) -> None:
    # A model trained on a single-class sample (e.g. only losses) has no
    # "up" column in predict_proba at all -- must not crash or silently
    # read the wrong column as "up".
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.9, classes=[0]))
    strategy = MLStrategy(model_dir=tmp_path)

    signal = strategy.evaluate(_features())

    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0


def test_model_is_loaded_from_disk_only_once_per_symbol_timeframe(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.9))
    strategy = MLStrategy(model_dir=tmp_path)

    strategy.evaluate(_features())
    strategy.evaluate(_features())

    # Reaching into the "private" cache is test-only introspection of the
    # loading behavior, not a public API guarantee.
    cached_model = strategy._models[(Symbol.XAUUSD.value, Timeframe.H1.value)]
    assert cached_model.call_count == 2  # predict_proba called each time, but it's the same loaded object


def test_different_symbol_timeframe_pairs_use_different_models(tmp_path: Path) -> None:
    _save_model(tmp_path, Symbol.XAUUSD, Timeframe.H1, _FakeClassifier(0.9))
    _save_model(tmp_path, Symbol.EURUSD, Timeframe.H1, _FakeClassifier(0.1))
    strategy = MLStrategy(model_dir=tmp_path)

    xauusd_signal = strategy.evaluate(_features(symbol=Symbol.XAUUSD))
    eurusd_signal = strategy.evaluate(_features(symbol=Symbol.EURUSD))

    assert xauusd_signal.direction == Direction.BULLISH
    assert eurusd_signal.direction == Direction.BEARISH
