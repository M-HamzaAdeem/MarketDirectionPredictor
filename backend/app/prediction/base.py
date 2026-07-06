"""Prediction domain types and the PredictionStrategy contract.

Every strategy (rule-based v1, ML later) implements this interface so the
engine, repository, and API never depend on a concrete strategy — swapping
in an ML model later is a new class here, not a change anywhere else.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.core.constants import Direction, Symbol, Timeframe
from app.features.feature_builder import FeatureSet


@dataclass(frozen=True, slots=True)
class PredictionSignal:
    direction: Direction
    confidence: float
    reason: str


@dataclass(frozen=True, slots=True)
class Prediction:
    symbol: Symbol
    timeframe: Timeframe
    direction: Direction
    confidence: float
    reason: str
    price: float
    timestamp: datetime


class PredictionStrategy(ABC):
    @abstractmethod
    def evaluate(self, features: FeatureSet) -> PredictionSignal:
        """Turn a feature set into a direction/confidence/reason signal."""
