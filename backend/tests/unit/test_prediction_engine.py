from datetime import UTC, datetime, timedelta

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.features.feature_builder import FeatureSet
from app.prediction.base import PredictionSignal, PredictionStrategy
from app.prediction.engine import PredictionEngine


class _StubStrategy(PredictionStrategy):
    def __init__(self, signal: PredictionSignal) -> None:
        self._signal = signal
        self.received_features: FeatureSet | None = None

    def evaluate(self, features: FeatureSet) -> PredictionSignal:
        self.received_features = features
        return self._signal


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


def test_engine_assembles_a_prediction_from_the_strategy_signal_and_latest_close() -> None:
    signal = PredictionSignal(direction=Direction.BULLISH, confidence=75.0, reason="test reason")
    strategy = _StubStrategy(signal)
    engine = PredictionEngine(strategy)
    candles = _make_candles([100.0, 101.0, 102.0])

    before = datetime.now(UTC)
    prediction = engine.run(Symbol.XAUUSD, Timeframe.M1, candles)
    after = datetime.now(UTC)

    assert prediction.symbol == Symbol.XAUUSD
    assert prediction.timeframe == Timeframe.M1
    assert prediction.direction == Direction.BULLISH
    assert prediction.confidence == 75.0
    assert prediction.reason == "test reason"
    assert prediction.price == 102.0
    assert before <= prediction.timestamp <= after


def test_engine_passes_a_real_feature_set_built_from_the_candles_to_the_strategy() -> None:
    strategy = _StubStrategy(PredictionSignal(direction=Direction.NEUTRAL, confidence=0.0, reason=""))
    engine = PredictionEngine(strategy)
    candles = _make_candles([100.0, 101.0, 102.0])

    engine.run(Symbol.XAUUSD, Timeframe.M1, candles)

    assert strategy.received_features is not None
    assert strategy.received_features.latest_close == 102.0
    assert strategy.received_features.symbol == Symbol.XAUUSD
