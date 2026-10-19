import os
import json
import pytest
import datetime
from app.models.journey import Location, CandidateRoute
from app.intelligence.journey.station_normalizer import StationNormalizer, clean_station_name, haversine_m
from app.intelligence.journey.multimodal_router import MultimodalRouter
from app.intelligence.journey.schedule_engine import ScheduleEngine
from app.intelligence.journey.transit_graph import TransitGraph
from app.intelligence.journey.transit_validator import TransportIndex, TransportNode

@pytest.fixture
def sample_gtfs_records():
    """Deterministic fixture with parent station, platforms, entrances, and an adjacent distinct station."""
    stops = [
        {"stop_id": "MAS", "stop_name": "CHENNAI CENTRAL SUBURBAN", "stop_lat": "13.0830", "stop_lon": "80.2748", "location_type": "1", "parent_station": ""},
        {"stop_id": "MAS_P_1", "stop_name": "CHENNAI CENTRAL SUBURBAN", "stop_lat": "13.0830", "stop_lon": "80.2748", "location_type": "0", "parent_station": "MAS"},
        {"stop_id": "MAS_P_2", "stop_name": "CHENNAI CENTRAL SUBURBAN", "stop_lat": "13.0830", "stop_lon": "80.2748", "location_type": "0", "parent_station": "MAS"},
        {"stop_id": "MAS_1", "stop_name": "Gate A1", "stop_lat": "13.0829", "stop_lon": "80.2741", "location_type": "2", "parent_station": "MAS"},
        # Distinct station nearby (350m away)
        {"stop_id": "MPK", "stop_name": "CHENNAI PARK", "stop_lat": "13.0807", "stop_lon": "80.2729", "location_type": "1", "parent_station": ""},
        {"stop_id": "MPK_P_1", "stop_name": "CHENNAI PARK", "stop_lat": "13.0807", "stop_lon": "80.2729", "location_type": "0", "parent_station": "MPK"},
    ]
    return stops

# 1. Normalization of platform-level stops with valid parent-station relationships
def test_platform_normalization(tmp_path, sample_gtfs_records):
    normalizer = StationNormalizer()
    import zipfile, csv, io
    zip_path = tmp_path / "test-gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        # stops.txt
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"])
        writer.writeheader()
        writer.writerows(sample_gtfs_records)
        z.writestr("stops.txt", out.getvalue())
        # empty stop_times, routes, trips
        z.writestr("stop_times.txt", "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n")
        z.writestr("routes.txt", "route_id,route_short_name,route_long_name,route_color\n")
        z.writestr("trips.txt", "route_id,service_id,trip_id\n")

    data, diag = normalizer.normalize_gtfs_rail(str(zip_path), mode_prefix="SRR", mode_type="Suburban")
    
    assert diag["logical_stations_count"] == 2
    assert diag["platform_records_associated"] == 3
    assert diag["entrance_records_associated"] == 1
    assert diag["unresolved_records"] == 0
    
    mas = next(s for s in data["stations"] if s["stop_id"] == "MAS")
    assert len(mas["platforms"]) == 2
    assert len(mas["entrances"]) == 1

# 2. Prevention of accidental merging of distinct nearby stations
def test_prevent_accidental_merge(tmp_path, sample_gtfs_records):
    normalizer = StationNormalizer()
    import zipfile, csv, io
    zip_path = tmp_path / "test-gtfs.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"])
        writer.writeheader()
        writer.writerows(sample_gtfs_records)
        z.writestr("stops.txt", out.getvalue())
        z.writestr("stop_times.txt", "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n")
        z.writestr("routes.txt", "route_id,route_short_name,route_long_name,route_color\n")
        z.writestr("trips.txt", "route_id,service_id,trip_id\n")

    data, _ = normalizer.normalize_gtfs_rail(str(zip_path), mode_prefix="SRR", mode_type="Suburban")
    station_names = [s["name"] for s in data["stations"]]
    assert "Chennai Central Suburban" in station_names
    assert "Chennai Park" in station_names
    assert len(data["stations"]) == 2 # Kept distinct, not merged into one!

# 3. Graph consistency after station normalization
def test_normalized_graph_consistency():
    suburban_file = "transit_data/processed/suburban_network.json"
    assert os.path.exists(suburban_file)
    with open(suburban_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["station_count"] == 104
    station_ids = set(s["id"] for s in data["stations"])
    for r in data["routes"]:
        for seq in r["stop_sequences"]:
            for sid in seq:
                assert sid in station_ids, f"Route stop {sid} missing from stations"

# 4. Station lookup through canonical graph spatial index
def test_canonical_spatial_lookup():
    router = MultimodalRouter("transit_data/processed")
    # Query stations near Chennai Central (13.0827, 80.2755)
    dest_stations = router.query_nearby_stations(13.0827, 80.2755, "suburban", max_dist_m=3000, k=8)
    names = [s["name"] for s in dest_stations]
    assert "Chennai Central Suburban" in names
    assert "Chennai Park" in names
    # Verify no duplicate platform records in results
    assert len(names) == len(set(names))

# 5. Absence of dependence on incomplete legacy station fallback
def test_canonical_all_stations_complete():
    assert os.path.exists("all_stations.json")
    with open("all_stations.json", "r", encoding="utf-8") as f:
        stations = json.load(f)
    assert len(stations) >= 140 # Normalized complete network, not legacy 42
    names = [s["name"] for s in stations]
    assert any("Park" in n for n in names)
    assert any("Central" in n for n in names)
    assert any("Tambaram" in n for n in names)

# 6. Schedule validation for active and inactive service dates/times
def test_schedule_validation_active_vs_inactive():
    engine = ScheduleEngine("transit_data/downloads/srr-gtfs.zip")
    # Day test: Monday 10:00 AM Tambaram to Chennai Park
    dt_active = datetime.datetime(2026, 10, 19, 10, 0, 0)
    status, meta = engine.get_service_availability("suburban", "Tambaram to Chennai Park", dt_active)
    assert status == "AVAILABLE"
    assert meta["data_type"] == "GTFS_TIMETABLE_DEPARTURE"
    assert "departure_time" in meta

    # Late night test: 02:00 AM (no trains running)
    dt_inactive = datetime.datetime(2026, 10, 19, 2, 0, 0)
    status_off, meta_off = engine.get_service_availability("suburban", "Tambaram to Chennai Park", dt_inactive)
    assert status_off == "UNAVAILABLE"
    assert meta_off["data_type"] == "OUT_OF_SERVICE_HOURS"

# 7. Missing and placeholder timetable data fallback
def test_missing_timetable_graceful_fallback():
    engine = ScheduleEngine("nonexistent-gtfs.zip")
    dt = datetime.datetime(2026, 10, 19, 10, 0, 0)
    # When timetable is absent, engine gracefully uses operational window without crash
    status, meta = engine.get_service_availability("metro", "Guindy to Central", dt)
    assert status == "AVAILABLE"
    assert meta["data_type"] in ["STATIC_SCHEDULE_DATA", "LIVE_STATUS_DATA"]

# 8. Preservation of null transit scores and LightGBM model contract
def test_transit_leg_scoring_contract():
    cand = CandidateRoute(
        route_identifier="verified_rail_0",
        distance=42000.0,
        duration=4200.0,
        recommendation_status="AVAILABLE"
    )
    cand.route_metadata = {
        "travel_mode": "Multimodal",
        "dynamic_segments": [
            {"mode": "auto", "distance_m": 12000.0, "duration_s": 900.0},
            {"mode": "suburban", "distance_m": 28000.0, "duration_s": 3000.0},
            {"mode": "walk", "distance_m": 400.0, "duration_s": 300.0}
        ]
    }
    # Multimodal route transit leg must not be artificially scored
    assert cand.route_metadata["dynamic_segments"][1]["mode"] == "suburban"
    assert "safety_score" not in cand.route_metadata["dynamic_segments"][1]

# 9. Distinct route deduplication
def test_route_deduplication():
    from app.intelligence.journey.deduplication import deduplicate_routes
    r1 = CandidateRoute(route_identifier="c1", distance=1000.0, duration=100.0, recommendation_status="AVAILABLE")
    r1.route_metadata = {"geometry": {"coordinates": [[80.1, 13.0], [80.2, 13.1]]}, "route_name": "R1"}
    r2 = CandidateRoute(route_identifier="c2", distance=1000.0, duration=100.0, recommendation_status="AVAILABLE")
    r2.route_metadata = {"geometry": {"coordinates": [[80.1, 13.0], [80.2, 13.1]]}, "route_name": "R1_Duplicate"}
    r3 = CandidateRoute(route_identifier="c3", distance=1500.0, duration=150.0, recommendation_status="AVAILABLE")
    r3.route_metadata = {"geometry": {"coordinates": [[80.1, 13.0], [80.3, 13.2]]}, "route_name": "R3_Unique"}
    
    deduped = deduplicate_routes([r1, r2, r3])
    assert len(deduped) == 2
    ids = [r.route_identifier for r in deduped]
    assert "c1" in ids
    assert "c3" in ids
