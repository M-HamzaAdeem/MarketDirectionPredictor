"""Registry of connected dashboard WebSocket clients.

Broadcasts are best-effort: a client whose send fails (closed connection,
slow consumer) is dropped rather than blocking or failing the rest of the
broadcast.
"""

import logging

from fastapi import WebSocket

from app.schemas.websocket_messages import WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: WebSocketMessage) -> None:
        payload = message.model_dump(mode="json")
        dead: list[WebSocket] = []
        for connection in list(self._connections):  # snapshot: safe under concurrent connect/disconnect
            try:
                await connection.send_json(payload)
            except Exception:
                logger.debug("Dropping unresponsive WebSocket client", exc_info=True)
                dead.append(connection)

        for connection in dead:
            self.disconnect(connection)
