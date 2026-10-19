import pytest
from unittest.mock import patch, MagicMock
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.models.journey import CandidateRoute, Location
from app.intelligence.journey.deduplication import deduplicate_routes
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.schemas.journey_schemas import JourneyCreate


def test_deduplication_preserves_distinct_modes():
    """Verify that different transport modes sharing the same corridor are not collapsed."""
    c1 = CandidateRoute(
        route_identifier="c1",
        distance=2000.0,
        duration=300.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Personal Vehicle",
            "transport_mode": "driving",
            "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}
        }
    )
    c2 = CandidateRoute(
        route_identifier="c2",
        distance=2000.0,
        duration=420.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Two Wheeler",
            "transport_mode": "two_wheeler",
            "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}
        }
    )
    c3 = CandidateRoute(
        route_identifier="c3",
        distance=2000.0,
        duration=1500.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Walking",
            "transport_mode": "walking",
            "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}
        }
    )
    
    deduped = deduplicate_routes([c1, c2, c3])
    assert len(deduped) == 3, "Distinct transport modes should not be collapsed into one route"
    names = [c.route_metadata.get("route_name") for c in deduped]
    assert "Personal Vehicle" in names
    assert "Two Wheeler" in names
    assert "Walking" in names


def test_deduplication_removes_identical_routes_within_same_mode():
    """Verify that identical routes within the same mode are properly deduplicated."""
    c1 = CandidateRoute(
        route_identifier="c1",
        distance=2000.0,
        duration=300.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Personal Vehicle",
            "transport_mode": "driving",
            "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}
        }
    )
    c2 = CandidateRoute(
        route_identifier="c2",
        distance=2000.0,
        duration=300.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Personal Vehicle",
            "transport_mode": "driving",
            "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}
        }
    )
    
    deduped = deduplicate_routes([c1, c2])
    assert len(deduped) == 1, "Identical route geometry and mode should be deduplicated"


def test_route_ranking_orders_highest_safety_score_first():
    """Verify ML route scoring sorts highest valid safety score first, with unscored at the end."""
    c_safe = CandidateRoute(
        route_identifier="c_safe",
        distance=5000.0,
        duration=900.0,
        recommendation_status="CANDIDATE",
        route_metadata={"route_name": "Safe Route", "transport_mode": "driving", "geometry": {"coordinates": [[80.15, 12.84], [80.14, 12.85]]}}
    )
    c_lower = CandidateRoute(
        route_identifier="c_lower",
        distance=4500.0,
        duration=840.0,
        recommendation_status="CANDIDATE",
        route_metadata={"route_name": "Lower Score Route", "transport_mode": "driving", "geometry": {"coordinates": [[80.15, 12.84], [80.145, 12.845], [80.14, 12.85]]}}
    )
    c_unscored = CandidateRoute(
        route_identifier="c_unscored",
        distance=6000.0,
        duration=1200.0,
        recommendation_status="CANDIDATE",
        route_metadata={"route_name": "Transit Route", "transport_mode": "transit", "geometry": {"coordinates": [[80.15, 12.84], [80.14, 12.85]]}}
    )
    
    mock_matcher = MagicMock()
    scoring_service = MLRouteScoringService(spatial_matcher=mock_matcher)
    
    # Mock score_candidate_route to return pre-computed scores
    def mock_score(cand):
        meta = cand.route_metadata
        if cand.route_identifier == "c_safe":
            meta["safety_score"] = 85.5
            meta["score_status"] = "READY"
        elif cand.route_identifier == "c_lower":
            meta["safety_score"] = 60.2
            meta["score_status"] = "READY"
        else:
            meta["safety_score"] = None
            meta["score_status"] = "INSUFFICIENT_COVERAGE"
        return MagicMock()
        
    with patch.object(scoring_service, "score_candidate_route", side_effect=mock_score):
        candidates = [c_lower, c_safe, c_unscored]
        scoring_service.score_candidate_routes(candidates)
        
        assert len(candidates) == 3
        # Route with 85.5 score must be first
        assert candidates[0].route_identifier == "c_safe"
        assert candidates[0].route_metadata.get("safety_score") == 85.5
        # Route with 60.2 score must be second
        assert candidates[1].route_identifier == "c_lower"
        assert candidates[1].route_metadata.get("safety_score") == 60.2
        # Unscored route must be third with null score preserved
        assert candidates[2].route_identifier == "c_unscored"
        assert candidates[2].route_metadata.get("safety_score") is None
        assert candidates[2].route_metadata.get("score_status") == "INSUFFICIENT_COVERAGE"


@pytest.mark.asyncio
async def test_missing_gemini_key_handles_gracefully():
    """Verify that when GEMINI_API_KEY is not set or empty, reasoning tool safely returns empty candidates without crashing."""
    from app.tools.specialized.reasoning_tool import ReasoningTool
    
    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value=""):
        tool = ReasoningTool()
        candidates = await tool.generate_dynamic_plans("12.84, 80.15", "12.85, 80.14", 2.0, ["driving", "transit"])
        assert candidates == []


@pytest.mark.asyncio
async def test_coordinator_generates_diverse_candidates_for_local_trip():
    """Verify coordinator generates multiple valid routes (Personal Vehicle, Alternative Road, Two Wheeler, Walking) for local trip."""
    coordinator = JourneyIntelligenceCoordinator()
    
    # Return realistic mode-specific mock routes
    async def mock_get_routes(s, e, mode="driving", alternatives="false", waypoints=None):
        if waypoints:
            return [CandidateRoute(
                route_identifier="mock_alt",
                distance=2100.0,
                duration=240.0,
                recommendation_status="AVAILABLE",
                route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.15271, 12.84480], [80.149, 12.843], [80.1403, 12.8495]]}}
            )]
        elif mode == "bike":
            return [CandidateRoute(
                route_identifier="mock_bike",
                distance=1700.0,
                duration=360.0,
                recommendation_status="AVAILABLE",
                route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.15271, 12.84480], [80.1465, 12.8470], [80.1403, 12.8495]]}}
            )]
        elif mode == "foot":
            return [CandidateRoute(
                route_identifier="mock_foot",
                distance=1700.0,
                duration=1260.0,
                recommendation_status="AVAILABLE",
                route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.15271, 12.84480], [80.1465, 12.8470], [80.1403, 12.8495]]}}
            )]
        else:
            return [CandidateRoute(
                route_identifier="mock_drive",
                distance=1700.0,
                duration=180.0,
                recommendation_status="AVAILABLE",
                route_metadata={"geometry": {"type": "LineString", "coordinates": [[80.15271, 12.84480], [80.1465, 12.8470], [80.1403, 12.8495]]}}
            )]
    
    with patch("app.providers.routing.provider.OSRMRoutingProvider.get_routes", side_effect=mock_get_routes):
        req = JourneyCreate(
            source="12.84480, 80.15271",
            destination="12.8495, 80.1403",
            preferences=["driving", "transit"]
        )
        response = await coordinator.build_journey_plan_response("test_journey_1", req)
        
        assert len(response.recommended_routes) >= 3, f"Expected at least 3 candidates, got {len(response.recommended_routes)}"
        names = [r.route_name for r in response.recommended_routes]
        assert "Personal Vehicle" in names
        assert "Two Wheeler" in names
        assert "Walking" in names
