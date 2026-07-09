"""WebSocket message envelopes broadcast to connected dashboard clients.
The `type` literal discriminates the payload so the frontend can dispatch
on shape without guessing. Every message also carries `source` (which of
the two independent pipelines it came from) — required, not defaulted, so
a message can't be constructed and silently mislabeled outside of
BroadcastService, the one place that stamps it."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.core.constants import DataSource, Direction, FeedStatus, Symbol, Timeframe
from app.prediction.signal import SignalStatus


class PriceMessage(BaseModel):
    type: Literal["price"] = "price"
    source: DataSource
    symbol: Symbol
    price: float
    timestamp: datetime


class PredictionMessage(BaseModel):
    type: Literal["prediction"] = "prediction"
    source: DataSource
    symbol: Symbol
    timeframe: Timeframe
    direction: Direction
    confidence: float
    reason: str
    price: float
    timestamp: datetime


class FeedStatusMessage(BaseModel):
    type: Literal["feed_status"] = "feed_status"
    source: DataSource
    status: FeedStatus
    timestamp: datetime


class SignalMessage(BaseModel):
    """Broadcast both when a signal opens (status=OPEN) and again whenever
    SignalTracker resolves it (status=WIN/LOSS/EXPIRED) — the frontend
    keys on `id` to know whether to add a new entry or update one it
    already has."""

    type: Literal["signal"] = "signal"
    source: DataSource
    id: int
    symbol: Symbol
    entry_timeframe: Timeframe
    direction: Direction
    entry: float
    stop: float
    target: float
    risk_reward: float
    reason: str
    details: dict[str, Any]
    status: SignalStatus
    opened_at: datetime
    closed_at: datetime | None
    realized_rr: float | None


WebSocketMessage = PriceMessage | PredictionMessage | FeedStatusMessage | SignalMessage
