"""
Phase 6: Journey API, DTO Normalization and Contract Verification Tests

Verifies that the backend journey-planning pipeline, Pydantic response schemas,
FastAPI REST routes, and serialized JSON conform to the normalized contract:
- Numeric nullable safety_score (JSON float or null; never string "N/A" or default numbers)
- Score readiness status consistency with safety_score
- Cross-field validation (READY requires valid score and coverage >= 70%; non-READY requires score=None)
- StandardResponse envelope integrity
- Clean serialization without leaked NumPy/pandas/ObjectId types
- Multimodal leg and geometry preservation
- Presentation layer score formatting
"""

import math
import json
import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from bson import ObjectId
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.config.settings import settings
from app.services.auth_service import AuthService
from app.schemas.responses import StandardResponse
from app.schemas.journey_schemas import (
    JourneyCreate,
    JourneyPlanResponse,
    JourneyResponse,
    MultimodalRoute,
    RouteSegment,
    JourneyInformation,
    SessionInfo,
    WeatherSummary,
    CommunitySummary,
    AIRecommendation,
)
from app.schemas.spatial_schemas import ScoreStatus
from app.models.journey import Journey, Location, JourneyState, JourneyStateEnum, CandidateRoute
from app.models.user import User
from app.api.dependencies import get_user_repository, get_journey_repository, get_current_user_id
from app.providers.routing.provider import OSRMRoutingProvider
from app.intelligence.response.builder import ResponseBuilder


class InMemoryJourneyRepo:
    def __init__(self):
        self.journeys = {}

    async def get_by_id(self, journey_id: str):
        return self.journeys.get(str(journey_id))

    async def create(self, journey: Journey) -> Journey:
        j_id = str(ObjectId())
        journey.id = ObjectId(j_id)
        self.journeys[j_id] = journey
        return journey

    async def update(self, journey_id: str, journey_data: dict):
        j = self.journeys.get(str(journey_id))
        if j:
            raw = j.model_dump()
            raw.update(journey_data)
            updated = Journey(**raw)
            self.journeys[str(journey_id)] = updated
            return updated
        return None


class InMemoryUserRepo:
    def __init__(self):
        self.users = {}

    async def get_by_id(self, user_id: str):
        return self.users.get(str(user_id))


@pytest.fixture
def auth_client():
    user_repo = InMemoryUserRepo()
    journey_repo = InMemoryJourneyRepo()
    test_user_id = str(ObjectId())

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_journey_repository] = lambda: journey_repo
    app.dependency_overrides[get_current_user_id] = lambda: test_user_id

    client = TestClient(app, raise_server_exceptions=False)
    yield client, journey_repo, test_user_id
    app.dependency_overrides.clear()


# --- 1. Schema Cross-Field Validation Unit Tests ---

def test_ready_route_requires_numeric_safety_score():
    """Route with READY status must have a finite numeric safety_score [0, 100]."""
    # Valid READY route
    route = MultimodalRoute(
        id="r1", rank=1, route_name="Route 1", mode="Cab",
        eta="15 min", cost="100", distance="5 km",
        safety_score=78.5, score_status="READY", scoreable_coverage_ratio=0.85,
        segments=[]
    )
    assert route.safety_score == 78.5
    assert route.overall_safety_score == 78.5

    # READY with None score must raise ValidationError
    with pytest.raises(ValidationError) as exc:
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=None, score_status="READY", scoreable_coverage_ratio=0.85,
            segments=[]
        )
    assert "READY status must have a finite numeric safety_score" in str(exc.value)

    # READY with NaN score must raise ValidationError
    with pytest.raises(ValidationError) as exc:
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=float("nan"), score_status="READY", scoreable_coverage_ratio=0.85,
            segments=[]
        )
    assert "READY status must have a finite numeric safety_score" in str(exc.value)

    # READY with score > 100 must raise ValidationError
    with pytest.raises(ValidationError) as exc:
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=105.0, score_status="READY", scoreable_coverage_ratio=0.85,
            segments=[]
        )
    assert "safety_score must be between 0.0 and 100.0" in str(exc.value)


def test_ready_route_requires_coverage_threshold():
    """Route with READY status must satisfy coverage threshold >= 0.70."""
    with pytest.raises(ValidationError) as exc:
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=78.5, score_status="READY", scoreable_coverage_ratio=0.45,
            segments=[]
        )
    assert "coverage >= 0.70" in str(exc.value)


def test_non_ready_route_requires_null_safety_score():
    """Route with non-READY status must have safety_score=None."""
    # Valid non-ready route
    route = MultimodalRoute(
        id="r2", rank=2, route_name="Route 2", mode="Public Transit",
        eta="30 min", cost="25", distance="8 km",
        safety_score=None, score_status="INSUFFICIENT_COVERAGE", scoreable_coverage_ratio=0.25,
        segments=[]
    )
    assert route.safety_score is None
    assert route.overall_safety_score is None

    # Non-ready route with a numeric score must raise ValidationError
    with pytest.raises(ValidationError) as exc:
        MultimodalRoute(
            id="r2", rank=2, route_name="Route 2", mode="Public Transit",
            eta="30 min", cost="25", distance="8 km",
            safety_score=50.0, score_status="INSUFFICIENT_COVERAGE", scoreable_coverage_ratio=0.25,
            segments=[]
        )
    assert "must have safety_score=None" in str(exc.value)


def test_coverage_ratio_bounds():
    """Coverage ratio must be in [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=None, score_status="NO_SCOREABLE_SEGMENTS", scoreable_coverage_ratio=1.5,
            segments=[]
        )

    with pytest.raises(ValidationError):
        MultimodalRoute(
            id="r1", rank=1, route_name="Route 1", mode="Cab",
            eta="15 min", cost="100", distance="5 km",
            safety_score=None, score_status="NO_SCOREABLE_SEGMENTS", scoreable_coverage_ratio=-0.1,
            segments=[]
        )


def test_journey_information_distance_duration_non_negative():
    """JourneyInformation must enforce non-negative metric values."""
    info = JourneyInformation(source="A", destination="B", distance=1500.0, estimated_duration=600.0)
    assert info.distance == 1500.0
    assert info.estimated_duration == 600.0

    with pytest.raises(ValidationError):
        JourneyInformation(source="A", destination="B", distance=-100.0, estimated_duration=600.0)

    with pytest.raises(ValidationError):
        JourneyInformation(source="A", destination="B", distance=100.0, estimated_duration=-50.0)


# --- 2. Serialization & DTO Conversion Tests ---

def test_response_builder_serializes_numeric_and_null_scores():
    """ResponseBuilder must serialize numeric scores when READY, and null when unscoreable. Never string 'N/A'."""
    builder = ResponseBuilder()

    # Candidate 1: Scored route (READY)
    c1 = CandidateRoute(
        route_identifier="c_scored",
        distance=1500.0,
        duration=300.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
            "travel_mode": "Road",
            "safety_score": 75.42,
            "score_status": "READY",
            "scoreable_coverage_ratio": 0.90,
            "score_basis": "matched_road_segments_only",
        }
    )

    # Candidate 2: Unscored route (INSUFFICIENT_COVERAGE)
    c2 = CandidateRoute(
        route_identifier="c_unscored",
        distance=2000.0,
        duration=400.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
            "travel_mode": "Multimodal",
            "safety_score": None,
            "score_status": "INSUFFICIENT_COVERAGE",
            "scoreable_coverage_ratio": 0.20,
            "score_basis": "matched_road_segments_only",
        }
    )

    context = {
        "source_name": "Anna Nagar",
        "dest_name": "T Nagar",
        "source_loc": [80.2498, 13.0500],
        "dest_loc": [80.2502, 13.0500],
        "routes": [c1, c2],
    }

    plan_response = builder.build_journey_plan(context, user_id="u1", journey_id="j1")
    assert isinstance(plan_response, JourneyPlanResponse)

    # Convert to pure JSON dictionary
    json_data = json.loads(plan_response.model_dump_json())

    routes = json_data["recommended_routes"]
    assert len(routes) == 2

    # Scored route
    r_scored = routes[0]
    assert isinstance(r_scored["safety_score"], float)
    assert r_scored["safety_score"] == 75.42
    assert r_scored["overall_safety_score"] == 75.42
    assert r_scored["score_status"] == "READY"
    assert r_scored["scoreable_coverage_ratio"] == 0.90
    assert r_scored["model_version"] == "2.0.0"
    assert "synthetic environmental safety proxy" in r_scored["target_disclosure"].lower()
    # Ensure explainability contains no fake static contributions
    assert r_scored["model_explainability"] == {}

    # Unscored route
    r_unscored = routes[1]
    assert r_unscored["safety_score"] is None
    assert r_unscored["overall_safety_score"] is None
    assert r_unscored["score_status"] == "INSUFFICIENT_COVERAGE"
    assert r_unscored["scoreable_coverage_ratio"] == 0.20

    # Explicit check: "N/A" must NOT appear as any score value
    for r in routes:
        assert r["safety_score"] != "N/A"
        assert r["overall_safety_score"] != "N/A"
        for seg in r["segments"]:
            assert seg["adjusted_safety_score"] != "N/A"
            assert seg["safety_score"] != "N/A"


def test_ai_recommendation_disclosure_and_no_fake_confidence():
    """AIRecommendation must contain disclosure warnings and omit static confidence."""
    builder = ResponseBuilder()
    c = CandidateRoute(
        route_identifier="c1",
        distance=500.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={"geometry": [[80.25, 13.05], [80.251, 13.05]]}
    )
    context = {"routes": [c]}
    plan = builder.build_journey_plan(context, "u1", "j1")

    json_str = plan.model_dump_json()
    data = json.loads(json_str)

    ai_rec = data["ai_recommendation"]
    assert ai_rec["confidence"] is None  # Static fake 95% omitted
    assert any("environmental safety proxy" in w.lower() for w in ai_rec["warnings"])


# --- 3. Full FastAPI Endpoint Contract Tests ---

def test_api_create_journey_successful_scored_route(auth_client, monkeypatch):
    """POST /api/v1/journeys/ returns StandardResponse with real ML-scored route."""
    client, journey_repo, user_id = auth_client

    # Deterministic OSRM mock returning coordinates passing through Chennai seg_A
    async def mock_get_routes(self, source, destination, mode="driving", alternatives=3):
        return [
            CandidateRoute(
                route_identifier="osrm_mock_1",
                distance=100.0,
                duration=120.0,
                recommendation_status="AVAILABLE",
                route_metadata={
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.283733, 13.084927], [80.283349, 13.084608]]
                    },
                    "travel_mode": "Road",
                }
            )
        ]

    monkeypatch.setattr(OSRMRoutingProvider, "get_routes", mock_get_routes)

    payload = {
        "source": "13.084927, 80.283733",
        "destination": "13.084608, 80.283349",
        "preferences": ["personal_vehicle", "safest"]
    }

    res = client.post("/api/v1/journeys/", json=payload)
    assert res.status_code == 200

    body = res.json()
    # Validate StandardResponse envelope
    assert body["success"] is True
    assert "data" in body
    data = body["data"]

    # Validate JourneyPlanResponse shape
    assert "journey_id" in data
    assert "recommended_routes" in data
    assert len(data["recommended_routes"]) >= 1

    primary_route = data["recommended_routes"][0]
    # Check score normalization
    assert "safety_score" in primary_route
    assert "score_status" in primary_route
    assert "scoreable_coverage_ratio" in primary_route

    assert primary_route["score_status"] == ScoreStatus.READY.value
    assert isinstance(primary_route["safety_score"], (int, float))
    assert 0.0 <= primary_route["safety_score"] <= 100.0
    assert primary_route["overall_safety_score"] == primary_route["safety_score"]
    assert primary_route["safety_score"] != "N/A"
    assert primary_route["scoreable_coverage_ratio"] >= 0.70
    assert primary_route["score_basis"] == "matched_road_segments_only"
    assert primary_route["model_version"] == "2.0.0"

    # Verify geometry representation
    assert len(primary_route["segments"]) >= 1
    seg = primary_route["segments"][0]
    assert seg["polyline"]["type"] == "Feature"
    assert seg["polyline"]["geometry"]["type"] == "LineString"


def test_api_create_journey_unscoreable_outside_geography(auth_client, monkeypatch):
    """Route outside supported geography produces safety_score: null, never 'N/A' or default 50."""
    client, journey_repo, user_id = auth_client

    # Mock OSRM returning London coordinates (far away from indexed Chennai OSM network)
    async def mock_get_routes(self, source, destination, mode="driving", alternatives=3):
        return [
            CandidateRoute(
                route_identifier="osrm_london",
                distance=500.0,
                duration=300.0,
                recommendation_status="AVAILABLE",
                route_metadata={
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.1278, 51.5074], [-0.1280, 51.5080]]
                    },
                    "travel_mode": "Road",
                }
            )
        ]

    monkeypatch.setattr(OSRMRoutingProvider, "get_routes", mock_get_routes)

    payload = {
        "source": "51.5074, -0.1278",
        "destination": "51.5080, -0.1280",
    }

    res = client.post("/api/v1/journeys/", json=payload)
    assert res.status_code == 200

    data = res.json()["data"]
    primary = data["recommended_routes"][0]

    # Must be null, never "N/A" or fake default
    assert primary["safety_score"] is None
    assert primary["overall_safety_score"] is None
    assert primary["safety_score"] != "N/A"
    assert primary["score_status"] in (ScoreStatus.UNSUPPORTED_GEOGRAPHY.value, ScoreStatus.NO_SCOREABLE_SEGMENTS.value)
    assert primary["scoreable_coverage_ratio"] == 0.0


def test_api_zero_distance_journey(auth_client):
    """Source == Destination is handled cleanly with zero_distance response."""
    client, journey_repo, user_id = auth_client

    payload = {
        "source": "13.0500, 80.2500",
        "destination": "13.0500, 80.2500",
    }

    res = client.post("/api/v1/journeys/", json=payload)
    assert res.status_code == 200

    data = res.json()["data"]
    assert data["journey_information"]["distance"] == 0.0
    assert len(data["recommended_routes"]) == 0
    assert "already at destination" in data["ai_recommendation"]["title"].lower()


def test_api_unauthenticated_request_rejected(auth_client):
    """Unauthenticated call to /api/v1/journeys/ must be rejected with 401."""
    client, _, _ = auth_client
    # Temporarily remove get_current_user_id override to test real auth dependency
    override = app.dependency_overrides.pop(get_current_user_id, None)
    try:
        payload = {"source": "13.05, 80.25", "destination": "13.06, 80.26"}
        res = client.post("/api/v1/journeys/", json=payload)

        assert res.status_code == 401
        body = res.json()
        assert body["success"] is False
        err_msg = body["error"]["message"] if isinstance(body["error"], dict) else str(body["error"])
        assert "token" in err_msg.lower() or "authentication" in err_msg.lower()
    finally:
        if override:
            app.dependency_overrides[get_current_user_id] = override


def test_api_missing_fields_validation_error(auth_client):
    """Invalid payload with missing required fields returns 422."""
    client, _, _ = auth_client
    res = client.post("/api/v1/journeys/", json={})
    assert res.status_code == 422


def test_api_journey_ownership_enforcement(auth_client):
    """User cannot access another user's journey details (403 Forbidden)."""
    client, journey_repo, current_user_id = auth_client

    # Create journey belonging to a different user
    other_user_id = str(ObjectId())
    journey = Journey(
        user_id=ObjectId(other_user_id),
        source=Location(type="Point", coordinates=[80.25, 13.05]),
        destination=Location(type="Point", coordinates=[80.26, 13.06])
    )
    j_id = str(ObjectId())
    journey.id = ObjectId(j_id)
    journey_repo.journeys[j_id] = journey

    # Attempt to fetch with test_user_id
    res = client.get(f"/api/v1/journeys/{j_id}")
    assert res.status_code == 403
    body = res.json()
    assert body["success"] is False
    err_msg = body["error"]["message"] if isinstance(body["error"], dict) else str(body["error"])
    assert "permission" in err_msg.lower()


def test_pure_json_serializability_no_complex_types(auth_client, monkeypatch):
    """Verify that complete response contains no NumPy, pandas, or non-JSON types."""
    client, _, _ = auth_client

    async def mock_get_routes(self, source, destination, mode="driving", alternatives=3):
        return [
            CandidateRoute(
                route_identifier="r_test",
                distance=100.0,
                duration=120.0,
                recommendation_status="AVAILABLE",
                route_metadata={
                    "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
                    "travel_mode": "Road",
                }
            )
        ]

    monkeypatch.setattr(OSRMRoutingProvider, "get_routes", mock_get_routes)

    res = client.post("/api/v1/journeys/", json={"source": "13.05, 80.2498", "destination": "13.05, 80.2502"})
    assert res.status_code == 200

    # Ensure round-trip serialization to JSON string and back succeeds without error
    raw_text = res.text
    re_parsed = json.loads(raw_text)
    assert re_parsed["success"] is True

    # Traverse all values recursively and assert only JSON-native types exist
    def assert_json_types(val):
        if isinstance(val, dict):
            for k, v in val.items():
                assert isinstance(k, str)
                assert_json_types(v)
        elif isinstance(val, list):
            for item in val:
                assert_json_types(item)
        else:
            assert isinstance(val, (int, float, str, bool, type(None)))
            if isinstance(val, float):
                assert not math.isnan(val) and not math.isinf(val)

    assert_json_types(re_parsed)
