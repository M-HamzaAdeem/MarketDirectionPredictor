from app.core.constants import Direction, Symbol, Timeframe
from app.features.feature_builder import FeatureSet
from app.prediction.rule_based import RuleBasedStrategy


def _features(**overrides: object) -> FeatureSet:
    defaults: dict[str, object] = {
        "symbol": Symbol.XAUUSD,
        "timeframe": Timeframe.M1,
        "latest_close": 2350.0,
        "sma_fast": None,
        "sma_slow": None,
        "rsi": None,
        "atr": None,
        "momentum": None,
        "volatility": None,
        "structure": Direction.NEUTRAL,
    }
    defaults.update(overrides)
    return FeatureSet(**defaults)  # type: ignore[arg-type]


def test_structure_alone_decides_direction_when_no_other_indicator_is_available() -> None:
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(_features(structure=Direction.BULLISH))

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 100.0
    assert "structure bullish" in signal.reason


def test_all_neutral_signals_produce_a_neutral_prediction() -> None:
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(
        _features(structure=Direction.NEUTRAL, sma_fast=10.0, sma_slow=10.0, rsi=50.0, momentum=0.0)
    )

    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0


def test_conflicting_signals_are_resolved_by_weighted_score() -> None:
    # structure bearish (weight 2, vote -1) vs. trend/RSI/momentum all bullish (weight 1 each, vote +1)
    # score = -2 + 1 + 1 + 1 = 1 over total weight 5 -> bullish at 20% confidence
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(
        _features(structure=Direction.BEARISH, sma_fast=11.0, sma_slow=10.0, rsi=65.0, momentum=1.0)
    )

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 20.0


def test_rsi_threshold_boundaries() -> None:
    strategy = RuleBasedStrategy()

    bullish = strategy.evaluate(_features(rsi=60.0))
    bearish = strategy.evaluate(_features(rsi=40.0))
    neutral = strategy.evaluate(_features(rsi=50.0))

    assert "RSI 60 bullish" in bullish.reason
    assert "RSI 40 bearish" in bearish.reason
    assert "RSI 50 neutral" in neutral.reason


def test_missing_indicators_are_excluded_from_the_vote_not_treated_as_neutral() -> None:
    # Only structure (bullish) is available; sma/rsi/momentum are None (insufficient history).
    strategy = RuleBasedStrategy()
    with_missing = strategy.evaluate(_features(structure=Direction.BULLISH))

    # If missing indicators counted as neutral (vote 0, but still added to total_weight),
    # confidence would drop below 100. It must not.
    assert with_missing.confidence == 100.0


def test_a_feature_set_with_absolutely_no_signal_returns_insufficient_data() -> None:
    # This can't happen via _structure_signal (always contributes), so exercise
    # _combine's empty-votes branch directly through the private helper.
    from app.prediction.rule_based import _combine

    signal = _combine([])
    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0
    assert signal.reason == "insufficient data"
