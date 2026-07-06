"""Shared FastAPI dependency accessors for request handlers."""

from functools import lru_cache

from fastapi import Request

from app.prediction.engine import PredictionEngine
from app.prediction.rule_based import RuleBasedStrategy
from app.services.feed_service import FeedService


def get_feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service


@lru_cache
def get_prediction_engine() -> PredictionEngine:
    """Cached process-wide singleton — safe only because RuleBasedStrategy
    and PredictionEngine are both stateless. If a future strategy carries
    state or config, move this to app.state instead (see feed_service)."""
    return PredictionEngine(RuleBasedStrategy())
