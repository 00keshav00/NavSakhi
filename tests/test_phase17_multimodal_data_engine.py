import pytest
import os
import json
import hashlib
from app.models.journey import Location
from app.intelligence.journey.multimodal_router import global_multimodal_router, haversine_m
from app.intelligence.journey.bus_network import global_bus_validator
from app.intelligence.journey.deduplication import deduplicate_routes, _get_mode_category
from app.models.journey import CandidateRoute

def test_frozen_ml_artifacts_checksums():
    """Verify that the 4 frozen ML artifacts remain byte-identical to their baseline hashes."""
    baseline_hashes = {
        "app/ml/Hack/ml/models/best_model.pkl": "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
        "app/ml/Hack/ml/models/preprocessing_pipeline.pkl": "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
        "app/ml/Hack/ml/datasets/processed/road_segments.parquet": "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
        "app/ml/Hack/ml/datasets/processed/master_feature_table.parquet": "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    }
    for rel_path, expected_sha in baseline_hashes.items():
        assert os.path.exists(rel_path), f"Frozen artifact missing: {rel_path}"
        sha256 = hashlib.sha256()
        with open(rel_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual_sha = sha256.hexdigest()
        assert actual_sha == expected_sha, f"Frozen artifact altered! Expected {expected_sha}, got {actual_sha} for {rel_path}"

def test_transit_data_manifest():
    """Verify manifest.json exists and documents all ingested feeds."""
    manifest_path = "transit_data/manifest.json"
    assert os.path.exists(manifest_path), "transit_data/manifest.json missing"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert "sources" in manifest
    source_ids = [s["id"] for s in manifest["sources"]]
    assert "cmrl_gtfs" in source_ids
    assert "srr_gtfs" in source_ids
    assert "mtc_gtfs" in source_ids
    
    # Check that SHA-256 digests are recorded
    for s in manifest["sources"]:
        assert "sha256" in s and len(s["sha256"]) == 64
        assert s["status"] == "VERIFIED"

def test_metro_network_graph():
    """Verify Metro network entities: stations, lines, spatial index."""
    metro_file = "transit_data/processed/metro_network.json"
    assert os.path.exists(metro_file)
    with open(metro_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("stations", [])) >= 40
    assert len(data.get("routes", [])) >= 2
    
    # Spatial query for Central
    nearby = global_multimodal_router.query_nearby_stations(13.0827, 80.2755, "metro", max_dist_m=1000.0)
    assert len(nearby) > 0
    names = [s["name"] for s in nearby]
    assert any("Central" in n for n in names)

def test_suburban_rail_network():
    """Verify Southern Railway Suburban/MRTS entities."""
    suburban_file = "transit_data/processed/suburban_network.json"
    assert os.path.exists(suburban_file)
    with open(suburban_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("stations", [])) >= 100
    assert len(data.get("routes", [])) >= 10
    
    # Spatial query for Tambaram
    nearby = global_multimodal_router.query_nearby_stations(12.9249, 80.1197, "suburban", max_dist_m=1000.0)
    assert len(nearby) > 0
    names = [s["name"] for s in nearby]
    assert any("Tambaram" in n for n in names)

def test_mtc_bus_network_and_validator():
    """Verify MTC Bus GTFS integration and BusValidator."""
    import datetime
    bus_file = "transit_data/processed/bus_network.json"
    assert os.path.exists(bus_file)
    with open(bus_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data.get("stops", [])) >= 4000
    assert len(data.get("routes", [])) >= 1000
    
    # Test BusValidator
    dt = datetime.datetime(2026, 10, 18, 10, 0, 0)
    is_valid, status, meta = global_bus_validator.validate_bus_segment("Melakottaiyur", "Kazhipattur", "555P", dt)
    assert is_valid is True
    assert status == "VALID"

def test_mode_differentiation_in_deduplication():
    """Ensure sub-modes (bus, metro, suburban, driving, walk) are categorized distinctly."""
    c_bus = CandidateRoute(route_identifier="c_bus", distance=10000, duration=2400, recommendation_status="AVAILABLE")
    c_bus.route_metadata = {
        "travel_mode": "Multimodal",
        "dynamic_segments": [{"mode": "bus", "service_number": "555P"}]
    }
    c_metro = CandidateRoute(route_identifier="c_metro", distance=10000, duration=1800, recommendation_status="AVAILABLE")
    c_metro.route_metadata = {
        "travel_mode": "Multimodal",
        "dynamic_segments": [{"mode": "metro"}]
    }
    c_suburban = CandidateRoute(route_identifier="c_suburban", distance=10000, duration=2000, recommendation_status="AVAILABLE")
    c_suburban.route_metadata = {
        "travel_mode": "Multimodal",
        "dynamic_segments": [{"mode": "suburban"}]
    }
    
    assert _get_mode_category(c_bus) == "bus"
    assert _get_mode_category(c_metro) == "metro"
    assert _get_mode_category(c_suburban) == "suburban"
    
    # Deduplication must not collapse these distinct transit modes
    routes = [c_bus, c_metro, c_suburban]
    deduped = deduplicate_routes(routes)
    assert len(deduped) == 3
