import pytest
import time
import json
import math
from datetime import datetime
from bson import ObjectId
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.journey import Journey, Location, JourneyState, JourneyStateEnum, JourneyProgress
from app.services.auth_service import AuthService
from app.services.ticket_service import ticket_service
from app.services.emergency_session_service import emergency_session_registry
from app.services.journey_telemetry_service import (
    haversine_distance_meters,
    project_point_to_route,
    extract_route_coordinates,
    JourneyTelemetryService,
    telemetry_service,
    DEFAULT_OFF_ROUTE_THRESHOLD_METERS
)
from app.api.websockets.journey_ws import journey_manager
from app.api.websockets.emergency_ws import manager as emergency_manager
from app.api.dependencies import get_user_repository, get_journey_repository

# Isolated Mock Repositories
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

    async def update(self, journey_id: str, update_data: dict) -> Journey:
        j = self.journeys.get(str(journey_id))
        if not j:
            return None
        # Handle dict update
        if isinstance(update_data, dict):
            # If full model dump
            if "state" in update_data and isinstance(update_data["state"], dict):
                j.state = JourneyState(**update_data["state"])
            elif "state" in update_data and hasattr(update_data["state"], "current_state"):
                j.state = update_data["state"]

            if "progress" in update_data and update_data["progress"] is not None:
                if isinstance(update_data["progress"], dict):
                    j.progress = JourneyProgress(**update_data["progress"])
                else:
                    j.progress = update_data["progress"]

            if "planned_routes" in update_data:
                j.planned_routes = update_data["planned_routes"]
            if "selected_route_id" in update_data:
                j.selected_route_id = update_data["selected_route_id"]
            if "last_telemetry_timestamp" in update_data:
                j.last_telemetry_timestamp = update_data["last_telemetry_timestamp"]
            if "started_timestamp" in update_data:
                j.started_timestamp = update_data["started_timestamp"]
            if "completed_timestamp" in update_data:
                j.completed_timestamp = update_data["completed_timestamp"]

        self.journeys[str(journey_id)] = j
        return j


# Deterministic Local Route Fixture
def create_fixture_route(route_id="route_fixture_1"):
    # Straight East line along latitude 12.9700 from lon 77.5900 to 77.6000 (~1084 meters)
    return {
        "id": route_id,
        "route_id": route_id,
        "route_name": "Test Safe Route",
        "distance": "1.08 km",
        "estimated_duration": 840,
        "safety_score": 94.5,
        "segments": [
            {
                "segment_name": "Segment 1",
                "transport_mode": "WALK",
                "polyline": {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [77.5900, 12.9700],
                            [77.5950, 12.9700],
                            [77.6000, 12.9700]
                        ]
                    }
                }
            }
        ]
    }


@pytest.fixture
def telemetry_test_env():
    user_repo = InMemoryUserRepository()
    journey_repo = InMemoryJourneyRepository()

    ticket_service.clear()
    emergency_session_registry.clear()
    telemetry_service._rate_limit_cache.clear()

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_journey_repository] = lambda: journey_repo

    client = TestClient(app, raise_server_exceptions=False)
    yield client, user_repo, journey_repo

    app.dependency_overrides.clear()
    ticket_service.clear()
    emergency_session_registry.clear()
    telemetry_service._rate_limit_cache.clear()


# Helper to build an active journey owned by a user with planned route fixture
def setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.ACTIVE):
    user_id = str(ObjectId())
    user = User(
        username="telemetry_user",
        email=f"user_{user_id[:6]}@safeshe.org",
        password_hash=AuthService.hash_password("SafeShe123!")
    )
    user.id = ObjectId(user_id)
    user_repo.users[user_id] = user

    j_id = str(ObjectId())
    fixture_route = create_fixture_route()
    journey = Journey(
        user_id=ObjectId(user_id),
        source=Location(coordinates=[77.5900, 12.9700]),
        destination=Location(coordinates=[77.6000, 12.9700]),
        state=JourneyState(current_state=state),
        progress=JourneyProgress(status="unavailable"),
        planned_routes=[fixture_route],
        selected_route_id="route_fixture_1"
    )
    journey.id = ObjectId(j_id)
    journey_repo.journeys[j_id] = journey

    token = AuthService.create_access_token(user_id=user_id, email=user.email)
    return user_id, j_id, token, journey


# 1. Monitoring cannot start without explicit lifecycle initiation
def test_monitoring_cannot_start_without_explicit_lifecycle(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.PLANNED)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        # Send location update while journey is still PLANNED
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5910}))
        msg = ws.receive_json()
        assert msg["status"] == "rejected"
        assert "Journey must be ACTIVE or MONITORING" in msg["error"]


# 2. Browser permission denial / missing location is handled safely without fake data
def test_missing_location_handled_safely_without_fabrication(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, token, _ = setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.ACTIVE)

    res = client.get(f"/api/v1/journeys/{j_id}/monitor", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()["data"]

    # Must NOT contain hardcoded Bangalore mock or fabricated contacts
    assert data["current_location"] is None
    assert data["status_summary"]["status"] == "unavailable"
    assert data["status_summary"]["progress_percentage"] == 0.0


# 3. A valid telemetry message from the journey owner is accepted
def test_valid_telemetry_message_accepted(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.ACTIVE)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        payload = {
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5950, # Exactly halfway along the route
            "accuracy": 10.0,
            "timestamp": time.time()
        }
        ws.send_text(json.dumps(payload))
        ack = ws.receive_json()

        assert ack["status"] == "acknowledged"
        assert ack["type"] == "telemetry_ack"
        assert ack["journey_id"] == j_id
        assert ack["is_on_route"] is True
        assert 45.0 <= ack["progress_percentage"] <= 55.0
        assert ack["distance_from_route_m"] < 10.0


# 4. Missing, invalid, expired, or replayed WebSocket tickets are rejected
def test_ws_ticket_lifecycle_enforcement(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    # Missing ticket
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/ws/journey/{j_id}"):
            pass
    assert exc.value.code == 1008

    # Invalid ticket
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket=invalid_ticket_xyz"):
            pass
    assert exc.value.code == 1008

    # Replayed ticket (ticket is consumed once)
    t = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={t}") as ws:
        pass # Disconnect cleanly
    # Second attempt with same ticket must be rejected
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={t}"):
            pass
    assert exc.value.code == 1008


# 5. User A cannot stream location into User B's journey
def test_user_a_cannot_stream_location_into_user_b_journey(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_a, j_a, _, _ = setup_active_journey(user_repo, journey_repo)
    user_b, j_b, _, _ = setup_active_journey(user_repo, journey_repo)

    # User A obtains ticket
    ticket_a = ticket_service.issue_ticket(user_a)

    # User A attempts to connect to User B's journey
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/v1/ws/journey/{j_b}?ticket={ticket_a}"):
            pass
    assert exc.value.code == 1008


# 6. A client cannot change the journey identifier after handshake
def test_client_cannot_change_journey_id_in_message(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({"type": "location_update", "journey_id": "other_fake_id", "lat": 12.97, "lng": 77.59}))
        res = ws.receive_json()
        assert res["error"] == "Cannot change journey_id in message payload"


# 7. Invalid or non-finite coordinates are rejected
def test_invalid_or_non_finite_coordinates_rejected(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        # Out of bounds lat
        ws.send_text(json.dumps({"type": "location_update", "lat": 195.0, "lng": 77.59}))
        r1 = ws.receive_json()
        assert "Latitude must be between" in r1["error"]

        # Missing lng
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.97}))
        r2 = ws.receive_json()
        assert "Coordinates missing" in r2["error"]

        # String non-numeric
        ws.send_text(json.dumps({"type": "location_update", "lat": "bad_lat", "lng": "bad_lng"}))
        r3 = ws.receive_json()
        assert "Coordinates must be numeric" in r3["error"]


# 8. Out-of-order or stale updates do not overwrite newer valid readings
def test_stale_or_out_of_order_telemetry_rejected(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        now_ts = time.time()
        # First valid update with modern timestamp
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5910, "timestamp": now_ts}))
        r1 = ws.receive_json()
        assert r1["status"] == "acknowledged"

        # Out-of-order update with older timestamp (e.g. 100 seconds in past)
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5905, "timestamp": now_ts - 100.0}))
        r2 = ws.receive_json()
        assert r2["status"] == "rejected"
        assert "Stale or out-of-order" in r2["error"]


# 9. Excessively frequent updates are rate-limited
def test_excessive_update_frequency_rate_limited(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        rate_limited_observed = False
        # Send 8 updates in tight succession (limit is 5/sec)
        for i in range(8):
            ws.send_text(json.dumps({
                "type": "location_update",
                "lat": 12.9700,
                "lng": 77.5900 + (i * 0.0001),
                "timestamp": time.time() + (i * 0.001)
            }))
            resp = ws.receive_json()
            if resp.get("status") == "rejected" and "Rate limit exceeded" in resp.get("error", ""):
                rate_limited_observed = True
                break

        assert rate_limited_observed is True


# 10. Paused journeys do not accept normal active telemetry
def test_paused_journeys_reject_telemetry(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.PAUSED)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5950}))
        res = ws.receive_json()
        assert res["status"] == "rejected"
        assert "Journey is paused" in res["error"]


# 11. Cancelled and completed journeys stop accepting tracking updates
def test_cancelled_and_completed_journeys_reject_telemetry(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo, state=JourneyStateEnum.COMPLETED)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5950}))
        res = ws.receive_json()
        assert res["status"] == "rejected"
        assert "Tracking updates are no longer accepted" in res["error"]


# 12. Geolocation watchers and connection registries are cleaned up
def test_connection_registry_cleaned_up_on_disconnect(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    assert journey_manager.is_connected(j_id) is False

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        assert journey_manager.is_connected(j_id) is True

    # Exiting context block triggers disconnect
    assert journey_manager.is_connected(j_id) is False


# 13. Reconnection obtains a fresh ticket
def test_reconnection_requires_fresh_ticket(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, token, _ = setup_active_journey(user_repo, journey_repo)

    # First ticket
    res1 = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    ticket1 = res1.json()["data"]["ticket"]

    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket1}") as ws:
        pass

    # Ticket 1 cannot be reused
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket1}"):
            pass

    # Client requests a new ticket for reconnection
    res2 = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    ticket2 = res2.json()["data"]["ticket"]
    assert ticket2 != ticket1

    # Second connection with fresh ticket succeeds
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket2}") as ws:
        assert journey_manager.is_connected(j_id) is True


# 14. Progress is derived from actual fixture route geometry
def test_progress_derived_from_fixture_route_geometry(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo)

    # Route coords are (77.5900, 12.9700) -> (77.6000, 12.9700)
    # Total length is approx 1084m. Point at 77.5950 is 50% along the route.
    res = telemetry_service.calculate_progress(journey, user_lon=77.5950, user_lat=12.9700)
    assert 48.0 <= res["progress_percentage"] <= 52.0
    assert 500.0 <= res["distance_remaining_m"] <= 600.0
    assert res["is_on_route"] is True
    assert res["status"] == "on_route"


# 15. Off-route distance uses metric units
def test_off_route_distance_uses_metric_units():
    # 0.0018 degrees North at lat 12.97 is approx 200 meters
    dist = haversine_distance_meters(77.5950, 12.9700, 77.5950, 12.9718)
    assert 190.0 <= dist <= 210.0

    coords = [(77.5900, 12.9700), (77.6000, 12.9700)]
    dist_from_route, dist_along, total_len = project_point_to_route(
        user_lon=77.5950,
        user_lat=12.9718, # ~200m off route
        route_coords=coords
    )
    assert 190.0 <= dist_from_route <= 210.0 # Metric meters, not 0.0018 degrees!


# 16. Invalid route geometry produces an explicit unavailable state
def test_invalid_route_geometry_produces_unavailable_state():
    j = Journey(
        user_id=ObjectId(),
        source=Location(coordinates=[0, 0]),
        destination=Location(coordinates=[0, 0]),
        state=JourneyState(current_state=JourneyStateEnum.ACTIVE),
        planned_routes=[] # Empty
    )
    res = telemetry_service.calculate_progress(j, user_lon=77.59, user_lat=12.97)
    assert res["status"] == "unavailable"
    assert res["progress_percentage"] == 0.0
    assert res["distance_from_route_m"] is None


# 17. A missing location does not generate a fake marker or fabricated progress
def test_missing_location_does_not_generate_fake_marker(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, token, _ = setup_active_journey(user_repo, journey_repo)

    res = client.get(f"/api/v1/journeys/{j_id}/progress", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    prog = res.json()["data"]["progress"]
    assert prog["current_location"] is None
    assert prog["distance_from_route"] is None


# 18. Journey progress reads enforce ownership
def test_journey_progress_enforces_ownership(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_a, j_a, token_a, _ = setup_active_journey(user_repo, journey_repo)
    user_b, j_b, token_b, _ = setup_active_journey(user_repo, journey_repo)

    # User B attempts to read User A's progress
    res = client.get(f"/api/v1/journeys/{j_a}/progress", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403

    # User B attempts to monitor User A's journey
    res_mon = client.get(f"/api/v1/journeys/{j_a}/monitor", headers={"Authorization": f"Bearer {token_b}"})
    assert res_mon.status_code == 403


# 19. No GPS history is persisted (only latest valid telemetry snapshot)
def test_no_continuous_gps_history_persisted(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, journey = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        # Stream 3 points
        for i in range(3):
            ws.send_text(json.dumps({
                "type": "location_update",
                "lat": 12.9700,
                "lng": 77.5910 + (i * 0.001),
                "timestamp": time.time() + (i * 1.5)
            }))
            ws.receive_json()

    saved_journey = journey_repo.journeys[j_id]
    # Check that progress only holds single current_location, not a list of coordinates
    assert isinstance(saved_journey.progress.current_location.coordinates, list)
    assert len(saved_journey.progress.current_location.coordinates) == 2
    assert not hasattr(saved_journey, "gps_history")
    assert not hasattr(saved_journey.progress, "history")


# 20. Normal journey telemetry does not trigger SOS or real-world dispatch
def test_telemetry_and_deviation_does_not_trigger_sos(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, _, _ = setup_active_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        # Send location 400m off route (deviating)
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9740,
            "lng": 77.5950,
            "timestamp": time.time()
        }))
        ack = ws.receive_json()
        assert ack["is_on_route"] is False
        assert ack["status_label"] == "deviating"

    # Verify no emergency session was triggered
    assert len(emergency_session_registry._sessions) == 0


# 21. Existing manual emergency functionality and authorization remain unaffected
def test_manual_emergency_flow_remains_unaffected(telemetry_test_env):
    client, user_repo, _ = telemetry_test_env
    user_id = str(ObjectId())
    user = User(username="sos_user", email="sos@safeshe.org", password_hash=AuthService.hash_password("SafeShe123!"))
    user.id = ObjectId(user_id)
    user_repo.users[user_id] = user

    session_id = "sos_session_phase9"
    emergency_session_registry.register_session(session_id=session_id, user_id=user_id)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/emergency/{session_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({"type": "telemetry", "lat": 12.97, "lng": 77.59, "notes": "Manual SOS trigger"}))
        broadcast = ws.receive_json()
        assert broadcast["status"] == "received"
        assert broadcast["session_id"] == session_id
        assert broadcast["sender_user_id"] == user_id


# 22. API progress responses conform to the existing Pydantic contract and serialize correctly
def test_progress_responses_pydantic_contract_conformance(telemetry_test_env):
    client, user_repo, journey_repo = telemetry_test_env
    user_id, j_id, token, _ = setup_active_journey(user_repo, journey_repo)

    # First send valid telemetry
    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({"type": "location_update", "lat": 12.9700, "lng": 77.5930, "timestamp": time.time()}))
        ws.receive_json()

    # Read progress endpoint
    prog_res = client.get(f"/api/v1/journeys/{j_id}/progress", headers={"Authorization": f"Bearer {token}"})
    assert prog_res.status_code == 200
    prog_json = prog_res.json()
    assert prog_json["success"] is True
    assert prog_json["data"]["progress"]["distance_remaining"] > 0
    assert prog_json["data"]["progress"]["current_location"]["coordinates"] == [77.5930, 12.9700]

    # Read monitor endpoint
    mon_res = client.get(f"/api/v1/journeys/{j_id}/monitor", headers={"Authorization": f"Bearer {token}"})
    assert mon_res.status_code == 200
    mon_json = mon_res.json()
    assert mon_json["success"] is True
    assert mon_json["data"]["is_active"] is True
    assert mon_json["data"]["current_location"]["lat"] == 12.9700
    assert mon_json["data"]["current_location"]["lng"] == 77.5930
    assert mon_json["data"]["status_summary"]["is_on_route"] is True
    assert json.dumps(mon_json) # pure JSON serializable
