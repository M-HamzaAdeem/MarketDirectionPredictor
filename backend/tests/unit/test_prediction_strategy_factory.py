from app.core.config import Settings
from app.core.constants import PredictionStrategyKind
from app.prediction.factory import create_strategy
from app.prediction.ml_strategy import MLStrategy
from app.prediction.rule_based import RuleBasedStrategy


def test_creates_rule_based_strategy_by_default() -> None:
    strategy = create_strategy(Settings())
    assert isinstance(strategy, RuleBasedStrategy)


def test_creates_ml_strategy_when_configured() -> None:
    settings = Settings(prediction_strategy=PredictionStrategyKind.ML, ml_model_dir="data/models")
    strategy = create_strategy(settings)
    assert isinstance(strategy, MLStrategy)
