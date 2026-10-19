import pytest
import time
from pathlib import Path
from bson import ObjectId
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.journey import Journey, Location, JourneyState, JourneyStateEnum
from app.services.auth_service import AuthService
from app.services.ticket_service import ticket_service
from app.services.emergency_session_service import emergency_session_registry
from app.api.websockets.journey_ws import journey_manager
from app.api.websockets.emergency_ws import manager as emergency_manager
from app.api.dependencies import get_user_repository, get_journey_repository

class InMemoryUserRepository:
    def __init__(self):
        self.users = {}

    async def get_by_email(self, email: str):
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_id(self, user_id: str):
        return self.users.get(str(user_id))

    async def create(self, user: User) -> User:
        user_id = str(ObjectId())
        user.id = ObjectId(user_id)
        self.users[user_id] = user
        return user


class InMemoryJourneyRepository:
    def __init__(self):
        self.journeys = {}

    async def get_by_id(self, journey_id: str):
        return self.journeys.get(str(journey_id))

    async def create(self, journey: Journey) -> Journey:
        j_id = str(ObjectId())
        journey.id = ObjectId(j_id)
        self.journeys[j_id] = journey
        return journey


@pytest.fixture
def ws_test_env():
    user_repo = InMemoryUserRepository()
    journey_repo = InMemoryJourneyRepository()

    ticket_service.clear()
    emergency_session_registry.clear()

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_journey_repository] = lambda: journey_repo

    client = TestClient(app, raise_server_exceptions=False)
    yield client, user_repo, journey_repo

    app.dependency_overrides.clear()
    ticket_service.clear()
    emergency_session_registry.clear()


# 1. Unauthenticated WebSocket connections are rejected
def test_unauthenticated_ws_rejected(ws_test_env):
    client, _, _ = ws_test_env
    fake_journey_id = str(ObjectId())
    fake_session_id = "sos_test_unauth"

    # Journey WS without ticket
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/journey/{fake_journey_id}"):
            pass
    assert exc_info.value.code == 1008

    # Emergency WS without ticket
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/emergency/{fake_session_id}"):
            pass
    assert exc_info.value.code == 1008


# 2. Long-lived JWT in ?token= is strictly rejected on both endpoints (Phase 2B.1 requirement)
def test_long_lived_jwt_token_query_rejected(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())

    # Create journey owned by user
    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    # Register emergency session for user
    session_id = "sos_jwt_test_session"
    emergency_session_registry.register_session(session_id=session_id, user_id=user_id)

    # Valid, active, properly signed JWT
    valid_jwt = AuthService.create_access_token(user_id=user_id, email="owner@safeshe.org")

    # Attempt to connect to Journey WS with ?token= -> must be rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info_j:
        with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?token={valid_jwt}"):
            pass
    assert exc_info_j.value.code == 1008

    # Attempt to connect to Emergency WS with ?token= -> must be rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info_e:
        with client.websocket_connect(f"/api/v1/ws/emergency/{session_id}?token={valid_jwt}"):
            pass
    assert exc_info_e.value.code == 1008


# 3. Invalid or tampered ticket is rejected
def test_invalid_ticket_rejected(ws_test_env):
    client, _, _ = ws_test_env
    fake_journey_id = str(ObjectId())

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/journey/{fake_journey_id}?ticket=invalid_bogus_ticket"):
            pass
    assert exc_info.value.code == 1008


# 4. Expired ticket is rejected
def test_expired_ticket_rejected(ws_test_env):
    client, _, _ = ws_test_env
    fake_journey_id = str(ObjectId())

    ticket_id = ticket_service.issue_ticket("user_123")
    ticket_service._tickets[ticket_id].expires_at = time.time() - 10

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/journey/{fake_journey_id}?ticket={ticket_id}"):
            pass
    assert exc_info.value.code == 1008


# 5. A single-use ticket cannot be replayed
def test_single_use_ticket_cannot_be_replayed(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())
    
    # Create valid journey owned by user
    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    # Issue single-use ticket
    ticket = ticket_service.issue_ticket(user_id)

    # First connection consumes ticket successfully
    with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket}") as ws:
        ws.send_text('{"type": "ping"}')
        data = ws.receive_json()
        assert data["type"] == "pong"

    # Second connection attempt with the SAME ticket must fail (replay rejection)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket}"):
            pass
    assert exc_info.value.code == 1008


# 6. An authenticated user can connect to an authorized resource
def test_authenticated_user_can_connect_to_authorized_resource(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())

    # Setup journey
    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    # Setup emergency session
    session_id = "sos_auth_test_123"
    emergency_session_registry.register_session(session_id=session_id, user_id=user_id)

    # Connect to journey WS
    ticket_j = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket_j}") as ws:
        ws.send_text('{"type": "ping"}')
        res = ws.receive_json()
        assert res["type"] == "pong"

    # Connect to emergency WS
    ticket_e = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/emergency/{session_id}?ticket={ticket_e}") as ws:
        ws.send_text('{"type": "ping"}')
        res = ws.receive_json()
        assert res["type"] == "pong"


# 7. User A cannot subscribe to User B's journey
def test_user_a_cannot_subscribe_to_user_b_journey(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_a = str(ObjectId())
    user_b = str(ObjectId())

    # Create journey belonging to User B
    journey_b = Journey(
        user_id=ObjectId(user_b),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_b_id = str(ObjectId())
    journey_b.id = ObjectId(journey_b_id)
    journey_repo.journeys[journey_b_id] = journey_b

    # User A obtains a ticket
    ticket_a = ticket_service.issue_ticket(user_a)

    # User A tries to connect to User B's journey -> rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/journey/{journey_b_id}?ticket={ticket_a}"):
            pass
    assert exc_info.value.code == 1008


# 8. User A cannot listen to User B's private emergency stream
def test_user_a_cannot_listen_to_user_b_emergency_stream(ws_test_env):
    client, _, _ = ws_test_env
    user_a = str(ObjectId())
    user_b = str(ObjectId())

    # Register emergency session for User B
    session_b_id = "sos_private_b_999"
    emergency_session_registry.register_session(session_id=session_b_id, user_id=user_b)

    # User A obtains a valid ticket
    ticket_a = ticket_service.issue_ticket(user_a)

    # User A tries to connect to User B's emergency session -> rejected with 1008
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/emergency/{session_b_id}?ticket={ticket_a}"):
            pass
    assert exc_info.value.code == 1008


# 9. A client cannot change its authorized resource through a message payload
def test_client_cannot_hijack_resource_in_message(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())

    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket}") as ws:
        # Attempt to spoof a different journey_id in payload
        ws.send_text('{"type": "location_update", "journey_id": "different_journey_id_xyz"}')
        res = ws.receive_json()
        assert "Cannot change journey_id" in res["error"]

        # Attempt to supply client-forged safety score
        ws.send_text('{"type": "location_update", "safety_score": 100}')
        res2 = ws.receive_json()
        assert "safety scores are not accepted" in res2["error"]


# 10. Malformed messages are rejected safely
def test_malformed_messages_handled_safely(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())

    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket}") as ws:
        # Malformed non-JSON
        ws.send_text("NOT_JSON_DATA!!!")
        res1 = ws.receive_json()
        assert res1["error"] == "Malformed JSON payload"

        # Out-of-bounds coordinate
        ws.send_text('{"type": "location_update", "lat": 999.0, "lng": 77.0}')
        res2 = ws.receive_json()
        assert "Latitude must be between" in res2["error"]

        # Oversized payload (>4096 bytes)
        huge_payload = "A" * 5000
        ws.send_text(huge_payload)
        res3 = ws.receive_json()
        assert "Payload size exceeded limit" in res3["error"]


# 11. Disconnected clients are removed from subscription registries
def test_disconnections_cleaned_up_from_registry(ws_test_env):
    client, _, journey_repo = ws_test_env
    user_id = str(ObjectId())

    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_id = str(ObjectId())
    journey.id = ObjectId(journey_id)
    journey_repo.journeys[journey_id] = journey

    assert journey_manager.is_connected(journey_id) is False

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{journey_id}?ticket={ticket}") as ws:
        assert journey_manager.is_connected(journey_id) is True

    # Exited context manager -> disconnected
    assert journey_manager.is_connected(journey_id) is False


# 12. Broadcasts reach only authorized recipients
def test_broadcasts_restricted_to_authorized_session(ws_test_env):
    client, _, _ = ws_test_env
    user_a = str(ObjectId())
    session_a = "sos_session_a_1"
    emergency_session_registry.register_session(session_id=session_a, user_id=user_a)

    user_b = str(ObjectId())
    session_b = "sos_session_b_2"
    emergency_session_registry.register_session(session_id=session_b, user_id=user_b)

    ticket_a = ticket_service.issue_ticket(user_a)
    with client.websocket_connect(f"/api/v1/ws/emergency/{session_a}?ticket={ticket_a}") as ws_a:
        # User A sends emergency telemetry
        ws_a.send_text('{"type": "telemetry", "lat": 12.9716, "lng": 77.5946, "notes": "Help needed"}')
        broadcast = ws_a.receive_json()
        assert broadcast["status"] == "received"
        assert broadcast["session_id"] == session_a
        assert broadcast["sender_user_id"] == user_a
        assert broadcast["data"]["notes"] == "Help needed"

    # Assert session_b receives no leaks
    assert emergency_manager.is_connected(session_b) is False


# 13. REST ws-ticket endpoint is protected and issues valid tickets
def test_rest_ws_ticket_endpoint(ws_test_env):
    client, user_repo, _ = ws_test_env
    user_id = str(ObjectId())
    user = User(
        username="ws_user",
        email="ws_user@safeshe.org",
        password_hash=AuthService.hash_password("ValidPassword123!")
    )
    user.id = ObjectId(user_id)
    user_repo.users[user_id] = user

    # Without auth token -> 401
    unauth_res = client.post("/api/v1/auth/ws-ticket")
    assert unauth_res.status_code == 401

    # With valid auth token -> 200 and ticket returned
    token = AuthService.create_access_token(user_id=user_id, email="ws_user@safeshe.org")
    auth_res = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 200
    ticket_data = auth_res.json()["data"]
    assert "ticket" in ticket_data
    assert ticket_data["expires_in"] == 60

    # Validate ticket can be consumed
    consumed_user_id = ticket_service.consume_ticket(ticket_data["ticket"])
    assert consumed_user_id == user_id


# 14. Frontend codebase verification: No WebSocket path contains long-lived JWT in URLs
def test_frontend_contains_no_websocket_token_query():
    frontend_services_dir = Path("frontend/src/api/services")
    for file_path in frontend_services_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert "?token=" not in content, f"Found '?token=' in frontend service {file_path}"
        assert "token=" not in content or "token_type" in content or "refresh_token" in content, f"Possible token in {file_path}"
