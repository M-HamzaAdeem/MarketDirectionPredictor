from datetime import UTC, datetime, timedelta

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.ml.dataset import build_training_examples

_WINDOW = 30  # binding constraint is SMA_SLOW_PERIOD=30; every other indicator needs fewer candles


def _candles(prices: list[float]) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            symbol=Symbol.XAUUSD,
            timeframe=Timeframe.M1,
            open_time=base + timedelta(minutes=i),
            close_time=base + timedelta(minutes=i + 1),
            open=price,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            volume=1.0,
        )
        for i, price in enumerate(prices)
    ]


def test_labels_reflect_whether_the_next_candle_closed_higher() -> None:
    prices = [100.0 + i * 0.5 for i in range(_WINDOW)]
    prices.append(prices[-1] + 0.5)  # up -> label 1
    prices.append(prices[-1] - 5.0)  # down -> label 0

    features, labels = build_training_examples(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert labels == [1, 0]
    assert len(features) == 2
    assert len(features[0]) == 6  # matches app.ml.features.FEATURE_NAMES


def test_fewer_candles_than_window_plus_one_produces_no_examples() -> None:
    prices = [100.0 + i for i in range(_WINDOW)]  # exactly window candles, no "next" candle to label against

    features, labels = build_training_examples(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert features == []
    assert labels == []


def test_rows_with_insufficient_indicator_history_are_skipped() -> None:
    # window=5 is below SMA_SLOW_PERIOD (30), so every row's feature_vector
    # is None (sma_slow never populates) -- none of these should be kept.
    prices = [100.0 + i for i in range(10)]

    features, labels = build_training_examples(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=5)

    assert features == []
    assert labels == []
