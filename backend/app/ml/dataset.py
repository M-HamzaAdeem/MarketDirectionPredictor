"""Builds (features, label) training examples for the ML prediction
strategy — a walk-forward pass over historical candles, structurally
identical to `run_prediction_backtest`'s loop: at each step, build a
`FeatureSet` from the trailing `window` candles and label it against
whether the very next candle's close ended up higher (1) or not (0).

Rows where `feature_vector()` returns None (not enough indicator history
yet) are skipped — same "insufficient data" gate `RuleBasedStrategy`/
`MLStrategy` both apply, just enforced here at training-set-construction
time instead of prediction time.
"""

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.features.feature_builder import build_feature_set
from app.ml.features import feature_vector
from app.prediction.engine import CANDLE_WINDOW


def build_training_examples(
    symbol: Symbol,
    timeframe: Timeframe,
    candles: list[Candle],
    window: int = CANDLE_WINDOW,
) -> tuple[list[list[float]], list[int]]:
    """`candles` must be closed candles in ascending open_time order."""
    features_rows: list[list[float]] = []
    labels: list[int] = []

    for i in range(window, len(candles)):
        window_candles = candles[i - window : i]
        features = build_feature_set(symbol, timeframe, window_candles)
        vector = feature_vector(features)
        if vector is None:
            continue

        next_candle = candles[i]
        label = 1 if next_candle.close > window_candles[-1].close else 0
        features_rows.append(vector)
        labels.append(label)

    return features_rows, labels
