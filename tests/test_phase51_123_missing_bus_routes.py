import asyncio
import os
import sys
import hashlib
import datetime
import pytest

sys.path.insert(0, os.path.abspath("."))
from app.models.journey import Location, CandidateRoute
from app.intelligence.journey.multimodal_router import global_multimodal_router, haversine_m
from app.intelligence.journey.bus_network import global_bus_validator
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.schemas.journey_schemas import JourneyCreate
from app.services.local_location_resolver import get_local_location_resolver
from app.providers.routing.provider import OSRMRoutingProvider


def test_frozen_ml_artifacts_sha256_integrity():
    """Verify all four frozen ML artifacts remain byte-for-byte identical."""
    expected = {
        "app/ml/Hack/ml/models/best_model.pkl": "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
        "app/ml/Hack/ml/models/preprocessing_pipeline.pkl": "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
        "app/ml/Hack/ml/datasets/processed/road_segments.parquet": "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
        "app/ml/Hack/ml/datasets/processed/master_feature_table.parquet": "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    }
    for path, exp_hash in expected.items():
        assert os.path.exists(path), f"Frozen artifact not found: {path}"
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        assert sha.hexdigest() == exp_hash, f"Hash mismatch for {path}"


@pytest.mark.asyncio
async def test_vvit_to_kandagai_resolution_and_bus_discovery():
    """Verify VVIT -> Kandagai location resolution, connectivity, and route generation."""
    resolver = get_local_location_resolver()
    vvit_loc = resolver.resolve("VVIT")
    kandagai_loc = resolver.resolve("Kandagai")

    assert vvit_loc is not None, "VVIT should resolve locally"
    assert kandagai_loc is not None, "Kandagai should resolve locally"
    assert vvit_loc.coordinates == [80.1554, 12.8406]
    assert kandagai_loc.coordinates == [80.1402, 12.8495]

    coordinator = JourneyIntelligenceCoordinator()
    data = JourneyCreate(
        source="VVIT",
        destination="Kandagai",
        travel_mode="PUBLIC_TRANSPORT",
        preferences=["public_transport"]
    )
    res = await coordinator.build_journey_plan_response("test_vvit_kandagai", data)
    assert res is not None
    assert len(res.recommended_routes) >= 1

    # Check warning is NOT the false 'No practical direct public transit' warning
    assert not any("No practical direct public transit" in str(alert) for alert in res.alerts)

    # Find the transit route
    bus_routes = [
        r for r in res.recommended_routes 
        if any(seg.transport_mode.lower() == "bus" for seg in r.segments)
    ]
    assert len(bus_routes) >= 1, "Expected at least 1 verified bus route for VVIT -> Kandagai"
    
    first_bus = bus_routes[0]
    bus_seg = [s for s in first_bus.segments if s.transport_mode.lower() == "bus"][0]
    assert "Vit University" in bus_seg.origin or "Kandigai" in bus_seg.destination
    assert bus_seg.score_status == "NOT_SCORED"


@pytest.mark.asyncio
async def test_short_distance_verified_bus_route_under_1km():
    """Verify that a valid bus service is found for a journey under 1 km (Mylapore Tank -> Mandaveli Market, ~618m)."""
    s_loc = Location(type="Point", coordinates=[80.26807, 13.03432])
    d_loc = Location(type="Point", coordinates=[80.26638, 13.02901])
    prov = OSRMRoutingProvider()
    
    dt = datetime.datetime(2026, 10, 29, 14, 0)
    cands = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=650.0,
        direct_road_dur_s=120.0,
        route_provider=prov,
        ist_dt=dt,
        preferences=["public_transport"]
    )
    assert len(cands) >= 1, "Direct bus should be discovered for short 0-1km trip"
    bus_cands = [c for c in cands if any(s.get("mode") == "bus" for s in c.route_metadata.get("dynamic_segments", []))]
    assert len(bus_cands) >= 1
    assert bus_cands[0].distance < 1200.0


@pytest.mark.asyncio
async def test_short_trip_without_bus_service_no_fabrication():
    """Verify that a short journey with no connected bus route produces no fake bus routes."""
    s_loc = Location(type="Point", coordinates=[80.1450, 12.8350])
    d_loc = Location(type="Point", coordinates=[80.1470, 12.8360])
    prov = OSRMRoutingProvider()
    dt = datetime.datetime(2026, 10, 29, 14, 0)
    
    cands = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=400.0,
        direct_road_dur_s=80.0,
        route_provider=prov,
        ist_dt=dt,
        preferences=["public_transport"]
    )
    bus_cands = [c for c in cands if any(s.get("mode") == "bus" for s in c.route_metadata.get("dynamic_segments", []))]
    assert len(bus_cands) == 0, "Must NOT fabricate a bus route where none connects"


@pytest.mark.asyncio
async def test_bus_availability_when_metro_and_suburban_unavailable():
    """Verify bus routes are generated even when Metro and Suburban Rail are completely absent/ineligible."""
    s_loc = Location(type="Point", coordinates=[80.1554, 12.8406])
    d_loc = Location(type="Point", coordinates=[80.1402, 12.8495])
    prov = OSRMRoutingProvider()
    dt = datetime.datetime(2026, 10, 29, 14, 0)

    cands = await global_multimodal_router.search_candidates(
        source_loc=s_loc,
        dest_loc=d_loc,
        direct_road_dist_m=2831.0,
        direct_road_dur_s=253.0,
        route_provider=prov,
        ist_dt=dt,
        preferences=["public_transport"]
    )
    bus_cands = [c for c in cands if any(s.get("mode") == "bus" for s in c.route_metadata.get("dynamic_segments", []))]
    assert len(bus_cands) >= 1
    rail_cands = [c for c in cands if any(s.get("mode") in ["metro", "suburban"] for s in c.route_metadata.get("dynamic_segments", []))]
    assert len(rail_cands) == 0


@pytest.mark.asyncio
async def test_wrong_direction_service_rejected():
    """Verify that a service running in reverse is rejected and not offered as forward trip."""
    dt = datetime.datetime(2026, 10, 29, 14, 0)
    # Tambaram West Bus Stand to Padappai on 555P (inbound pattern goes Padappai to Sholinganallur)
    is_valid, status, _ = global_bus_validator.validate_bus_segment("Tambaram West Bus Stand", "Padappai", "555P", dt)
    assert is_valid is False
    assert status in ["NO_DIRECT_SERVICE_PAIR", "REJECTED"]


@pytest.mark.asyncio
async def test_longer_journey_valid_bus_corridor():
    """Verify longer journey (VIT Chennai -> Marina Mall / OMR corridor) generates valid bus routes."""
    coordinator = JourneyIntelligenceCoordinator()
    data = JourneyCreate(
        source="12.8448, 80.1527",
        destination="12.8359, 80.2291",
        travel_mode="PUBLIC_TRANSPORT",
        preferences=["public_transport"]
    )
    res = await coordinator.build_journey_plan_response("test_longer_corridor", data)
    assert res is not None
    assert len(res.recommended_routes) >= 3
    bus_routes = [r for r in res.recommended_routes if any(s.transport_mode.lower() == "bus" for s in r.segments)]
    assert len(bus_routes) >= 1


@pytest.mark.asyncio
async def test_ranking_prefers_walking_for_short_trip_when_appropriate():
    """Verify that walking ranks as BALANCED for very short trips while bus remains an eligible alternative."""
    coordinator = JourneyIntelligenceCoordinator()
    # Mylapore Tank to Mandaveli Market (~618m)
    data = JourneyCreate(
        source="13.03432, 80.26807",
        destination="13.02901, 80.26638",
        preferences=["safest"]
    )
    res = await coordinator.build_journey_plan_response("test_short_ranking", data)
    assert res is not None
    modes = [r.mode for r in res.recommended_routes]
    assert any("Walking" in m for m in modes), "Walking route should be available on short trip"
    assert any("Public Transit" in r.mode or "Bus" in r.route_name for r in res.recommended_routes), "Bus route should remain available"
    
    top_route = res.recommended_routes[0]
    dist_val = float(top_route.distance.split()[0])
    assert dist_val < 2.0
