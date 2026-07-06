"""Thin translation layer between domain events (a tick, a fresh
prediction, a feed-status change) and the WebSocket wire format. Keeps
ConnectionManager and message-schema details out of FeedService and
PredictionService."""

from datetime import UTC, datetime

from app.core.constants import FeedStatus
from app.feeds.base import Tick
from app.prediction.base import Prediction
from app.schemas.websocket_messages import FeedStatusMessage, PredictionMessage, PriceMessage
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
