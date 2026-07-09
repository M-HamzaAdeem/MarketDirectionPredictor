from app.api.source_models import candle_model_for, prediction_model_for, signal_model_for
from app.core.constants import DataSource
from app.storage.models import (
    CandleORM,
    PredictionORM,
    SignalORM,
    TradingViewCandleORM,
    TradingViewPredictionORM,
    TradingViewSignalORM,
)


def test_candle_model_for_maps_both_sources() -> None:
    assert candle_model_for(DataSource.TWELVE_DATA) is CandleORM
    assert candle_model_for(DataSource.TRADINGVIEW) is TradingViewCandleORM


def test_prediction_model_for_maps_both_sources() -> None:
    assert prediction_model_for(DataSource.TWELVE_DATA) is PredictionORM
    assert prediction_model_for(DataSource.TRADINGVIEW) is TradingViewPredictionORM


def test_signal_model_for_maps_both_sources() -> None:
    assert signal_model_for(DataSource.TWELVE_DATA) is SignalORM
    assert signal_model_for(DataSource.TRADINGVIEW) is TradingViewSignalORM
