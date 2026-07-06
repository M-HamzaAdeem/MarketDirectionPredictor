from datetime import UTC, datetime

from app.core.constants import Symbol
from app.schemas.websocket_messages import PriceMessage
from app.services.connection_manager import ConnectionManager


class _FakeWebSocket:
    def __init__(self, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict] = []
        self._fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        if self._fail_on_send:
            raise RuntimeError("simulated dead connection")
        self.sent.append(data)


def _price_message(price: float = 2350.0) -> PriceMessage:
    return PriceMessage(symbol=Symbol.XAUUSD, price=price, timestamp=datetime.now(UTC))


async def test_connect_accepts_and_registers_the_websocket() -> None:
    manager = ConnectionManager()
    websocket = _FakeWebSocket()

    await manager.connect(websocket)

    assert websocket.accepted


async def test_broadcast_sends_to_every_connected_client() -> None:
    manager = ConnectionManager()
    first, second = _FakeWebSocket(), _FakeWebSocket()
    await manager.connect(first)
    await manager.connect(second)

    await manager.broadcast(_price_message())

    assert len(first.sent) == 1
    assert len(second.sent) == 1
    assert first.sent[0]["type"] == "price"
    assert first.sent[0]["symbol"] == "XAUUSD"


async def test_broadcast_drops_a_client_whose_send_fails() -> None:
    manager = ConnectionManager()
    healthy = _FakeWebSocket()
    dead = _FakeWebSocket(fail_on_send=True)
    await manager.connect(healthy)
    await manager.connect(dead)

    await manager.broadcast(_price_message())
    await manager.broadcast(_price_message(price=2351.0))

    assert len(healthy.sent) == 2


async def test_disconnect_removes_a_registered_client() -> None:
    manager = ConnectionManager()
    websocket = _FakeWebSocket()
    await manager.connect(websocket)

    manager.disconnect(websocket)
    await manager.broadcast(_price_message())

    assert websocket.sent == []
