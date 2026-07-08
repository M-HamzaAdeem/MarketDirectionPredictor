"""Selects and constructs the configured PredictionStrategy.

The only place that branches on `Settings.prediction_strategy` — mirrors
`app/feeds/factory.py`'s pattern for feed providers: adding a new strategy
means a new class implementing `PredictionStrategy` plus one branch here,
never a second branch ladder scattered across calling code."""

from pathlib import Path

from app.core.config import Settings
from app.core.constants import PredictionStrategyKind
from app.prediction.base import PredictionStrategy
from app.prediction.ml_strategy import MLStrategy
from app.prediction.rule_based import RuleBasedStrategy


def create_strategy(settings: Settings) -> PredictionStrategy:
    if settings.prediction_strategy == PredictionStrategyKind.RULE_BASED:
        return RuleBasedStrategy()

    if settings.prediction_strategy == PredictionStrategyKind.ML:
        return MLStrategy(model_dir=Path(settings.ml_model_dir))

    raise ValueError(f"Unknown prediction_strategy: {settings.prediction_strategy!r}")
