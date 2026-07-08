"""ML PredictionStrategy — a separate trained scikit-learn binary
classifier per (symbol, timeframe) pair, produced by `python -m
app.ml.train`. Loads lazily and caches per pair, keyed off whatever
`FeatureSet` it's asked to evaluate — `PredictionEngine`/`get_prediction_engine()`
stay a single, symbol/timeframe-agnostic singleton (same as
RuleBasedStrategy); this class is the one that's actually symbol/timeframe-
aware internally.

A missing model file (e.g. a symbol added after the last training run, or
training simply never having been run) returns NEUTRAL/0 confidence rather
than raising — PredictionStrategy.evaluate() has no error-signaling path,
and a missing model isn't a bug, just an untrained pair.
"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import joblib

from app.core.constants import Direction
from app.features.feature_builder import FeatureSet
from app.ml.features import feature_vector
from app.prediction.base import PredictionSignal, PredictionStrategy

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = Path("data/models")
# Predicted probability of "up" within this band of 0.5 counts as NEUTRAL —
# the model has no real edge, not a coin-flip worth acting on either way.
_NEUTRAL_BAND = 0.05
# Linear map from probability-distance-from-0.5 (range [0, 0.5]) to a
# confidence percentage (range [0, 100]) — the inverse of _NEUTRAL_BAND's
# 0.5 midpoint, hence 100.0 / 0.5.
_CONFIDENCE_SCALE = 100.0 / 0.5
_UP_LABEL = 1


class _BinaryClassifier(Protocol):
    classes_: Sequence[int]

    def predict_proba(self, X: list[list[float]]) -> list[list[float]]: ...


class MLStrategy(PredictionStrategy):
    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR) -> None:
        self._model_dir = model_dir
        self._models: dict[tuple[str, str], _BinaryClassifier | None] = {}

    def evaluate(self, features: FeatureSet) -> PredictionSignal:
        model = self._load_model(features.symbol.value, features.timeframe.value)
        if model is None:
            return PredictionSignal(
                direction=Direction.NEUTRAL,
                confidence=0.0,
                reason=f"no trained model for {features.symbol.value}/{features.timeframe.value}",
            )

        vector = feature_vector(features)
        if vector is None:
            return PredictionSignal(direction=Direction.NEUTRAL, confidence=0.0, reason="insufficient data")

        proba_up = _extract_up_probability(model, vector)
        return _signal_from_probability(proba_up)

    def _load_model(self, symbol: str, timeframe: str) -> _BinaryClassifier | None:
        key = (symbol, timeframe)
        if key not in self._models:
            self._models[key] = _load_from_disk(self._model_dir, symbol, timeframe)
        return self._models[key]


def _load_from_disk(model_dir: Path, symbol: str, timeframe: str) -> _BinaryClassifier | None:
    path = model_dir / f"{symbol}_{timeframe}.joblib"
    if not path.exists():
        return None
    try:
        return joblib.load(path)
    except Exception:
        logger.exception("Failed to load ML model from %s", path)
        return None


def _extract_up_probability(model: _BinaryClassifier, vector: list[float]) -> float:
    # Never assume predict_proba's column order — resolve the "up" class's
    # actual column via classes_. A model trained on a single-class sample
    # (only ever saw wins or only losses; _MIN_TRAINING_EXAMPLES makes this
    # unlikely but not impossible) won't have _UP_LABEL in classes_ at all;
    # treating that as an exact 50/50 keeps this NEUTRAL rather than
    # crashing or silently reading the wrong column as "up".
    classes = list(model.classes_)
    if _UP_LABEL not in classes:
        return 0.5
    proba_row = model.predict_proba([vector])[0]
    return float(proba_row[classes.index(_UP_LABEL)])


def _signal_from_probability(proba_up: float) -> PredictionSignal:
    distance_from_neutral = proba_up - 0.5

    if abs(distance_from_neutral) <= _NEUTRAL_BAND:
        return PredictionSignal(
            direction=Direction.NEUTRAL, confidence=0.0, reason=f"model probability {proba_up:.2f} near 50/50"
        )

    confidence = round(min(100.0, abs(distance_from_neutral) * _CONFIDENCE_SCALE), 1)
    if distance_from_neutral > 0:
        return PredictionSignal(
            direction=Direction.BULLISH, confidence=confidence, reason=f"model probability {proba_up:.2f} bullish"
        )
    return PredictionSignal(
        direction=Direction.BEARISH, confidence=confidence, reason=f"model probability {proba_up:.2f} bearish"
    )
