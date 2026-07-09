"""Maps a DataSource to the ORM model its pipeline's repository should use.

The single place this mapping is defined — routers and main.py both import
these instead of each hand-rolling their own `if source == ...` branch,
so a third source only needs adding here once."""

from app.core.constants import DataSource
from app.storage.models import (
    CandleColumns,
    CandleORM,
    PredictionColumns,
    PredictionORM,
    SignalColumns,
    SignalORM,
    TradingViewCandleORM,
    TradingViewPredictionORM,
    TradingViewSignalORM,
)

_CANDLE_MODELS: dict[DataSource, type[CandleColumns]] = {
    DataSource.TWELVE_DATA: CandleORM,
    DataSource.TRADINGVIEW: TradingViewCandleORM,
}
_PREDICTION_MODELS: dict[DataSource, type[PredictionColumns]] = {
    DataSource.TWELVE_DATA: PredictionORM,
    DataSource.TRADINGVIEW: TradingViewPredictionORM,
}
_SIGNAL_MODELS: dict[DataSource, type[SignalColumns]] = {
    DataSource.TWELVE_DATA: SignalORM,
    DataSource.TRADINGVIEW: TradingViewSignalORM,
}


def candle_model_for(source: DataSource) -> type[CandleColumns]:
    return _CANDLE_MODELS[source]


def prediction_model_for(source: DataSource) -> type[PredictionColumns]:
    return _PREDICTION_MODELS[source]


def signal_model_for(source: DataSource) -> type[SignalColumns]:
    return _SIGNAL_MODELS[source]
