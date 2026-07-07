from datetime import UTC, datetime

import pytest

from app.core.constants import Direction, FeedStatus, Symbol, Timeframe
from app.feeds.base import Tick
from app.prediction.base import Prediction
from app.prediction.signal import Signal, SignalStatus
from app.schemas.websocket_messages import FeedStatusMessage, PredictionMessage, PriceMessage, SignalMessage
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


def _signal(**overrides: object) -> Signal:
    defaults: dict[str, object] = {
        "id": 1,
        "symbol": Symbol.XAUUSD,
        "entry_timeframe": Timeframe.M15,
        "direction": Direction.BULLISH,
        "entry": 2350.0,
        "stop": 2345.0,
        "target": 2365.0,
        "risk_reward": 3.0,
        "reason": "test reason",
        "details": {},
        "opened_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Signal(**defaults)  # type: ignore[arg-type]


async def test_broadcast_signal_sends_a_signal_message_for_a_new_open_signal() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)

    await service.broadcast_signal(_signal(details={"poi_type": "fair_value_gap"}))

    message = manager.broadcasted[0]
    assert isinstance(message, SignalMessage)
    assert message.details == {"poi_type": "fair_value_gap"}
    assert message.id == 1
    assert message.direction == Direction.BULLISH
    assert message.risk_reward == 3.0
    assert message.reason == "test reason"
    assert message.status == SignalStatus.OPEN
    assert message.closed_at is None


async def test_broadcast_signal_sends_a_signal_message_for_a_resolved_signal() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)
    closed_at = datetime.now(UTC)

    await service.broadcast_signal(
        _signal(status=SignalStatus.WIN, closed_at=closed_at, realized_rr=3.0)
    )

    message = manager.broadcasted[0]
    assert message.status == SignalStatus.WIN
    assert message.closed_at == closed_at
    assert message.realized_rr == 3.0


async def test_broadcast_signal_rejects_an_unpersisted_signal() -> None:
    manager = _RecordingConnectionManager()
    service = BroadcastService(manager)

    with pytest.raises(ValueError, match="hasn't been persisted"):
        await service.broadcast_signal(_signal(id=None))
