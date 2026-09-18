from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from typing import Dict

logger = logging.getLogger(__name__)
ws_router = APIRouter()

class EmergencyConnectionManager:
    def __init__(self):
        # Maps session_id to WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for Emergency Session: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for Emergency Session: {session_id}")

    async def broadcast_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")

manager = EmergencyConnectionManager()

@ws_router.websocket("/emergency/{session_id}")
async def emergency_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # We expect to receive telemetry from the user's device
            data = await websocket.receive_json()
            logger.info(f"[Emergency WS {session_id}] Received data: {data}")
            # Echo back to confirm receipt, or process it
            await manager.broadcast_to_session(session_id, {"status": "received", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(session_id)
