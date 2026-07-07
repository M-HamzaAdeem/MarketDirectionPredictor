"""WebSocket message envelopes broadcast to connected dashboard clients.
The `type` literal discriminates the payload so the frontend can dispatch
on shape without guessing."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.constants import Direction, FeedStatus, Symbol, Timeframe


class PriceMessage(BaseModel):
    type: Literal["price"] = "price"
    symbol: Symbol
    price: float
    timestamp: datetime


class PredictionMessage(BaseModel):
    type: Literal["prediction"] = "prediction"
    symbol: Symbol
    timeframe: Timeframe
    direction: Direction
    confidence: float
    reason: str
    price: float
    timestamp: datetime


class FeedStatusMessage(BaseModel):
    type: Literal["feed_status"] = "feed_status"
    status: FeedStatus
    timestamp: datetime


class SignalMessage(BaseModel):
    type: Literal["signal"] = "signal"
    symbol: Symbol
    direction: Direction
    entry: float
    stop: float
    target: float
    risk_reward: float
    reason: str
    opened_at: datetime


WebSocketMessage = PriceMessage | PredictionMessage | FeedStatusMessage | SignalMessage
