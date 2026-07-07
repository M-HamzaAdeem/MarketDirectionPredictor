"""Thin translation layer between domain events (a tick, a fresh
prediction, a feed-status change, a new ICT signal) and the WebSocket wire
format. Keeps ConnectionManager and message-schema details out of
FeedService, PredictionService, and SignalService."""

from datetime import UTC, datetime

from app.core.constants import FeedStatus
from app.feeds.base import Tick
from app.prediction.base import Prediction
from app.prediction.signal import Signal
from app.schemas.websocket_messages import (
    FeedStatusMessage,
    PredictionMessage,
    PriceMessage,
    SignalMessage,
)
from app.services.connection_manager import ConnectionManager


class BroadcastService:
    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def broadcast_price(self, tick: Tick) -> None:
        await self._connection_manager.broadcast(
            PriceMessage(symbol=tick.symbol, price=tick.price, timestamp=tick.timestamp)
        )

    async def broadcast_prediction(self, prediction: Prediction) -> None:
        await self._connection_manager.broadcast(
            PredictionMessage(
                symbol=prediction.symbol,
                timeframe=prediction.timeframe,
                direction=prediction.direction,
                confidence=prediction.confidence,
                reason=prediction.reason,
                price=prediction.price,
                timestamp=prediction.timestamp,
            )
        )

    async def broadcast_feed_status(self, status: FeedStatus) -> None:
        await self._connection_manager.broadcast(FeedStatusMessage(status=status, timestamp=datetime.now(UTC)))

    async def broadcast_signal(self, signal: Signal) -> None:
        await self._connection_manager.broadcast(
            SignalMessage(
                symbol=signal.symbol,
                direction=signal.direction,
                entry=signal.entry,
                stop=signal.stop,
                target=signal.target,
                risk_reward=signal.risk_reward,
                reason=signal.reason,
                opened_at=signal.opened_at,
            )
        )
