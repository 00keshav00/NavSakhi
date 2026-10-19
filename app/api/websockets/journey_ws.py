import asyncio
import json
import logging
from typing import Dict, Set, Optional
from collections import defaultdict
from starlette import status
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends

from app.services.ticket_service import ticket_service
from app.services.auth_service import AuthService
from app.services.journey_telemetry_service import telemetry_service
from app.services.journey_service import JourneyService
from app.repositories.journey_repository import JourneyRepository
from app.api.dependencies import get_journey_repository

router = APIRouter()
logger = logging.getLogger(__name__)

class JourneyConnectionManager:
    """
    Thread-safe connection manager for journey WebSocket streams.
    Enforces per-journey connection bounds and prevents unauthorized broadcast leakage.
    """
    def __init__(self, max_connections_per_journey: int = 5, max_total_connections: int = 1000):
        self.max_per_journey = max_connections_per_journey
        self.max_total = max_total_connections
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.connection_meta: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, journey_id: str, user_id: str):
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        if total_connections >= self.max_total:
            logger.warning("Journey WS connection rejected: global connection limit reached.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Server busy")
            return False

        if len(self.active_connections[journey_id]) >= self.max_per_journey:
            logger.warning(f"Journey WS connection rejected for {journey_id}: per-journey limit reached.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Too many connections")
            return False

        await websocket.accept()
        self.active_connections[journey_id].add(websocket)
        self.connection_meta[websocket] = {"journey_id": journey_id, "user_id": user_id}
        logger.info(f"Journey WebSocket connected: journey={journey_id}, user={user_id}")
        return True

    def disconnect(self, journey_id: str, websocket: WebSocket):
        if journey_id in self.active_connections:
            self.active_connections[journey_id].discard(websocket)
            if not self.active_connections[journey_id]:
                del self.active_connections[journey_id]
        self.connection_meta.pop(websocket, None)
        logger.info(f"Journey WebSocket disconnected: journey={journey_id}")

    async def send_personal_message(self, message: dict, journey_id: str):
        """Send message strictly to sockets connected to this journey."""
        if journey_id in self.active_connections:
            dead_sockets = set()
            for ws in list(self.active_connections[journey_id]):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to journey {journey_id}: {e}")
                    dead_sockets.add(ws)

            for ws in dead_sockets:
                self.disconnect(journey_id, ws)

    def is_connected(self, journey_id: str) -> bool:
        return journey_id in self.active_connections and len(self.active_connections[journey_id]) > 0

journey_manager = JourneyConnectionManager()

@router.websocket("/{journey_id}")
async def journey_websocket_endpoint(
    websocket: WebSocket,
    journey_id: str,
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    journey_repo: JourneyRepository = Depends(get_journey_repository)
):
    # 1. Reject any attempt to authenticate using long-lived JWT in query parameters
    if token:
        logger.warning(f"Journey WS rejected for {journey_id}: Query-parameter JWT authentication is disabled.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Query token authentication is disabled. Use single-use tickets.")
        return

    # Authenticate exclusively via single-use ticket
    if not ticket:
        logger.warning(f"Journey WS rejected for {journey_id}: Missing WebSocket ticket.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing single-use ticket.")
        return

    user_id = ticket_service.consume_ticket(ticket)
    if not user_id:
        logger.warning(f"Journey WS rejected for {journey_id}: Invalid, expired, or replayed ticket.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized: Invalid or expired ticket.")
        return

    # 2. Resource ownership check: load journey and verify user_id
    try:
        journey = await journey_repo.get_by_id(journey_id)
    except Exception as exc:
        logger.error(f"Error querying journey {journey_id}: {exc}")
        journey = None

    if not journey:
        logger.warning(f"Journey WS rejected: journey {journey_id} not found.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Journey not found")
        return

    if str(journey.user_id) != str(user_id):
        logger.warning(f"Journey WS rejected: user {user_id} does not own journey {journey_id}.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden: Resource ownership mismatch")
        return

    # 3. Establish connection
    connected = await journey_manager.connect(websocket, journey_id, str(user_id))
    if not connected:
        return

    # 4. Message processing loop with bounds and validation
    try:
        while True:
            raw_text = await websocket.receive_text()
            
            # Bound payload size (max 4KB)
            if len(raw_text) > 4096:
                await websocket.send_json({"error": "Payload size exceeded limit (max 4096 bytes)"})
                continue

            try:
                message = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Malformed JSON payload"})
                continue

            if not isinstance(message, dict):
                await websocket.send_json({"error": "Message must be a JSON object"})
                continue

            # Heartbeat ping/pong
            msg_type = message.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Prevent resource hijacking via payload
            if "journey_id" in message and str(message["journey_id"]) != str(journey_id):
                await websocket.send_json({"error": "Cannot change journey_id in message payload"})
                continue

            if "user_id" in message and str(message["user_id"]) != str(user_id):
                await websocket.send_json({"error": "Cannot spoof user_id in message payload"})
                continue

            # Reject untrusted client safety scores
            if "safety_score" in message:
                await websocket.send_json({"error": "Client-supplied safety scores are not accepted"})
                continue

            # Validate and process telemetry updates
            if msg_type in ["location_update", "telemetry"]:
                # Reload journey to obtain current state and planned routes
                current_journey = await journey_repo.get_by_id(journey_id)
                if not current_journey:
                    await websocket.send_json({"error": "Journey not found"})
                    continue

                is_valid, res = telemetry_service.process_telemetry_message(current_journey, message)
                if not is_valid:
                    await websocket.send_json({"error": res.get("error", "Invalid telemetry update"), **res})
                    continue

                try:
                    # Valid reading: Persist latest snapshot into journey progress
                    journey_service = JourneyService(journey_repo=journey_repo)
                    await journey_service.record_telemetry(journey_id, res["persistence"])

                    # Send acknowledgment to sender
                    ack_msg = res["ack"]
                    await websocket.send_json(ack_msg)
                except Exception as e:
                    logger.error(f"Error persisting telemetry for {journey_id}: {e}")
                    await websocket.send_json({"error": f"Internal error processing telemetry: {str(e)}"})
            else:
                await websocket.send_json({"status": "received", "type": msg_type or "unknown"})

    except WebSocketDisconnect:
        journey_manager.disconnect(journey_id, websocket)
    except Exception as exc:
        logger.warning(f"Journey WS connection error for {journey_id}: {exc}")
        journey_manager.disconnect(journey_id, websocket)
