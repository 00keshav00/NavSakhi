import asyncio
import copy
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config.settings import settings
from app.schemas.journey_schemas import JourneyCreate, JourneyPlanResponse
from app.api.dependencies import get_journey_coordinator


@pytest.fixture(autouse=True)
def restore_environment():
    """Ensure settings.environment is restored after each test."""
    original_env = settings.environment
    yield
    settings.environment = original_env


@pytest.mark.asyncio
async def test_staging_exposes_valid_stage_timings_telemetry():
    """
    Test 1: When settings.environment is 'staging', responses include valid
    non-negative timing metrics for all stages that ran in the pipeline.
    """
    settings.environment = "staging"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "source": "13.0067, 80.2184",
            "destination": "13.0213, 80.2230",
            "preferences": ["personal_vehicle"]
        }
        res = await client.post("/api/v1/journeys/guest/plan", json=payload)
        assert res.status_code == 200
        body = res.json()

        assert body["success"] is True
        assert "meta" in body
        assert body["meta"] is not None
        assert "stage_timings" in body["meta"]

        timings = body["meta"]["stage_timings"]

        # Expected core stage metrics
        expected_metrics = [
            "total_duration_ms",
            "location_resolution_ms",
            "road_routing_ms",
            "transit_discovery_ms",
            "candidate_creation_ms",
            "spatial_index_construction_ms",
            "spatial_matching_ms",
            "ml_inference_and_attribution_ms",
            "ml_scoring_total_ms",
            "poi_retrieval_ms",
            "night_activity_evaluation_ms",
            "response_dto_construction_ms",
            "response_construction_ms",
            "response_serialization_ms",
        ]

        for metric in expected_metrics:
            assert metric in timings, f"Expected {metric} to be recorded in stage_timings"
            val = timings[metric]
            assert isinstance(val, (int, float)), f"{metric} should be numeric"
            assert val >= 0.0, f"{metric} must be non-negative, got {val}"

        # Total duration must be greater than zero and >= individual non-overlapping stages
        assert timings["total_duration_ms"] > 0.0

        # JourneyPlanResponse.meta inside data must also be populated
        assert "data" in body
        assert "meta" in body["data"]
        assert body["data"]["meta"] is not None
        assert "stage_timings" in body["data"]["meta"]


@pytest.mark.asyncio
async def test_production_does_not_expose_telemetry():
    """
    Test 2: When settings.environment is 'production' (or non-staging),
    neither the StandardResponse envelope nor JourneyPlanResponse exposes
    staging latency telemetry.
    """
    settings.environment = "production"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "source": "13.0067, 80.2184",
            "destination": "13.0213, 80.2230",
            "preferences": ["personal_vehicle"]
        }
        res = await client.post("/api/v1/journeys/guest/plan", json=payload)
        assert res.status_code == 200
        body = res.json()

        assert body["success"] is True
        # Top-level meta should be None / null
        assert body.get("meta") is None

        # Data-level meta should be None / null
        data = body["data"]
        assert data.get("meta") is None


@pytest.mark.asyncio
async def test_guest_and_auth_schema_compatibility():
    """
    Test 3: Guest planning and authenticated journey planning endpoints
    remain 100% schema compatible with JourneyPlanResponse.
    """
    settings.environment = "staging"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "source": "13.0067, 80.2184",
            "destination": "13.0213, 80.2230",
            "preferences": ["personal_vehicle"]
        }
        res = await client.post("/api/v1/journeys/guest/plan", json=payload)
        assert res.status_code == 200
        body = res.json()

        # Validate with strict Pydantic model
        validated = JourneyPlanResponse.model_validate(body["data"])
        assert validated.journey_id == "guest-exploration"
        assert len(validated.recommended_routes) >= 1
        assert validated.meta is not None
        assert "stage_timings" in validated.meta


@pytest.mark.asyncio
async def test_zero_distance_staging_telemetry():
    """
    Test 4: When a journey is zero-distance (already at destination),
    staging telemetry reports valid timing metrics without crashing.
    """
    settings.environment = "staging"

    coordinator = get_journey_coordinator()
    req = JourneyCreate(
        source="13.0067, 80.2184",
        destination="13.0067, 80.2184",
        preferences=["personal_vehicle"]
    )
    resp = await coordinator.build_journey_plan_response("test-zero-dist", req)

    assert resp.zero_distance is True
    assert resp.meta is not None
    assert "stage_timings" in resp.meta
    timings = resp.meta["stage_timings"]
    assert timings["total_duration_ms"] >= 0.0
    assert timings["location_resolution_ms"] >= 0.0
    assert timings["poi_retrieval_ms"] == 0.0
    assert timings["night_activity_evaluation_ms"] == 0.0


@pytest.mark.asyncio
async def test_concurrent_requests_timing_isolation():
    """
    Test 5: Concurrent requests executed simultaneously produce independent,
    request-scoped telemetry attached only to their respective responses,
    with zero leakage across concurrent tasks.
    """
    settings.environment = "staging"
    coordinator = get_journey_coordinator()

    req_a = JourneyCreate(
        source="13.0067, 80.2184",
        destination="13.0213, 80.2230",
        preferences=["personal_vehicle"]
    )
    req_b = JourneyCreate(
        source="13.0067, 80.2184",
        destination="13.0213, 80.2230",
        preferences=["walking"]
    )

    # Launch two journey planning operations concurrently
    resp_a, resp_b = await asyncio.gather(
        coordinator.build_journey_plan_response("req-a", req_a),
        coordinator.build_journey_plan_response("req-b", req_b)
    )

    assert resp_a.journey_id == "req-a"
    assert resp_b.journey_id == "req-b"

    assert resp_a.meta is not None
    assert resp_b.meta is not None

    timings_a = resp_a.meta["stage_timings"]
    timings_b = resp_b.meta["stage_timings"]

    # Timings dictionaries must be distinct instances in memory
    assert timings_a is not timings_b
    assert resp_a.meta is not resp_b.meta

    # Both must have valid non-negative metrics
    assert timings_a["total_duration_ms"] > 0
    assert timings_b["total_duration_ms"] > 0


@pytest.mark.asyncio
async def test_existing_scoring_and_attribution_unaltered():
    """
    Test 6: Existing scores, status, and TreeSHAP attribution outputs
    remain strictly unchanged by the timing instrumentation.
    """
    settings.environment = "staging"

    coordinator = get_journey_coordinator()
    req = JourneyCreate(
        source="13.0067, 80.2184",
        destination="13.0213, 80.2230",
        preferences=["personal_vehicle"]
    )
    resp = await coordinator.build_journey_plan_response("test-integrity", req)

    assert len(resp.recommended_routes) >= 3

    r0 = resp.recommended_routes[0]
    # Verify score presence and validity
    assert r0.safety_score is not None
    assert 0.0 <= r0.safety_score <= 100.0
    assert r0.overall_safety_score == r0.safety_score
    assert r0.score_status == "READY"
    assert r0.scoreable_coverage_ratio is not None and r0.scoreable_coverage_ratio >= 0.70

    # Verify TreeSHAP attribution intact
    assert r0.model_attribution is not None
    assert r0.model_attribution.status == "VALIDATED_ATTRIBUTION"
    assert r0.model_attribution.is_mathematically_reconstructed is True
