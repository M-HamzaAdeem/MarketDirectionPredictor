"""Orchestrates a prediction run: builds a feature set from a window of
closed candles, asks the configured strategy for a signal, and assembles
the full Prediction. Thin glue — the strategy owns the actual reasoning,
and persistence is the caller's responsibility (see api/routers/predictions.py).
"""

from datetime import UTC, datetime

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.features.feature_builder import build_feature_set
from app.prediction.base import Prediction, PredictionStrategy

# How many recent closed candles to feed the engine per run — shared by
# every caller (on-demand REST, event-driven candle-close) so the window
# can't silently diverge between them.
CANDLE_WINDOW = 100


class PredictionEngine:
    def __init__(self, strategy: PredictionStrategy) -> None:
        self._strategy = strategy

    def run(self, symbol: Symbol, timeframe: Timeframe, candles: list[Candle]) -> Prediction:
        """`candles` must be closed candles in ascending open_time order."""
        features = build_feature_set(symbol, timeframe, candles)
        signal = self._strategy.evaluate(features)

        return Prediction(
            symbol=symbol,
            timeframe=timeframe,
            direction=signal.direction,
            confidence=signal.confidence,
            reason=signal.reason,
            price=features.latest_close,
            timestamp=datetime.now(UTC),
        )
