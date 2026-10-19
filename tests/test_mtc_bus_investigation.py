import pytest
import os
import hashlib
import datetime
from app.models.journey import Location, CandidateRoute
from app.intelligence.journey.multimodal_router import global_multimodal_router, haversine_m
from app.intelligence.journey.bus_network import global_bus_validator
from app.intelligence.journey.schedule_engine import global_schedule_engine
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.schemas.journey_schemas import JourneyCreate
from app.providers.routing.provider import OSRMRoutingProvider

def test_frozen_ml_artifacts_byte_identical():
    """Verify that all 4 frozen ML artifacts remain byte-for-byte unchanged."""
    expected_hashes = {
        "app/ml/Hack/ml/models/best_model.pkl": "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
        "app/ml/Hack/ml/models/preprocessing_pipeline.pkl": "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
        "app/ml/Hack/ml/datasets/processed/road_segments.parquet": "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
        "app/ml/Hack/ml/datasets/processed/master_feature_table.parquet": "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    }
    for file_path, exp_hash in expected_hashes.items():
        assert os.path.exists(file_path), f"File missing: {file_path}"
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        assert sha.hexdigest() == exp_hash, f"Hash mismatch for {file_path}"

def test_actual_mtc_dataset_loaded():
    """Verify the real MTC GTFS dataset has loaded stops and routes."""
    assert len(global_multimodal_router.bus_stops) >= 5000
    assert len(global_multimodal_router.bus_routes) >= 1000
    # Confirm 555P and 555G are present in actual loaded routes
    services = {r["service_number"] for r in global_multimodal_router.bus_routes}
    assert "555P" in services
    assert "555G" in services

def test_bus_validator_valid_connection():
    """Test valid bus connection between VIT Chennai area and Siruseri/Marina Mall."""
    dt_day = datetime.datetime(2026, 10, 18, 14, 0)
    is_valid, status, meta = global_bus_validator.validate_bus_segment("Vit University", "It Park Siruseri", "555P", dt_day)
    assert is_valid is True
    assert status == "VALID"
    assert meta["service_number"] == "555P"
    assert meta["stop_count"] >= 10

def test_bus_validator_reverse_direction_rejected():
    """A service with stops in reverse direction should not validate as a forward trip."""
    dt_day = datetime.datetime(2026, 10, 18, 14, 0)
    # Trying to travel from IT Park Siruseri to Vit University on a Padappai->Sholinganallur outbound trip pattern
    # Should reject when no matching forward directional pattern exists
    is_valid, status, meta = global_bus_validator.validate_bus_segment("Tambaram West Bus Stand", "Padappai", "555P", dt_day)
    # 555P route 11831 is Padappai to Sholinganallur, and 11834 is Tambaram West to Sholinganallur.
    # Neither goes Tambaram West to Padappai.
    assert is_valid is False
    assert status in ["NO_DIRECT_SERVICE_PAIR", "REJECTED"]

def test_bus_validator_nonexistent_service():
    """Genuinely nonexistent bus service number must be rejected."""
    dt_day = datetime.datetime(2026, 10, 18, 14, 0)
    is_valid, status, meta = global_bus_validator.validate_bus_segment("Vit University", "Sipcot", "9999XYZ", dt_day)
    assert is_valid is False
    assert status == "NO_SUCH_SERVICE"

def test_schedule_engine_operating_hours():
    """Verify ScheduleEngine operating window: daytime available, late night unavailable."""
    dt_day = datetime.datetime(2026, 10, 18, 14, 0)
    status_day, meta_day = global_schedule_engine.get_service_availability("bus", "Bus 555P", dt_day)
    assert status_day == "AVAILABLE"
    assert meta_day["waiting_time"] > 0

    dt_night = datetime.datetime(2026, 10, 18, 2, 0) # 2:00 AM
    status_night, meta_night = global_schedule_engine.get_service_availability("bus", "Bus 555P", dt_night)
    assert status_night == "UNAVAILABLE"
    assert "Operating hours" in meta_night.get("reason", "")

@pytest.mark.asyncio
async def test_vit_to_marina_mall_candidates_generated():
    """Verify that the exact VIT Chennai -> Marina Mall journey generates valid bus candidates."""
    s_lat, s_lon = 12.8448, 80.1527
    d_lat, d_lon = 12.8359, 80.2291
    source_loc = Location(type="Point", coordinates=[s_lon, s_lat])
    dest_loc = Location(type="Point", coordinates=[d_lon, d_lat])

    route_provider = OSRMRoutingProvider()
    direct_road_dist_m = 16784.8
    direct_road_dur_s = 1039.6
    ist_dt = datetime.datetime(2026, 10, 18, 12, 0)

    candidates = await global_multimodal_router.search_candidates(
        source_loc=source_loc,
        dest_loc=dest_loc,
        direct_road_dist_m=direct_road_dist_m,
        direct_road_dur_s=direct_road_dur_s,
        route_provider=route_provider,
        ist_dt=ist_dt,
        preferences=["public_transport"]
    )
    assert len(candidates) >= 1
    # Check that at least one candidate has a bus leg
    bus_cands = [
        c for c in candidates 
        if any(s.get("mode") == "bus" for s in c.route_metadata.get("dynamic_segments", []))
    ]
    assert len(bus_cands) >= 1
    bus_cand = bus_cands[0]
    assert "MTC Bus" in bus_cand.route_metadata.get("route_name", "")
    assert bus_cand.distance > 10000 # at least 10km
    assert bus_cand.duration > 1800 # at least 30 min realistic travel

@pytest.mark.asyncio
async def test_full_journey_plan_includes_bus_and_honest_scores():
    """Verify full coordinator journey response includes bus routes with NOT_SCORED transit legs and no false warning."""
    coordinator = JourneyIntelligenceCoordinator()
    data = JourneyCreate(
        source="12.8448, 80.1527",
        destination="12.8359, 80.2291",
        travel_mode="PUBLIC_TRANSPORT",
        preferences=["public_transport"]
    )
    res = await coordinator.build_journey_plan_response("test_vit_journey", data)
    assert res is not None
    assert len(res.recommended_routes) >= 3

    # Check warning is NOT the 'No practical direct public transit' false warning
    assert not any("No practical direct public transit" in str(alert) for alert in res.alerts)

    # Find the transit route
    transit_routes = [r for r in res.recommended_routes if "Public Transit" in r.mode or "Bus" in r.route_name]
    assert len(transit_routes) >= 1

    bus_route = transit_routes[0]
    assert len(bus_route.segments) == 3 # Walk -> Bus -> Walk
    bus_leg = [s for s in bus_route.segments if s.transport_mode.lower() == "bus"][0]
    assert bus_leg.adjusted_safety_score is None
    assert bus_leg.score_status == "NOT_SCORED"
    assert bus_leg.color == "#10B981"

@pytest.mark.asyncio
async def test_full_journey_plan_with_default_frontend_preferences():
    """Verify that default frontend preferences (preferences=['safest']) generate all 5 alternatives including MTC buses."""
    coordinator = JourneyIntelligenceCoordinator()
    data = JourneyCreate(
        source="12.8448, 80.1527",
        destination="12.8359, 80.2291",
        preferences=["safest"]
    )
    res = await coordinator.build_journey_plan_response("test_frontend_defaults", data)
    assert res is not None
    assert len(res.recommended_routes) >= 5
    assert not any("No practical direct public transit" in str(alert) for alert in res.alerts)

    bus_routes = [r for r in res.recommended_routes if "Public Transit" in r.mode or "Bus" in r.route_name]
    assert len(bus_routes) >= 2
    bus_names = [r.route_name for r in bus_routes]
    assert any("555G" in name for name in bus_names)
    assert any("555P" in name for name in bus_names)

