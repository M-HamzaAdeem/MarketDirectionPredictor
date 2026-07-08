from datetime import UTC, datetime, timedelta

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.backtesting.prediction_backtest import run_prediction_backtest

_WINDOW = 20  # RuleBasedStrategy needs ~20 candles before structure/RSI/momentum produce a real (non-neutral) vote


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


def test_correct_bullish_call_when_price_keeps_rising() -> None:
    prices = [100.0 + i * 0.5 for i in range(_WINDOW)]
    prices.append(prices[-1] + 0.5)  # continues rising -> the bullish call was correct

    summary = run_prediction_backtest(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert summary.total_predictions == 1
    assert summary.correct == 1
    assert summary.incorrect == 0
    assert summary.direction_accuracy == 1.0


def test_incorrect_call_when_price_reverses() -> None:
    prices = [100.0 + i * 0.5 for i in range(_WINDOW)]
    prices.append(prices[-1] + 0.5)  # correct bullish call
    prices.append(prices[-1] - 5.0)  # sharp reversal -> the next bullish call was wrong

    summary = run_prediction_backtest(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert summary.total_predictions == 2
    assert summary.correct == 1
    assert summary.incorrect == 1
    assert summary.direction_accuracy == 0.5


def test_neutral_predictions_are_skipped_not_scored() -> None:
    # Flat, uneventful prices give a NEUTRAL call at every step (no strong
    # structure/trend/RSI/momentum vote) — none of these should count
    # toward direction_accuracy either way.
    prices = [100.0] * (_WINDOW + 5)

    summary = run_prediction_backtest(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert summary.correct == 0
    assert summary.incorrect == 0
    assert summary.neutral_skipped == 5
    assert summary.direction_accuracy == 0.0  # nothing scored, not "0% accurate"


def test_fewer_candles_than_the_window_produces_an_empty_summary() -> None:
    prices = [100.0 + i for i in range(_WINDOW - 1)]  # one short of a single full window

    summary = run_prediction_backtest(Symbol.XAUUSD, Timeframe.M1, _candles(prices), window=_WINDOW)

    assert summary.total_predictions == 0
    assert summary.range_start is None
    assert summary.range_end is None
    assert summary.direction_accuracy == 0.0
