"""Walk-forward backtest of a direction-predicting PredictionStrategy over
real historical candles for a single symbol/timeframe. Defaults to the
Phase 3 rule-based strategy, but accepts any PredictionStrategy (e.g. the
ML strategy — see app/ml/) so both can be scored with the exact same
methodology for an honest comparison.

Scores each non-neutral prediction against whether the very next candle's
close actually moved in the predicted direction — the simplest defensible
read of "did this short-term direction call pan out," matching PROJECT.md's
"short-term market direction" framing. NEUTRAL predictions are excluded
from accuracy scoring (there's no direction to have been right or wrong
about), the same convention `performanceStats.ts` already uses to exclude
OPEN/EXPIRED signals from win-rate.

This backtest is what closes TD-2 (confidence calibration) with real
evidence: run it, then compare `direction_accuracy` against what the
predictor's own average confidence claims — see docs/prediction-method.md.
"""

from dataclasses import dataclass
from datetime import datetime

from app.core.constants import Direction, Symbol, Timeframe
from app.feeds.base import Candle
from app.prediction.base import PredictionStrategy
from app.prediction.engine import CANDLE_WINDOW, PredictionEngine
from app.prediction.rule_based import RuleBasedStrategy


@dataclass(frozen=True, slots=True)
class PredictionBacktestSummary:
    symbol: Symbol
    timeframe: Timeframe
    range_start: datetime | None
    range_end: datetime | None
    total_predictions: int
    correct: int
    incorrect: int
    neutral_skipped: int
    direction_accuracy: float


def run_prediction_backtest(
    symbol: Symbol,
    timeframe: Timeframe,
    candles: list[Candle],
    window: int = CANDLE_WINDOW,
    strategy: PredictionStrategy | None = None,
) -> PredictionBacktestSummary:
    """`candles` must be closed candles in ascending open_time order.
    `window` defaults to the real live window — overridable so tests can
    exercise this with small fixtures instead of needing 100+ candles.
    `strategy` defaults to a fresh `RuleBasedStrategy()`."""
    engine = PredictionEngine(strategy if strategy is not None else RuleBasedStrategy())
    correct = incorrect = neutral_skipped = 0

    for i in range(window, len(candles)):
        prediction_window = candles[i - window : i]
        prediction = engine.run(symbol, timeframe, prediction_window)
        next_candle = candles[i]

        if prediction.direction == Direction.NEUTRAL:
            neutral_skipped += 1
            continue

        # An exactly flat close counts as "not up" — on real float OHLC
        # data this is effectively never hit, so it doesn't skew results
        # in practice, but it does mean a BULLISH call on a dead-flat
        # close scores incorrect while a BEARISH one scores correct.
        actual_up = next_candle.close > prediction_window[-1].close
        predicted_up = prediction.direction == Direction.BULLISH
        if actual_up == predicted_up:
            correct += 1
        else:
            incorrect += 1

    scored = correct + incorrect
    has_scored_range = len(candles) > window
    return PredictionBacktestSummary(
        symbol=symbol,
        timeframe=timeframe,
        range_start=candles[window].open_time if has_scored_range else None,
        range_end=candles[-1].close_time if has_scored_range else None,
        total_predictions=scored + neutral_skipped,
        correct=correct,
        incorrect=incorrect,
        neutral_skipped=neutral_skipped,
        direction_accuracy=round(correct / scored, 4) if scored else 0.0,
    )
