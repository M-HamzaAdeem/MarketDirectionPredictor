"""The /ws endpoint. v1 is broadcast-only — the server pushes price,
prediction, and feed-status updates; it doesn't act on client messages,
it just drains them so the connection stays alive until the client
disconnects.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.websocket_messages import FeedStatusMessage

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager = websocket.app.state.connection_manager
    await manager.connect(websocket)

    feed_service = websocket.app.state.feed_service
    await websocket.send_json(
        FeedStatusMessage(status=feed_service.status, timestamp=datetime.now(UTC)).model_dump(mode="json")
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
