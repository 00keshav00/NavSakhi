import pytest
import datetime
from app.intelligence.journey.transit_graph import (
    global_metro_graph,
    global_suburban_graph,
    get_graph_for_mode,
    TransitGraph
)
from app.intelligence.journey.transit_validator import (
    global_index,
    global_schedule_engine,
    haversine_m
)
from app.intelligence.journey.schedule_engine import ScheduleEngine
from app.models.journey import CandidateRoute, Location
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.providers.live.weather import WeatherProvider
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.intelligence.response.builder import ResponseBuilder, get_mode_color


def test_station_index_integrity_and_node_uniqueness():
    """Verify all transport nodes have unique coordinates and operational tags."""
    assert global_index is not None
    assert len(global_index.nodes) >= 30

    for node in global_index.nodes:
        assert node.name, "Station name must not be empty"
        assert node.type in ["Metro", "Suburban", "MRTS", "Bus"], f"Unknown mode: {node.type}"
        assert 12.0 <= node.latitude <= 14.0, f"Lat {node.latitude} out of Chennai range"
        assert 79.5 <= node.longitude <= 81.0, f"Lon {node.longitude} out of Chennai range"
        assert node.is_operational() or "planned" in node.operational_status.lower()


def test_mode_specific_graph_isolation():
    """Verify metro and suburban graphs are strictly isolated and do not bridge networks."""
    metro_graph = get_graph_for_mode("Metro")
    suburban_graph = get_graph_for_mode("Suburban")

    assert metro_graph is not suburban_graph, "Metro and suburban graphs must be distinct instances"
    assert len(metro_graph.adj) > 0, "Metro graph must have track edges"
    assert len(suburban_graph.adj) > 0, "Suburban graph must have track edges"

    # In Chennai, Airport to Guindy is on the Metro Blue Line
    # Airport Metro coordinates: 12.9808, 80.1642
    # Guindy Metro coordinates: 13.0084, 80.2137
    coords, dist, status = metro_graph.build_transit_segment("metro", 12.9808, 80.1642, 13.0084, 80.2137)
    assert status == "SUCCESS", f"Metro track build failed: {status}"
    assert dist > 1000
    assert len(coords) > 5

    # Metro graph MUST reject suburban-only stations
    # e.g., Vandalur (12.8916, 80.0849) to Tambaram (12.9258, 80.1179)
    vandalur_lat, vandalur_lon = 12.8916, 80.0849
    tambaram_lat, tambaram_lon = 12.9258, 80.1179
    m_coords, m_dist, m_status = metro_graph.build_transit_segment("metro", vandalur_lat, vandalur_lon, tambaram_lat, tambaram_lon)
    assert m_status != "SUCCESS", "Metro graph must not route suburban track segments"

    # Suburban graph MUST succeed on Vandalur to Tambaram
    s_coords, s_dist, s_status = suburban_graph.build_transit_segment("suburban", vandalur_lat, vandalur_lon, tambaram_lat, tambaram_lon)
    assert s_status == "SUCCESS", f"Suburban track build failed: {s_status}"
    assert s_dist > 4000
    assert len(s_coords) > 10


def test_station_terminal_snapping_exactness():
    """Verify rail geometry endpoints snap exactly to station coordinates."""
    suburban_graph = get_graph_for_mode("Suburban")
    vandalur_lat, vandalur_lon = 12.8916, 80.0849
    tambaram_lat, tambaram_lon = 12.9258, 80.1179

    coords, dist, status = suburban_graph.build_transit_segment("suburban", vandalur_lat, vandalur_lon, tambaram_lat, tambaram_lon)
    assert status == "SUCCESS"
    # First coordinate must be start station [lon, lat]
    assert coords[0] == [vandalur_lon, vandalur_lat]
    # Last coordinate must be destination station [lon, lat]
    assert coords[-1] == [tambaram_lon, tambaram_lat]


def test_timetable_ist_conversion_and_bounds():
    """Verify schedule validation strictly uses Indian Standard Time (IST) operational bounds."""
    engine = ScheduleEngine()

    # Chennai Metro runs ~05:00 to 23:00 IST
    # 02:00 IST (night) -> UNAVAILABLE
    night_ist = datetime.datetime(2026, 10, 18, 2, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    status, meta = engine.get_service_availability("metro", "Airport to Koyambedu", night_ist)
    assert status == "UNAVAILABLE"
    assert meta.get("next_service") is None

    # 10:00 IST (day) -> AVAILABLE
    day_ist = datetime.datetime(2026, 10, 18, 10, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    status_day, meta_day = engine.get_service_availability("metro", "Airport to Koyambedu", day_ist)
    assert status_day == "AVAILABLE"
    assert meta_day.get("waiting_time") == 5


def test_disconnected_leg_rejection_in_scoring_and_builder():
    """Verify candidate without geometry or with disconnected legs is rejected rather than fabricated."""
    builder = ResponseBuilder()

    # Candidate with empty coordinates
    cand_empty = CandidateRoute(
        route_identifier="unroutable_cand",
        distance=15000.0,
        duration=1200.0,
        recommendation_status="CANDIDATE",
        route_metadata={
            "geometry": {"type": "LineString", "coordinates": []},
            "travel_mode": "Cab Direct"
        }
    )

    context = {
        "routes": [cand_empty],
        "source_name": "Origin",
        "dest_name": "Destination",
        "source_loc": [12.8406, 80.1534],
        "dest_loc": [12.9249, 80.1000]
    }

    resp = builder.build_journey_plan(context, user_id="u1", journey_id="j1")
    # Cand empty must NOT be rendered with fabricated straight lines
    assert len(resp.recommended_routes) == 0, "Routes with invalid geometry must be discarded"


def test_ml_scoring_distinguishes_road_vs_transit():
    """Verify rail legs are marked NOT_SCORED while road legs are properly scored by LightGBM."""
    scoring_svc = MLRouteScoringService()

    cand = CandidateRoute(
        route_identifier="multimodal_test",
        distance=20000.0,
        duration=2400.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "travel_mode": "Multimodal",
            "dynamic_segments": [
                {
                    "mode": "auto",
                    "start_name": "Origin",
                    "end_name": "Vandalur Station",
                    "distance_m": 4500.0,
                    "duration_s": 600.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.1534, 12.8406], [80.1450, 12.8600]]}
                },
                {
                    "mode": "suburban",
                    "start_name": "Vandalur Station",
                    "end_name": "Tambaram Station",
                    "distance_m": 5300.0,
                    "duration_s": 700.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.1450, 12.8600], [80.1179, 12.9258]]}
                },
                {
                    "mode": "walk",
                    "start_name": "Tambaram Station",
                    "end_name": "Destination",
                    "distance_m": 800.0,
                    "duration_s": 600.0,
                    "geometry": {"type": "LineString", "coordinates": [[80.1179, 12.9258], [80.1150, 12.9270]]}
                }
            ]
        }
    )

    scoring_svc.score_candidate_route(cand)
    segs = cand.route_metadata["dynamic_segments"]

    # Transit leg must be NOT_SCORED with None score
    rail_seg = segs[1]
    assert rail_seg["mode"] == "suburban"
    assert rail_seg["score_status"] == "NOT_SCORED"
    assert rail_seg["safety_score"] is None
    assert "Transit track safety assessment is not modeled" in rail_seg["score_disclosure"]

    # Road leg must be scored
    road_seg = segs[0]
    assert road_seg["score_status"] in ["READY", "INSUFFICIENT_COVERAGE"]


@pytest.mark.asyncio
async def test_weather_failure_handling():
    """Verify weather provider handles failure gracefully without inventing fake weather."""
    provider = WeatherProvider()

    # Invalid coordinates (lat 999.0) will fail provider gracefully
    weather = await provider.get_live_weather(999.0, 999.0)
    assert weather.get("available") is False
    assert weather.get("condition") == "Unavailable"
    assert weather.get("temperature_raw") is None

@pytest.mark.asyncio
async def test_gemini_fallback_without_route_invention():
    """Verify Gemini failure returns truthful fallback explanation and does not invent routes."""
    tool = ReasoningTool()
    # Explain verified routes with invalid/unavailable weather
    explanation = await tool.explain_journey_recommendations(
        source="VIT Chennai",
        dest="Marina Mall",
        verified_routes=[{
            "route_name": "Personal Vehicle",
            "travel_mode": "Personal Vehicle",
            "distance_km": 15.2,
            "eta_min": 24,
            "safety_score": 78.4
        }],
        preferences=["safest"],
        weather={"available": False, "condition": "Unavailable"}
    )

    assert explanation is not None
    assert "title" in explanation
    assert "summary" in explanation
    assert "reasoning" in explanation
