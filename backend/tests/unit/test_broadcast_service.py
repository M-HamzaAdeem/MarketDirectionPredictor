from datetime import UTC, datetime

from app.core.constants import Direction, FeedStatus, Symbol, Timeframe
from app.feeds.base import Tick
from app.prediction.base import Prediction
from app.schemas.websocket_messages import FeedStatusMessage, PredictionMessage, PriceMessage
from app.services.broadcast_service import BroadcastService


class _RecordingConnectionManager:
    def __init__(self) -> None:
        self.broadcasted: list[object] = []

    async def broadcast(self, message: object) -> None:
        self.broadcasted.append(message)


async def test_broadcast_price_sends_a_price_message() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)
    tick = Tick(symbol=Symbol.XAUUSD, price=2350.0, timestamp=datetime.now(UTC))

    await service.broadcast_price(tick)

    assert len(manager.broadcasted) == 1
    message = manager.broadcasted[0]
    assert isinstance(message, PriceMessage)
    assert message.symbol == Symbol.XAUUSD
    assert message.price == 2350.0


async def test_broadcast_prediction_sends_a_prediction_message() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)
    prediction = Prediction(
        symbol=Symbol.EURUSD,
        timeframe=Timeframe.M5,
        direction=Direction.BULLISH,
        confidence=80.0,
        reason="test reason",
        price=1.085,
        timestamp=datetime.now(UTC),
    )

    await service.broadcast_prediction(prediction)

    message = manager.broadcasted[0]
    assert isinstance(message, PredictionMessage)
    assert message.direction == Direction.BULLISH
    assert message.confidence == 80.0
    assert message.reason == "test reason"


async def test_broadcast_feed_status_sends_a_feed_status_message() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)

    await service.broadcast_feed_status(FeedStatus.MOCK)

    message = manager.broadcasted[0]
    assert isinstance(message, FeedStatusMessage)
    assert message.status == FeedStatus.MOCK
