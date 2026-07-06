"""Rule-based v1 prediction strategy: combines market structure, trend
(SMA crossover), RSI, and momentum into a weighted direction vote.

This is a heuristic, not a fitted model — the weights and thresholds below
are initial, documented choices (see docs/prediction-method.md), not tuned
against real outcomes yet. An ML strategy can replace this later behind
the same PredictionStrategy interface without touching the engine or API.

An indicator that isn't available yet (not enough candle history) is
excluded from the vote entirely, rather than counted as neutral — it
shouldn't silently drag confidence down just because the symbol is new.
"""

from app.core.constants import Direction
from app.features.feature_builder import FeatureSet
from app.prediction.base import PredictionSignal, PredictionStrategy

_STRUCTURE_WEIGHT = 2.0
_TREND_WEIGHT = 1.0
_RSI_WEIGHT = 1.0
_MOMENTUM_WEIGHT = 1.0

_RSI_BULLISH_THRESHOLD = 60.0
_RSI_BEARISH_THRESHOLD = 40.0

_Vote = tuple[float, float, str]  # (weight, vote in [-1, 0, 1], reason fragment)


class RuleBasedStrategy(PredictionStrategy):
    def evaluate(self, features: FeatureSet) -> PredictionSignal:
        votes: list[_Vote] = [(_STRUCTURE_WEIGHT, *_structure_signal(features))]

        for weight, signal in (
            (_TREND_WEIGHT, _trend_signal(features)),
            (_RSI_WEIGHT, _rsi_signal(features)),
            (_MOMENTUM_WEIGHT, _momentum_signal(features)),
        ):
            if signal is not None:
                votes.append((weight, *signal))

        return _combine(votes)


def _structure_signal(features: FeatureSet) -> tuple[float, str]:
    if features.structure == Direction.BULLISH:
        return 1.0, "structure bullish"
    if features.structure == Direction.BEARISH:
        return -1.0, "structure bearish"
    return 0.0, "structure neutral"


def _trend_signal(features: FeatureSet) -> tuple[float, str] | None:
    if features.sma_fast is None or features.sma_slow is None:
        return None
    if features.sma_fast > features.sma_slow:
        return 1.0, "fast SMA above slow SMA"
    if features.sma_fast < features.sma_slow:
        return -1.0, "fast SMA below slow SMA"
    return 0.0, "SMA fast/slow flat"


def _rsi_signal(features: FeatureSet) -> tuple[float, str] | None:
    if features.rsi is None:
        return None
    if features.rsi >= _RSI_BULLISH_THRESHOLD:
        return 1.0, f"RSI {features.rsi:.0f} bullish"
    if features.rsi <= _RSI_BEARISH_THRESHOLD:
        return -1.0, f"RSI {features.rsi:.0f} bearish"
    return 0.0, f"RSI {features.rsi:.0f} neutral"


def _momentum_signal(features: FeatureSet) -> tuple[float, str] | None:
    if features.momentum is None:
        return None
    if features.momentum > 0:
        return 1.0, "positive momentum"
    if features.momentum < 0:
        return -1.0, "negative momentum"
    return 0.0, "flat momentum"


def _combine(votes: list[_Vote]) -> PredictionSignal:
    if not votes:
        return PredictionSignal(direction=Direction.NEUTRAL, confidence=0.0, reason="insufficient data")

    total_weight = sum(weight for weight, _, _ in votes)
    score = sum(weight * vote for weight, vote, _ in votes)
    confidence = min(100.0, abs(score) / total_weight * 100.0) if total_weight else 0.0

    if score > 0:
        direction = Direction.BULLISH
    elif score < 0:
        direction = Direction.BEARISH
    else:
        direction = Direction.NEUTRAL

    reason = "; ".join(reason for _, _, reason in votes)
    return PredictionSignal(direction=direction, confidence=round(confidence, 1), reason=reason)
