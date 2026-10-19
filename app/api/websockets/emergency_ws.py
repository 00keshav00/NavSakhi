import logging
import json
from typing import Dict, Set, Optional
from collections import defaultdict
from starlette import status
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.ticket_service import ticket_service
from app.services.auth_service import AuthService
from app.services.emergency_session_service import emergency_session_registry

logger = logging.getLogger(__name__)
ws_router = APIRouter()

class EmergencyConnectionManager:
    """
    Manages active WebSocket connections for emergency SOS streams.
    Restricts broadcasts strictly to authorized participants of each specific emergency session.
    """
    def __init__(self, max_connections_per_session: int = 10, max_total_connections: int = 1000):
        self.max_per_session = max_connections_per_session
        self.max_total = max_total_connections
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.connection_meta: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        if total_connections >= self.max_total:
            logger.warning("Emergency WS rejected: global connection limit reached.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Server busy")
            return False

        if len(self.active_connections[session_id]) >= self.max_per_session:
            logger.warning(f"Emergency WS rejected for {session_id}: per-session limit reached.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Too many connections")
            return False

        await websocket.accept()
        self.active_connections[session_id].add(websocket)
        self.connection_meta[websocket] = {"session_id": session_id, "user_id": user_id}
        logger.info(f"Emergency WebSocket connected: session={session_id}, user={user_id}")
        return True

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        self.connection_meta.pop(websocket, None)
        logger.info(f"Emergency WebSocket disconnected: session={session_id}")

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast strictly to authorized sockets connected to this emergency session."""
        if session_id in self.active_connections:
            dead_sockets = set()
            for ws in list(self.active_connections[session_id]):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to session {session_id}: {e}")
                    dead_sockets.add(ws)

            for ws in dead_sockets:
                self.disconnect(session_id, ws)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self.active_connections and len(self.active_connections[session_id]) > 0

manager = EmergencyConnectionManager()

@ws_router.websocket("/emergency/{session_id}")
async def emergency_websocket(
    websocket: WebSocket,
    session_id: str,
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    # 1. Reject any attempt to authenticate using long-lived JWT in query parameters
    if token:
        logger.warning(f"Emergency WS rejected for {session_id}: Query-parameter JWT authentication is disabled.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Query token authentication is disabled. Use single-use tickets.")
        return

    # Authenticate exclusively via single-use ticket
    if not ticket:
        logger.warning(f"Emergency WS rejected for {session_id}: Missing WebSocket ticket.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing single-use ticket.")
        return

    user_id = ticket_service.consume_ticket(ticket)
    if not user_id:
        logger.warning(f"Emergency WS rejected for {session_id}: Invalid, expired, or replayed ticket.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized: Invalid or expired ticket.")
        return

    # 2. Enforce emergency session authorization
    if not emergency_session_registry.is_authorized(session_id, str(user_id)):
        logger.warning(f"Emergency WS rejected: User {user_id} not authorized for session {session_id}.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden: Unauthorized emergency session")
        return

    # 3. Establish connection
    connected = await manager.connect(websocket, session_id, str(user_id))
    if not connected:
        return

    # 4. Message processing loop with bounds and validation
    try:
        while True:
            raw_text = await websocket.receive_text()

            # Bound message size
            if len(raw_text) > 4096:
                await websocket.send_json({"error": "Payload size exceeded limit (max 4096 bytes)"})
                continue

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Malformed JSON payload"})
                continue

            if not isinstance(data, dict):
                await websocket.send_json({"error": "Message must be a JSON object"})
                continue

            # Heartbeat handling
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Prevent resource hijacking via payload
            if "session_id" in data and str(data["session_id"]) != str(session_id):
                await websocket.send_json({"error": "Cannot change session_id in message payload"})
                continue

            if "user_id" in data and str(data["user_id"]) != str(user_id):
                await websocket.send_json({"error": "Cannot spoof user_id in message payload"})
                continue

            # Validate coordinate bounds if coordinates are sent
            lat = data.get("lat") or data.get("latitude")
            lng = data.get("lng") or data.get("longitude")
            if lat is not None:
                try:
                    lat_val = float(lat)
                    if not (-90.0 <= lat_val <= 90.0):
                        await websocket.send_json({"error": "Latitude must be between -90 and 90"})
                        continue
                except (ValueError, TypeError):
                    await websocket.send_json({"error": "Invalid latitude format"})
                    continue

            if lng is not None:
                try:
                    lng_val = float(lng)
                    if not (-180.0 <= lng_val <= 180.0):
                        await websocket.send_json({"error": "Longitude must be between -180 and 180"})
                        continue
                except (ValueError, TypeError):
                    await websocket.send_json({"error": "Invalid longitude format"})
                    continue

            # Broadcast verified update strictly to authorized session participants
            broadcast_payload = {
                "status": "received",
                "session_id": session_id,
                "sender_user_id": str(user_id),
                "data": data
            }
            await manager.broadcast_to_session(session_id, broadcast_payload)

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as exc:
        logger.warning(f"Emergency WS connection error for {session_id}: {exc}")
        manager.disconnect(session_id, websocket)
