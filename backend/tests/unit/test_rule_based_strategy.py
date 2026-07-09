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


def test_structure_alone_decides_direction_but_confidence_is_capped_by_evidence_available() -> None:
    # Structure (weight 2) is the only vote available out of a possible 5 total
    # weight -> even a fully unanimous vote can't read as full confidence,
    # since 3/5 of the evidence this strategy considers wasn't checked at all.
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(_features(structure=Direction.BULLISH))

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 40.0
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
    # score = -2 + 1 + 1 + 1 = 1 over total weight 5 -> bullish at 20% confidence.
    # All four indicators are present here (full evidence), so this exercises
    # the pure agreement side of the calibration without any evidence discount.
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(
        _features(structure=Direction.BEARISH, sma_fast=11.0, sma_slow=10.0, rsi=65.0, momentum=1.0)
    )

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 20.0


def test_full_agreement_with_full_evidence_reads_as_100_percent_confidence() -> None:
    # All four indicators present and unanimous -- the one case where evidence
    # is complete (4/4 weight available), so confidence isn't discounted at all.
    strategy = RuleBasedStrategy()
    signal = strategy.evaluate(
        _features(structure=Direction.BULLISH, sma_fast=11.0, sma_slow=10.0, rsi=65.0, momentum=1.0)
    )

    assert signal.direction == Direction.BULLISH
    assert signal.confidence == 100.0


def test_rsi_threshold_boundaries() -> None:
    strategy = RuleBasedStrategy()

    bullish = strategy.evaluate(_features(rsi=60.0))
    bearish = strategy.evaluate(_features(rsi=40.0))
    neutral = strategy.evaluate(_features(rsi=50.0))

    assert "RSI 60 bullish" in bullish.reason
    assert "RSI 40 bearish" in bearish.reason
    assert "RSI 50 neutral" in neutral.reason


def test_excluding_missing_indicators_gives_the_same_confidence_as_counting_them_neutral() -> None:
    # A neutral (zero) vote contributes nothing to score, and confidence is
    # scaled against the constant _TOTAL_POSSIBLE_WEIGHT rather than the
    # weight of votes present -- so excluding vs. neutral-including an
    # unavailable indicator doesn't actually change score or confidence.
    # The real reason to exclude rather than neutral-vote is keeping
    # `reason` truthful (see the module docstring), verified separately by
    # test_rsi_threshold_boundaries and friends never seeing a fabricated
    # fragment for an indicator that wasn't computed.
    from app.prediction.rule_based import _combine

    excluded = _combine([(2.0, 1.0, "structure bullish")])
    neutral_included = _combine(
        [
            (2.0, 1.0, "structure bullish"),
            (1.0, 0.0, "trend unavailable"),
            (1.0, 0.0, "rsi unavailable"),
            (1.0, 0.0, "momentum unavailable"),
        ]
    )

    assert excluded.confidence == neutral_included.confidence == 40.0
    assert excluded.direction == neutral_included.direction == Direction.BULLISH


def test_a_feature_set_with_absolutely_no_signal_returns_insufficient_data() -> None:
    # This can't happen via _structure_signal (always contributes), so exercise
    # _combine's empty-votes branch directly through the private helper.
    from app.prediction.rule_based import _combine

    signal = _combine([])
    assert signal.direction == Direction.NEUTRAL
    assert signal.confidence == 0.0
    assert signal.reason == "insufficient data"
