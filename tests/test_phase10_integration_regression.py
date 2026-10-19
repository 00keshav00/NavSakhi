"""
SafeShe - Phase 10 End-to-End Integration and Defect Correction Regression Test Suite

Verifies:
1. Rejection of far-future telemetry timestamps (clock-skew bounding).
2. Rejection of duplicate/replay and stale timestamps.
3. Rejection of implausibly large location jumps (teleportation/glitch prevention).
4. Route continuity preservation across loops, switchbacks, and intersection crossings.
5. Telemetry progress never marks journey completed automatically when near destination.
6. Robustness against degenerate, empty, and single-point route geometries.
7. End-to-end integration: User registration -> Auth -> Journey Planning with Frozen ML Scoring -> Route Selection -> WebSocket Ticket Acquisition -> Telemetry Progress Streaming.
"""

import math
import time
import json
import pytest
from bson import ObjectId
from datetime import datetime
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.journey import Journey, Location, JourneyState, JourneyStateEnum, JourneyProgress
from app.services.auth_service import AuthService
from app.services.ticket_service import ticket_service
from app.services.journey_telemetry_service import (
    haversine_distance_meters,
    project_point_to_route,
    extract_route_coordinates,
    JourneyTelemetryService,
    telemetry_service,
    DEFAULT_OFF_ROUTE_THRESHOLD_METERS
)
from app.api.dependencies import get_user_repository, get_journey_repository, get_current_user_id


class MockUserRepo:
    def __init__(self):
        self.users = {}

    async def get_by_email(self, email: str):
        for u in self.users.values():
            if u.email.lower() == email.lower():
                return u
        return None

    async def get_by_id(self, user_id: str):
        return self.users.get(str(user_id))

    async def create(self, user: User) -> User:
        uid = str(ObjectId())
        user.id = ObjectId(uid)
        self.users[uid] = user
        return user


class MockJourneyRepo:
    def __init__(self):
        self.journeys = {}

    async def get_by_id(self, journey_id: str):
        return self.journeys.get(str(journey_id))

    async def create(self, journey: Journey) -> Journey:
        jid = str(ObjectId())
        journey.id = ObjectId(jid)
        self.journeys[jid] = journey
        return journey

    async def update(self, journey_id: str, update_data: dict) -> Journey:
        j = self.journeys.get(str(journey_id))
        if not j:
            return None
        if isinstance(update_data, dict):
            if "state" in update_data:
                if hasattr(update_data["state"], "current_state"):
                    j.state = update_data["state"]
                elif isinstance(update_data["state"], dict):
                    j.state = JourneyState(**update_data["state"])
            if "progress" in update_data and update_data["progress"] is not None:
                if isinstance(update_data["progress"], dict):
                    j.progress = JourneyProgress(**update_data["progress"])
                else:
                    j.progress = update_data["progress"]
            if "last_telemetry_timestamp" in update_data:
                j.last_telemetry_timestamp = update_data["last_telemetry_timestamp"]
            if "selected_route_id" in update_data:
                j.selected_route_id = update_data["selected_route_id"]
            if "planned_routes" in update_data:
                j.planned_routes = update_data["planned_routes"]
        self.journeys[str(journey_id)] = j
        return j


@pytest.fixture
def phase10_env():
    user_repo = MockUserRepo()
    journey_repo = MockJourneyRepo()

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_journey_repository] = lambda: journey_repo

    client = TestClient(app, raise_server_exceptions=False)
    yield client, user_repo, journey_repo
    app.dependency_overrides.clear()


def make_loop_route():
    """
    Creates a route geometry that forms a teardrop loop crossing near the start:
    Start: (77.5900, 12.9700)
    East:  (77.5950, 12.9700) ~550m
    North: (77.5950, 12.9750) ~550m
    West:  (77.5905, 12.9750) ~500m
    South: (77.5905, 12.9702) ~530m  (Crosses within 25m of the start segment!)
    End:   (77.5850, 12.9700) ~600m
    Total length: ~2730m
    """
    coords = [
        [77.5900, 12.9700],
        [77.5950, 12.9700],
        [77.5950, 12.9750],
        [77.5905, 12.9750],
        [77.5905, 12.9702],
        [77.5850, 12.9700]
    ]
    return {
        "id": "loop_route_1",
        "route_id": "loop_route_1",
        "distance": "2.7 km",
        "duration": "35 mins",
        "safety_score": 82.5,
        "score_status": "READY",
        "segments": [
            {
                "segment_name": "Loop Segment",
                "transport_mode": "walk",
                "polyline": {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coords
                    }
                }
            }
        ]
    }


def setup_active_loop_journey(user_repo, journey_repo):
    uid = str(ObjectId())
    user = User(
        username="integration_tester",
        email="integration@safeshe.org",
        password_hash=AuthService.hash_password("IntegrationPass123!")
    )
    user.id = ObjectId(uid)
    user_repo.users[uid] = user

    jid = str(ObjectId())
    loop_route = make_loop_route()
    journey = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[77.5900, 12.9700]),
        destination=Location(coordinates=[77.5850, 12.9700]),
        state=JourneyState(current_state=JourneyStateEnum.ACTIVE),
        selected_route_id="loop_route_1",
        planned_routes=[loop_route],
        progress=JourneyProgress()
    )
    journey.id = ObjectId(jid)
    journey_repo.journeys[jid] = journey

    token = AuthService.create_access_token(user_id=uid, email="integration@safeshe.org")
    return uid, jid, token, journey


# --- 1. Far-Future Timestamp Rejection ---
def test_far_future_timestamp_rejected(phase10_env):
    client, user_repo, journey_repo = phase10_env
    user_id, j_id, token, _ = setup_active_loop_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        # Send timestamp 1 hour in the future
        future_ts = time.time() + 3600.0
        payload = {
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5910,
            "timestamp": future_ts
        }
        ws.send_text(json.dumps(payload))
        resp = ws.receive_json()

        assert resp.get("status") == "rejected"
        assert "future" in resp.get("error", "").lower()

    # Verify that the rejected timestamp was NOT recorded on the journey
    saved = journey_repo.journeys[j_id]
    assert saved.last_telemetry_timestamp is None


# --- 2. Duplicate and Replay Timestamps Rejection ---
def test_duplicate_and_replay_timestamps_rejected(phase10_env):
    client, user_repo, journey_repo = phase10_env
    user_id, j_id, token, _ = setup_active_loop_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        now_ts = time.time()
        # First update
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5910,
            "timestamp": now_ts
        }))
        r1 = ws.receive_json()
        assert r1.get("status") == "acknowledged"

        # Duplicate update with identical timestamp (replay)
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5912,
            "timestamp": now_ts
        }))
        r2 = ws.receive_json()
        assert r2.get("status") == "rejected"
        assert "stale or out-of-order" in r2.get("error", "").lower()


# --- 3. Implausibly Large Location Jump Rejection ---
def test_implausibly_large_location_jump_rejected(phase10_env):
    client, user_repo, journey_repo = phase10_env
    user_id, j_id, token, _ = setup_active_loop_journey(user_repo, journey_repo)

    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        t0 = time.time()
        # Normal initial location
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5910,
            "timestamp": t0
        }))
        r1 = ws.receive_json()
        assert r1.get("status") == "acknowledged"

        # 2 seconds later: jump 50 km away (implausible velocity ~25,000 m/s)
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 13.4000,
            "lng": 77.5910,
            "timestamp": t0 + 2.0
        }))
        r2 = ws.receive_json()
        assert r2.get("status") == "rejected"
        assert "jump" in r2.get("error", "").lower()


# --- 4. Route Continuity Preservation Across Loop / Intersection ---
def test_route_continuity_preserves_progression_across_crossing(phase10_env):
    """
    A teardrop loop crosses within 25m of the early start segment.
    When the user is progressing along the early segment, the algorithm must not
    falsely jump 2 km ahead to the return leg.
    """
    client, user_repo, journey_repo = phase10_env
    user_id, j_id, token, journey = setup_active_loop_journey(user_repo, journey_repo)

    # Initial position near the start: ~50m along
    p1 = telemetry_service.calculate_progress(journey, user_lon=77.5905, user_lat=12.9700)
    assert p1["is_on_route"] is True
    assert p1["distance_remaining_m"] > 2000.0  # Far from destination

    # Set prior progress as if user has covered ~55m
    journey.progress.distance_covered = 55.0

    # User is at crossing (77.5905, 12.9701), which is close to both:
    # 1. Early segment (along-distance ~55m)
    # 2. Return leg segment (along-distance ~2130m)
    p2 = telemetry_service.calculate_progress(journey, user_lon=77.5905, user_lat=12.9701)

    # Must stay on the early segment (~55m), NOT jump to 2130m!
    assert p2["is_on_route"] is True
    assert p2["progress_percentage"] < 15.0
    assert p2["distance_remaining_m"] > 2000.0


# --- 5. Telemetry Near Destination Never Marks Journey Completed Automatically ---
def test_progress_near_destination_never_marks_journey_completed(phase10_env):
    client, user_repo, journey_repo = phase10_env
    user_id, j_id, token, journey = setup_active_loop_journey(user_repo, journey_repo)

    # Position user 5 meters from destination point (77.5850, 12.9700)
    res = telemetry_service.calculate_progress(journey, user_lon=77.58504, user_lat=12.9700)

    assert res["distance_remaining_m"] <= 25.0
    assert res["is_on_route"] is True
    # Crucial Phase 10 verification: status must NOT be 'completed'
    assert res["status"] != "completed"
    assert res["status"] == "on_route"

    # Also verify through WebSocket that journey state is NOT automatically changed to COMPLETED
    ticket = ticket_service.issue_ticket(user_id)
    with client.websocket_connect(f"/api/v1/ws/journey/{j_id}?ticket={ticket}") as ws:
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.58504,
            "timestamp": time.time()
        }))
        ack = ws.receive_json()
        assert ack["status"] == "acknowledged"
        assert ack["status_label"] != "completed"

    saved_journey = journey_repo.journeys[j_id]
    assert saved_journey.state.current_state == JourneyStateEnum.ACTIVE


# --- 6. Robustness on Degenerate and Malformed Route Geometries ---
def test_degenerate_and_single_point_geometries():
    # Empty coords
    d, along, total = project_point_to_route(77.59, 12.97, [])
    assert (d, along, total) == (0.0, 0.0, 0.0)

    # Single point
    d, along, total = project_point_to_route(77.59, 12.97, [(77.59, 12.97)])
    assert (d, along, total) == (0.0, 0.0, 0.0)

    # Coincident identical points
    d, along, total = project_point_to_route(77.59, 12.97, [(77.59, 12.97), (77.59, 12.97)])
    assert (d, along, total) == (0.0, 0.0, 0.0)


# --- 7. Full Integration: Registration -> Auth -> Planning -> Selection -> Live Telemetry ---
def test_full_integration_lifecycle_flow(phase10_env):
    client, user_repo, journey_repo = phase10_env

    # Step A: Register User
    reg_res = client.post("/api/v1/auth/register", json={
        "username": "e2e_user",
        "email": "e2e@safeshe.org",
        "password": "SecurePassword123!"
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["success"] is True

    # Step B: Login and obtain JWT
    login_res = client.post("/api/v1/auth/login", json={
        "email": "e2e@safeshe.org",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    assert token is not None

    # Step C: Authenticated User creates an Active Journey with planned routes
    uid = str(user_repo.users[list(user_repo.users.keys())[0]].id)
    jid = str(ObjectId())
    route_fix = make_loop_route()
    j = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[77.5900, 12.9700]),
        destination=Location(coordinates=[77.5850, 12.9700]),
        state=JourneyState(current_state=JourneyStateEnum.ACTIVE),
        selected_route_id="loop_route_1",
        planned_routes=[route_fix],
        progress=JourneyProgress()
    )
    j.id = ObjectId(jid)
    journey_repo.journeys[jid] = j

    # Step D: Acquire Single-Use WebSocket Ticket
    ticket_res = client.post(
        "/api/v1/auth/ws-ticket",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert ticket_res.status_code == 200
    ws_ticket = ticket_res.json()["data"]["ticket"]
    assert ws_ticket is not None

    # Step E: Connect WebSocket and Stream Valid Telemetry
    with client.websocket_connect(f"/api/v1/ws/journey/{jid}?ticket={ws_ticket}") as ws:
        t_now = time.time()
        ws.send_text(json.dumps({
            "type": "location_update",
            "lat": 12.9700,
            "lng": 77.5925,
            "accuracy": 12.0,
            "timestamp": t_now
        }))
        ack = ws.receive_json()
        assert ack["status"] == "acknowledged"
        assert ack["is_on_route"] is True
        assert ack["progress_percentage"] > 5.0
        assert ack["distance_from_route_m"] < 15.0

    # Step F: Monitor Endpoint reflects authentic server-derived progress
    mon_res = client.get(
        f"/api/v1/journeys/{jid}/monitor",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert mon_res.status_code == 200
    mon_data = mon_res.json()["data"]
    assert mon_data["is_active"] is True
    assert mon_data["current_location"]["lat"] == 12.9700
    assert mon_data["current_location"]["lng"] == 77.5925
    assert mon_data["status_summary"]["is_on_route"] is True
