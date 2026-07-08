"""Shared FastAPI dependency accessors for request handlers."""

from functools import lru_cache

from fastapi import Request

from app.core.config import get_settings
from app.prediction.engine import PredictionEngine
from app.prediction.factory import create_strategy
from app.services.feed_service import FeedService


def get_feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service


@lru_cache
def get_prediction_engine() -> PredictionEngine:
    """Cached process-wide singleton — safe even for MLStrategy, which is
    symbol/timeframe-agnostic at construction and figures out which
    per-pair model to use from the FeatureSet it's asked to evaluate (see
    ml_strategy.py). If a future strategy needs per-request state, move
    this to app.state instead (see feed_service)."""
    return PredictionEngine(create_strategy(get_settings()))
