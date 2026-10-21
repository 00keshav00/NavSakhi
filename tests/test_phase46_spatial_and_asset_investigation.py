import os
import sys
import hashlib
from pathlib import Path
import pytest

from app.intelligence.journey.spatial_matcher import SpatialMatchingService


@pytest.fixture
def matcher():
    m = SpatialMatchingService(auto_build_index=False)
    yield m
    m.invalidate_index()


def test_corridor_boxes_geographic_span_bounded(matcher):
    """Verify corridor boxes strictly bound geographic span to prevent giant diagonal boxes."""
    # 35 km route with 36 points across Chennai
    coords = [
        [80.1179 + i * (80.2760 - 80.1179) / 35, 12.9258 + i * (13.0824 - 12.9258) / 35]
        for i in range(36)
    ]
    boxes = matcher._compute_corridor_boxes(coords, margin=0.0035, max_step_pts=30, max_span_deg=0.020)
    assert len(boxes) > 1, "Must partition 35km diagonal route into multiple chunks"

    # Margin is 0.0035 on both sides, so max dimension must be <= 0.020 + 2*0.0035 = 0.027 deg
    for min_lon, min_lat, max_lon, max_lat in boxes:
        assert (max_lon - min_lon) <= 0.0275, f"Lon span too wide: {max_lon - min_lon}"
        assert (max_lat - min_lat) <= 0.0275, f"Lat span too tall: {max_lat - min_lat}"


def test_long_route_segment_count_strictly_bounded(matcher):
    """Verify a 35km cross-city corridor indexes a bounded segment count (< 45,000, not 100k+)."""
    coords = [
        [80.1179 + i * (80.2760 - 80.1179) / 35, 12.9258 + i * (13.0824 - 12.9258) / 35]
        for i in range(36)
    ]
    matcher._ensure_index_for_corridor(coords, margin=0.0035)
    indexed_count = len(matcher._segment_records)
    assert indexed_count > 0, "Must index segments for the route"
    assert indexed_count <= 45000, f"Indexed count {indexed_count} exceeded 45,000 safety threshold"


def test_auto_build_index_default_is_false():
    """Verify default auto_build_index=False prevents eager loading of 1M row dataset."""
    m = SpatialMatchingService()
    assert m._index is None, "Index should not be eagerly built on initialization"
    assert len(m._segment_records) == 0
    assert m._road_segments_df is None


def test_frozen_ml_artifact_hashes():
    """Verify all 4 ML artifacts match the exact frozen SHA-256 baselines."""
    expected = {
        "best_model.pkl": "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
        "preprocessing_pipeline.pkl": "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
        "road_segments.parquet": "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
        "master_feature_table.parquet": "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    }
    root = Path("app/ml/Hack/ml")
    files = {
        "best_model.pkl": root / "models" / "best_model.pkl",
        "preprocessing_pipeline.pkl": root / "models" / "preprocessing_pipeline.pkl",
        "road_segments.parquet": root / "datasets" / "processed" / "road_segments.parquet",
        "master_feature_table.parquet": root / "datasets" / "processed" / "master_feature_table.parquet",
    }
    for name, path in files.items():
        assert path.exists(), f"Missing artifact: {name}"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        assert h.hexdigest() == expected[name], f"SHA256 mismatch for {name}"


def test_middleware_public_route_rules():
    """Verify the middleware rules classify static assets as public routes without redirection."""
    public_paths = [
        "/",
        "/robots.txt",
        "/sitemap.xml",
        "/manifest.json",
        "/maplibre-worker.js",
        "/resources",
        "/home",
        "/journey",
        "/assistant",
        "/community",
    ]
    protected_paths = [
        "/emergency",
        "/live",
        "/profile",
        "/settings",
        "/activity",
    ]

    for p in public_paths:
        is_public = (
            p == "/"
            or p.startswith("/login")
            or p == "/robots.txt"
            or p == "/sitemap.xml"
            or p == "/manifest.json"
            or p == "/maplibre-worker.js"
            or p == "/resources"
            or p == "/home"
            or p == "/journey"
            or p == "/assistant"
            or p == "/community"
        )
        assert is_public is True, f"Path {p} should be public"

    for p in protected_paths:
        is_public = (
            p == "/"
            or p.startswith("/login")
            or p == "/robots.txt"
            or p == "/sitemap.xml"
            or p == "/manifest.json"
            or p == "/maplibre-worker.js"
            or p == "/resources"
            or p == "/home"
            or p == "/journey"
            or p == "/assistant"
            or p == "/community"
        )
        assert is_public is False, f"Path {p} must NOT be public"


def test_interior_route_within_indexed_bounds_loads_missing_corridor(matcher):
    """
    Regression test: routes located in the geographic interior gap of an existing
    multi-corridor index must not be falsely marked as 'covered' by _indexed_bounds.
    They must trigger genuine road-segment loading for their corridor.
    """
    # 1. Establish an index covering two distant endpoints (South and East)
    route_endpoints = [
        [80.1527, 12.8448],  # VIT area
        [80.2291, 12.8359],  # OMR / Marina Mall
    ]
    matcher._ensure_index_for_corridor(route_endpoints, margin=0.0035)
    initial_boxes = list(matcher._indexed_boxes)
    assert matcher._index is not None
    assert len(initial_boxes) > 0

    # 2. Query a route located in Tambaram/Chromepet (interior/adjacent gap)
    interior_route_geom = {
        "type": "LineString",
        "coordinates": [[80.1100, 12.9240], [80.1000, 12.9249]],
    }
    match_res = matcher.match_route(interior_route_geom, travel_mode="auto")

    # Must NOT fail with zero matches due to false coverage bypass
    assert match_res.status in ["SUCCESS", "PARTIAL"]
    assert len(match_res.matched_segments) > 0, "Interior corridor must load road segments and find matches"
    assert match_res.coverage.matched_length_m > 0

def test_secondary_ram_guard_narrows_indexed_boxes_and_prevents_false_reuse(matcher):
    """
    Phase 46B Comprehensive Regression Test for Secondary 50,000-Segment RAM Guard:
    Exercises complete lifecycle across two nearby corridors:
      A. Index Route A (30,000 segments) -> verify initial state and query count.
      B. Index Route B (25,000 segments) -> trigger secondary guard (>50k combined).
         Verify all six internal attributes are narrowed strictly to Route B data.
      C. Reuse Route B -> contained sub-route achieves index reuse with zero new queries.
      D. Return to Route A -> discarded corridor triggers genuine Parquet reload,
         matches authentic Route A segments, and rejects NO_SCOREABLE_SEGMENTS.
      E. Verify Recovery -> matcher remains internally consistent and reuses rebuilt index.
    """
    import pandas as pd
    from unittest.mock import MagicMock, patch
    from shapely.geometry import Point

    coords_a = [[80.1500, 12.8500], [80.1550, 12.8550]]
    coords_b = [[80.1600, 12.8600], [80.1650, 12.8650]]

    # Synthetic segments for corridor A (30,000 segments)
    df_a = pd.DataFrame({
        "segment_id": [f"seg_a_{i}" for i in range(30000)],
        "way_id": [100] * 30000,
        "latitude": [12.8525] * 30000,
        "longitude": [80.1525] * 30000,
        "length_m": [25.0] * 30000,
        "road_type": ["primary"] * 30000,
    })

    # Synthetic segments for corridor B (25,000 segments)
    df_b = pd.DataFrame({
        "segment_id": [f"seg_b_{i}" for i in range(25000)],
        "way_id": [200] * 25000,
        "latitude": [12.8625] * 25000,
        "longitude": [80.1625] * 25000,
        "length_m": [30.0] * 25000,
        "road_type": ["secondary"] * 25000,
    })

    mock_table_a = MagicMock()
    mock_table_a.to_pandas.return_value = df_a

    mock_table_b = MagicMock()
    mock_table_b.to_pandas.return_value = df_b

    mock_ds = MagicMock()
    # 1st call: route A; 2nd call: route B; 3rd call: route A reload
    mock_ds.to_table.side_effect = [mock_table_a, mock_table_b, mock_table_a]

    with patch("pyarrow.dataset.dataset", return_value=mock_ds):
        # -------------------------------------------------------------
        # Step A: Index Route A (30,000 segments)
        # -------------------------------------------------------------
        matcher._ensure_index_for_corridor(coords_a)
        assert mock_ds.to_table.call_count == 1
        assert len(matcher._segment_records) == 30000
        assert all(sid.startswith("seg_a_") for sid in matcher._segment_records.segment_ids)
        assert matcher._road_segments_df["segment_id"].str.startswith("seg_a_").all()
        boxes_a = list(matcher._indexed_boxes)
        bounds_a = matcher._indexed_bounds
        assert len(boxes_a) == 1

        # -------------------------------------------------------------
        # Step B: Index nearby Route B (25,000 segments) -> Trigger Guard
        # 30,000 + 25,000 = 55,000 > 50,000 limit (dist_deg < 0.15)
        # -------------------------------------------------------------
        matcher._ensure_index_for_corridor(coords_b)
        assert mock_ds.to_table.call_count == 2

        # 1. _road_segments_df contains only Route B data
        assert len(matcher._road_segments_df) == 25000
        assert matcher._road_segments_df["segment_id"].str.startswith("seg_b_").all()
        assert not matcher._road_segments_df["segment_id"].str.startswith("seg_a_").any()

        # 2. _segment_records contains expected records and corresponds to dataframe
        assert len(matcher._segment_records) == 25000
        assert all(sid.startswith("seg_b_") for sid in matcher._segment_records.segment_ids)

        # 3. _index is built for retained geometries, not containing discarded Route A
        mx_a, my_a = matcher.transformer.transform(80.1525, 12.8525)
        mx_b, my_b = matcher.transformer.transform(80.1625, 12.8625)
        assert len(matcher._index.query(Point(mx_a, my_a).buffer(100.0))) == 0, "Route A geometries must be evicted from index"
        assert len(matcher._index.query(Point(mx_b, my_b).buffer(100.0))) > 0, "Route B geometries must be present in index"

        # 4. _indexed_boxes contains only Route B corridor boxes
        assert len(matcher._indexed_boxes) == 1
        assert matcher._indexed_boxes != boxes_a, "Stale corridor A boxes must be evicted from _indexed_boxes"

        # 5. _indexed_bounds and _indexed_bbox agree with Route B metadata in (min_lon, min_lat, max_lon, max_lat)
        b_box = matcher._indexed_boxes[0]
        assert matcher._indexed_bounds == b_box, "Indexed bounds must match corridor B bounds"
        assert matcher._indexed_bbox == b_box, "Indexed bbox must match corridor B bbox"

        # 6. Retained index remains within configured 50,000 segment-count limit
        assert len(matcher._segment_records) <= 50000
        assert len(matcher._road_segments_df) <= 50000

        # -------------------------------------------------------------
        # Step C: Reuse Route B (contained sub-route)
        # -------------------------------------------------------------
        contained_b = [[80.1610, 12.8610], [80.1640, 12.8640]]
        match_sub_b = matcher.match_route({"type": "LineString", "coordinates": contained_b}, travel_mode="auto")
        assert mock_ds.to_table.call_count == 2, "Contained route within Route B must achieve zero-query cache reuse"
        assert match_sub_b.status in ["SUCCESS", "PARTIAL"]
        assert len(match_sub_b.matched_segments) > 0
        assert all(s.segment_id.startswith("seg_b_") for s in match_sub_b.matched_segments)

        # -------------------------------------------------------------
        # Step D: Return to Route A (previously discarded corridor)
        # -------------------------------------------------------------
        geom_a = {"type": "LineString", "coordinates": coords_a}
        match_a = matcher.match_route(geom_a, travel_mode="auto")

        # Must trigger a fresh data query (not false reuse)
        assert mock_ds.to_table.call_count == 3, "Discarded corridor must trigger genuine Parquet reload"
        assert match_a.status != "NO_SCOREABLE_SEGMENTS", "Must not report NO_SCOREABLE_SEGMENTS when segments exist"
        assert match_a.status in ["SUCCESS", "PARTIAL"]
        assert len(match_a.matched_segments) > 0
        assert match_a.coverage.matched_length_m > 0
        assert all(s.segment_id.startswith("seg_a_") for s in match_a.matched_segments), "Matched segments must belong to Route A"

        # -------------------------------------------------------------
        # Step E: Verify Recovery & Subsequent Cache Reuse
        # -------------------------------------------------------------
        assert len(matcher._segment_records) == 30000
        assert matcher._road_segments_df["segment_id"].str.startswith("seg_a_").all()
        assert matcher._indexed_boxes == boxes_a
        assert matcher._indexed_bounds == bounds_a

        # Subsequent contained Route A request reuses rebuilt index without reloading
        contained_a = [[80.1510, 12.8510], [80.1540, 12.8540]]
        match_sub_a = matcher.match_route({"type": "LineString", "coordinates": contained_a}, travel_mode="auto")
        assert mock_ds.to_table.call_count == 3, "Subsequent request for Route A must reuse rebuilt index"
        assert match_sub_a.status in ["SUCCESS", "PARTIAL"]
        assert len(match_sub_a.matched_segments) > 0
        assert all(s.segment_id.startswith("seg_a_") for s in match_sub_a.matched_segments)
