import pytest
from unittest.mock import patch, MagicMock
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.models.journey import CandidateRoute, Location
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.intelligence.response.builder import ResponseBuilder, get_mode_color
from app.schemas.journey_schemas import JourneyCreate, RouteSegment


def test_get_mode_color_palette():
    """Verify semantic mode palette fulfills exact addendum color specifications."""
    assert get_mode_color("auto") == "#F97316"  # Orange
    assert get_mode_color("metro") == "#8B5CF6"  # Violet
    assert get_mode_color("suburban") == "#3B82F6"  # Blue
    assert get_mode_color("mrts") == "#06B6D4"  # Cyan/Teal
    assert get_mode_color("bus") == "#10B981"  # Green
    assert get_mode_color("walk") == "#EAB308"  # Yellow
    assert get_mode_color("cab") == "#0284C7"  # Bright Blue
    assert get_mode_color("driving") == "#0284C7"
    assert get_mode_color("personal vehicle") == "#0284C7"


def test_multimodal_per_leg_scoring_distinction():
    """Verify road legs receive ML scoring while transit legs strictly receive null score and NOT_SCORED."""
    scoring_svc = MLRouteScoringService()
    
    # Construct a multimodal CandidateRoute with 3 distinct legs: Auto -> Suburban -> Auto
    cand = CandidateRoute(
        route_identifier="multimodal_test_1",
        distance=12000.0,
        duration=1800.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Auto + Suburban + Auto",
            "transport_mode": "multimodal",
            "travel_mode_chain": "Auto -> Suburban -> Auto",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [80.1534, 12.8406], [80.1500, 12.8500],
                    [80.1450, 12.8600], [80.1200, 12.9200],
                    [80.1100, 12.9240], [80.1000, 12.9249]
                ]
            },
            "dynamic_segments": [
                {
                    "name": "Origin -> Vandalur Station",
                    "mode": "auto",
                    "distance": 4500.0,
                    "duration": 600.0,
                    "origin": "Origin",
                    "destination": "Vandalur Station",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.1534, 12.8406], [80.1500, 12.8500]]
                    }
                },
                {
                    "name": "Vandalur -> Tambaram (Suburban Rail)",
                    "mode": "suburban",
                    "distance": 5300.0,
                    "duration": 500.0,
                    "origin": "Vandalur Station",
                    "destination": "Tambaram Station",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.1450, 12.8600], [80.1200, 12.9200]]
                    }
                },
                {
                    "name": "Tambaram Station -> Destination",
                    "mode": "auto",
                    "distance": 2200.0,
                    "duration": 300.0,
                    "origin": "Tambaram Station",
                    "destination": "Destination",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.1100, 12.9240], [80.1000, 12.9249]]
                    }
                }
            ]
        }
    )

    scored = scoring_svc.score_candidate_route(cand)
    segments = cand.route_metadata.get("dynamic_segments", [])
    assert len(segments) == 3

    # Leg 1: Auto (Road ML pipeline evaluated)
    assert segments[0]["mode"] == "auto"
    assert segments[0]["score_status"] in ["READY", "INSUFFICIENT_COVERAGE"]
    assert "LightGBM" in segments[0]["score_source"]

    # Leg 2: Suburban Rail (Strictly NOT_SCORED by road model, score is None)
    assert segments[1]["mode"] == "suburban"
    assert segments[1]["score_status"] == "NOT_SCORED"
    assert segments[1]["safety_score"] is None
    assert segments[1]["score_source"] == "None (Transit infrastructure unrated)"
    assert "not modeled by the road-segment LightGBM pipeline" in segments[1]["score_disclosure"]

    # Leg 3: Auto (Road ML pipeline evaluated)
    assert segments[2]["mode"] == "auto"
    assert segments[2]["score_status"] in ["READY", "INSUFFICIENT_COVERAGE"]
    assert "LightGBM" in segments[2]["score_source"]


def test_builder_populates_per_leg_contract_fields():
    """Verify response builder assigns stable leg_id, sequence, colors, and GeoJSON properties."""
    cand = CandidateRoute(
        route_identifier="cand_multimodal_build",
        distance=8000.0,
        duration=1200.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "route_name": "Walk + Metro + Walk",
            "transport_mode": "multimodal",
            "travel_mode_chain": "Walk -> Metro -> Walk",
            "geometry": {
                "type": "LineString",
                "coordinates": [[80.170, 12.980], [80.175, 12.985], [80.200, 13.010], [80.205, 13.015]]
            },
            "dynamic_segments": [
                {
                    "name": "Origin -> Airport Metro",
                    "mode": "walk",
                    "distance": 800.0,
                    "duration": 600.0,
                    "origin": "Origin",
                    "destination": "Airport Metro",
                    "score_status": "READY",
                    "safety_score": 42.5,
                    "scoreable_coverage_ratio": 0.85,
                    "score_source": "SafeShe LightGBM Road Risk Model v2.0",
                    "score_disclosure": "Pedestrian road proxy score",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.170, 12.980], [80.175, 12.985]]
                    }
                },
                {
                    "name": "Airport -> Guindy (Blue Line)",
                    "mode": "metro",
                    "distance": 6400.0,
                    "duration": 480.0,
                    "origin": "Airport Metro",
                    "destination": "Guindy Metro",
                    "score_status": "NOT_SCORED",
                    "safety_score": None,
                    "scoreable_coverage_ratio": 0.0,
                    "score_source": "None (Transit infrastructure unrated)",
                    "score_disclosure": "Transit safety data unavailable",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.175, 12.985], [80.200, 13.010]]
                    }
                },
                {
                    "name": "Guindy Metro -> Destination",
                    "mode": "walk",
                    "distance": 800.0,
                    "duration": 600.0,
                    "origin": "Guindy Metro",
                    "destination": "Destination",
                    "score_status": "READY",
                    "safety_score": 38.0,
                    "scoreable_coverage_ratio": 0.90,
                    "score_source": "SafeShe LightGBM Road Risk Model v2.0",
                    "score_disclosure": "Pedestrian road proxy score",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[80.200, 13.010], [80.205, 13.015]]
                    }
                }
            ]
        }
    )

    builder = ResponseBuilder()
    context = {
        "routes": [cand],
        "source_name": "Origin",
        "dest_name": "Destination",
        "source_loc": [12.980, 80.170],
        "dest_loc": [13.015, 80.205]
    }
    resp = builder.build_journey_plan(context, user_id="test_user", journey_id="test_journey")

    assert len(resp.recommended_routes) == 1
    route = resp.recommended_routes[0]
    assert len(route.segments) == 3

    # Check Leg 1: Walk
    leg1 = route.segments[0]
    assert leg1.leg_id == "cand_multimodal_build_leg_1"
    assert leg1.sequence == 1
    assert leg1.transport_mode == "Walk"
    assert leg1.color == "#EAB308"
    assert leg1.safety_score == 42.5
    assert leg1.polyline["properties"]["color"] == "#EAB308"
    assert leg1.polyline["properties"]["legIndex"] == 0

    # Check Leg 2: Metro
    leg2 = route.segments[1]
    assert leg2.leg_id == "cand_multimodal_build_leg_2"
    assert leg2.sequence == 2
    assert leg2.transport_mode == "Metro"
    assert leg2.color == "#8B5CF6"
    assert leg2.safety_score is None
    assert leg2.score_status == "NOT_SCORED"
    assert leg2.polyline["properties"]["color"] == "#8B5CF6"
    assert leg2.polyline["properties"]["legIndex"] == 1

    # Check Leg 3: Walk
    leg3 = route.segments[2]
    assert leg3.leg_id == "cand_multimodal_build_leg_3"
    assert leg3.sequence == 3
    assert leg3.transport_mode == "Walk"
    assert leg3.color == "#EAB308"
    assert leg3.safety_score == 38.0


@pytest.mark.asyncio
async def test_end_to_end_multimodal_route_generation():
    """Verify coordinator generates valid connected multimodal route when transit is requested for viable distance."""
    coord = JourneyIntelligenceCoordinator()
    req = JourneyCreate(
        source="12.8406, 80.1534",
        destination="12.9249, 80.1000",
        preferences=["transit"]
    )

    response = await coord.build_journey_plan_response("test_journey_mm", req)
    routes = response.recommended_routes

    assert len(routes) >= 2
    transit_routes = [
        r for r in routes
        if "suburban" in r.route_name.lower()
        or "metro" in r.route_name.lower()
        or "multimodal" in r.travel_mode_chain.lower()
    ]
    assert len(transit_routes) >= 1, "At least one genuine multimodal transit route must be generated"

    tr = transit_routes[0]
    segments = tr.segments
    assert len(segments) >= 2, "Multimodal route must contain at least 2 distinct legs"
    
    # Check that rail leg has actual OSM track coordinates
    rail_legs = [s for s in segments if s.transport_mode.lower() in ["suburban", "metro", "mrts"]]
    assert len(rail_legs) >= 1
    coords = rail_legs[0].polyline["geometry"]["coordinates"]
    assert len(coords) > 10, "Rail leg must follow OSM track geometry, not a straight line"
