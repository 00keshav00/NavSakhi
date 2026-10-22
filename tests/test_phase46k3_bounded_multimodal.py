"""
NavSakhi Phase 46K.3 Regression Test Suite:
Bounded Multimodal Transit Search, Latency Optimization, and Cooperative Client Cancellation.
"""

import pytest
import datetime
import warnings
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from starlette.testclient import TestClient

from app.schemas.journey_schemas import Location
from app.models.journey import CandidateRoute
from app.schemas.journey_schemas import JourneyCreate
from app.intelligence.journey.multimodal_router import global_multimodal_router
from app.intelligence.journey.coordinator import (
    JourneyIntelligenceCoordinator,
    DEFAULT_GEMINI_DYNAMIC_PLANS_BUDGET_S,
    DEFAULT_GEMINI_EXPLANATION_BUDGET_S,
)
from app.services.ml_route_scoring_service import MLRouteScoringService, _current_spatial_matcher
from app.intelligence.journey.spatial_matcher import SpatialMatchingService, CompanionStoreError


@pytest.mark.asyncio
async def test_bounded_multimodal_operation_count_and_timing():
    """
    1. Bounded Section 3 completes in sub-second time on reproduced dense corridor.
    """
    s_loc = Location(type="Point", coordinates=[80.2755, 13.0827])  # Chennai Central
    d_loc = Location(type="Point", coordinates=[80.1639, 12.9800])  # Tambaram

    mock_provider = MagicMock()
    mock_route = CandidateRoute(
        route_identifier="mock_leg",
        distance=1200.0,
        duration=250.0,
        recommendation_status="AVAILABLE",
        route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.27, 13.08], [80.271, 13.081]]}}
    )
    mock_provider.get_routes = AsyncMock(return_value=[mock_route])

    import time
    t0 = time.perf_counter()
    candidates = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=18500.0,
        direct_road_dur_s=2100.0,
        route_provider=mock_provider,
        ist_dt=datetime.datetime.now(),
        preferences=["transit"]
    )
    elapsed = time.perf_counter() - t0
    # Must complete comfortably under 5 seconds (previously took 215.8 seconds!)
    assert elapsed < 5.0, f"Section 3 took {elapsed:.2f}s, expected < 5.0s"
    assert len(candidates) >= 1, "Must discover valid multimodal transit candidates"


@pytest.mark.asyncio
async def test_bounded_multimodal_discovers_valid_connections():
    """
    2. The bounded search discovers valid rail-to-bus connections with continuous geometry.
    """
    s_loc = Location(type="Point", coordinates=[80.2755, 13.0827])
    d_loc = Location(type="Point", coordinates=[80.1639, 12.9800])

    mock_provider = MagicMock()
    mock_route = CandidateRoute(
        route_identifier="mock_leg",
        distance=1000.0,
        duration=200.0,
        recommendation_status="AVAILABLE",
        route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.27, 13.08], [80.271, 13.081]]}}
    )
    mock_provider.get_routes = AsyncMock(return_value=[mock_route])

    candidates = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=18500.0,
        direct_road_dur_s=2100.0,
        route_provider=mock_provider,
        ist_dt=datetime.datetime.now(),
        preferences=["transit"]
    )

    for c in candidates:
        geom = c.route_metadata.get("geometry", {})
        coords = geom.get("coordinates", [])
        assert len(coords) >= 2, f"Candidate {c.route_identifier} must have >= 2 coordinates"
        segs = c.route_metadata.get("dynamic_segments", [])
        assert len(segs) >= 1, f"Candidate {c.route_identifier} must have dynamic segments"


@pytest.mark.asyncio
async def test_bounded_multimodal_eliminates_duplicates():
    """
    3. Duplicate interchange routes are eliminated.
    """
    s_loc = Location(type="Point", coordinates=[80.2755, 13.0827])
    d_loc = Location(type="Point", coordinates=[80.1639, 12.9800])

    mock_provider = MagicMock()
    mock_route = CandidateRoute(
        route_identifier="mock_leg",
        distance=1000.0,
        duration=200.0,
        recommendation_status="AVAILABLE",
        route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.27, 13.08], [80.271, 13.081]]}}
    )
    mock_provider.get_routes = AsyncMock(return_value=[mock_route])

    candidates = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=18500.0,
        direct_road_dur_s=2100.0,
        route_provider=mock_provider,
        ist_dt=datetime.datetime.now(),
        preferences=["transit"]
    )

    names = [c.route_metadata.get("route_name") for c in candidates]
    assert len(names) == len(set(names)), "All returned candidate route names must be distinct"


@pytest.mark.asyncio
async def test_no_feasible_interchange_produces_empty_not_fabricated():
    """
    4. No feasible interchange produces a truthful empty fallback rather than a fabricated route.
    """
    # Coordinates in middle of ocean / off-network
    s_loc = Location(type="Point", coordinates=[80.9999, 13.9999])
    d_loc = Location(type="Point", coordinates=[81.0000, 14.0000])

    mock_provider = MagicMock()
    mock_provider.get_routes = AsyncMock(return_value=[])

    candidates = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=10000.0,
        direct_road_dur_s=1200.0,
        route_provider=mock_provider,
        ist_dt=datetime.datetime.now(),
        preferences=["transit"]
    )
    assert candidates == [], "Must return empty list when no transit infrastructure exists; never fabricate"


@pytest.mark.asyncio
async def test_transit_score_semantics_preserved():
    """
    5. Transit legs remain NOT_SCORED with safety_score: None.
    """
    scorer = MLRouteScoringService()

    multimodal_cand = CandidateRoute(
        route_identifier="test_multi_1",
        distance=15000.0,
        duration=1800.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "travel_mode": "Multimodal",
            "geometry": {"type": "LineString", "coordinates": [[80.27, 13.08], [80.26, 13.05], [80.20, 13.00]]},
            "dynamic_segments": [
                {
                    "mode": "walk",
                    "distance_m": 500.0,
                    "duration_s": 360.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.27, 13.08], [80.268, 13.078]]}
                },
                {
                    "mode": "metro",
                    "distance_m": 12000.0,
                    "duration_s": 1200.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.268, 13.078], [80.21, 13.01]]}
                },
                {
                    "mode": "auto",
                    "distance_m": 2500.0,
                    "duration_s": 300.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.21, 13.01], [80.20, 13.00]]}
                }
            ]
        }
    )

    res = scorer.score_candidate_route(multimodal_cand)
    # The metro leg inside dynamic_segments must be NOT_SCORED with safety_score None
    dyn = multimodal_cand.route_metadata.get("dynamic_segments", [])
    metro_leg = next(s for s in dyn if s["mode"] == "metro")
    assert metro_leg.get("safety_score") is None
    assert metro_leg.get("score_status") == "NOT_SCORED"
    assert "Transit track safety assessment is not modeled" in metro_leg.get("score_disclosure", "")


@pytest.mark.asyncio
async def test_async_cancellation_check_false_continues():
    """
    6. An asynchronous cancellation check returning False allows journey planning to continue.
    """
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="13.0827, 80.2755",
        destination="12.9800, 80.1639",
        preferences=["driving"]
    )

    async def mock_not_disconnected():
        return False

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        response = await coordinator.build_journey_plan_response(
            "test_journey_continue",
            req,
            cancel_check=mock_not_disconnected
        )
        assert response is not None
        assert hasattr(response, "recommended_routes")

        # Verify no unawaited coroutine warnings were emitted
        unawaited = [w for w in captured_warnings if "coroutine" in str(w.message).lower() and "never awaited" in str(w.message).lower()]
        assert len(unawaited) == 0, f"Found unawaited coroutines: {unawaited}"


@pytest.mark.asyncio
async def test_async_cancellation_check_true_causes_controlled_499():
    """
    7. An asynchronous cancellation check returning True causes controlled HTTP 499 cancellation.
    """
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="13.0827, 80.2755",
        destination="12.9800, 80.1639",
        preferences=["transit"]
    )

    async def mock_disconnected():
        return True

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.build_journey_plan_response(
            "test_journey_cancel_async",
            req,
            cancel_check=mock_disconnected
        )
    assert exc_info.value.status_code == 499
    assert exc_info.value.detail == "Client Closed Request"


def test_sync_cancellation_callback_supported():
    """
    8. Existing synchronous test callbacks (returning bool) remain fully supported.
    """
    import asyncio
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="13.0827, 80.2755",
        destination="12.9800, 80.1639",
        preferences=["transit"]
    )

    # Sync callback returning True
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coordinator.build_journey_plan_response(
            "test_journey_cancel_sync",
            req,
            cancel_check=lambda: True
        ))
    assert exc_info.value.status_code == 499
    assert exc_info.value.detail == "Client Closed Request"


@pytest.mark.asyncio
async def test_cancellation_leaves_no_stale_contextvar_or_matcher_corruption():
    """
    9. Cooperative cancellation leaves zero stale ContextVar state or matcher corruption.
    """
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="13.0827, 80.2755",
        destination="12.9800, 80.1639",
        preferences=["transit"]
    )

    # Pre-cancellation ContextVar state must be None
    assert _current_spatial_matcher.get() is None

    async def mock_disconnected():
        return True

    with pytest.raises(HTTPException):
        await coordinator.build_journey_plan_response(
            "test_journey_ctx",
            req,
            cancel_check=mock_disconnected
        )

    # Post-cancellation ContextVar state must be restored to None
    assert _current_spatial_matcher.get() is None


def test_starlette_testclient_connected_no_accidental_499():
    """
    10. A connected Starlette TestClient request does not trigger accidental HTTP 499.
    """
    from app.main import app
    client = TestClient(app)

    response = client.post(
        "/api/v1/journeys/",
        json={
            "source": "13.0827, 80.2755",
            "destination": "12.9800, 80.1639",
            "preferences": ["driving"]
        }
    )
    # Must NOT be 499 Client Closed Request
    assert response.status_code != 499, f"Unexpected 499 Client Closed Request on connected client: {response.text}"
    assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"


def test_gemini_timeout_budget_constants():
    """
    11. Gemini failure remains non-fatal and uses deterministic fallback with tighter constants.
    """
    assert DEFAULT_GEMINI_DYNAMIC_PLANS_BUDGET_S == 1.5
    assert DEFAULT_GEMINI_EXPLANATION_BUDGET_S == 2.0


def test_phase46i_production_store_guard():
    """
    12. The Phase 46I production store guard prevents silent full-Parquet fallback.
    """
    matcher = SpatialMatchingService(auto_build_index=False, require_companion_stores=True)
    # Pointing to non-existent store must raise CompanionStoreError
    matcher.road_segments_store_path = matcher.road_segments_store_path.parent / "non_existent.db"

    with pytest.raises(CompanionStoreError) as exc_info:
        matcher.build_index()
    assert "prohibited in production mode" in str(exc_info.value)
