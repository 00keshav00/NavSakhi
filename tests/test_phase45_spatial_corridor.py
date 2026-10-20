"""
Phase 45 Unit & Regression Tests for Bounded Spatial Memory & Corridor Partitioning.
Covers:
1. Corridor partitioning on long cross-city routes
2. Disjoint bounding boxes and index invalidation
3. Bounded chunk sizes (no multi-degree giant diagonal boxes)
4. Score coverage and matched segment integrity
5. Repeated requests and cache reuse
"""

import pytest
from app.intelligence.journey.spatial_matcher import SpatialMatchingService


@pytest.fixture
def matcher():
    m = SpatialMatchingService()
    yield m
    m.invalidate_index()


def test_corridor_boxes_bounded_chunk_sizes(matcher):
    """Verify corridor boxes stay tightly bounded around route coords."""
    # Long diagonal path across Chennai (~20km)
    coords = [
        [80.1500 + i * 0.005, 12.8500 + i * 0.005]
        for i in range(30)
    ]
    boxes = matcher._compute_corridor_boxes(coords, margin=0.0035, max_step_pts=10)
    assert len(boxes) > 1, "Should partition long route into multiple boxes"

    # Each box must have bounded dimensions
    for min_lon, min_lat, max_lon, max_lat in boxes:
        assert max_lon - min_lon < 0.1, "Box width should be tightly bounded"
        assert max_lat - min_lat < 0.1, "Box height should be tightly bounded"


def test_repeated_requests_index_reuse(matcher):
    """Verify identical or overlapping route reuses existing spatial index without reindexing."""
    coords = [
        [80.2000, 13.0000],
        [80.2050, 13.0050],
        [80.2100, 13.0100],
    ]
    matcher._ensure_index_for_corridor(coords, margin=0.0035)
    initial_index = matcher._index
    initial_count = len(matcher._segment_records)
    assert initial_index is not None
    assert initial_count > 0

    # Same corridor request should reuse the active index
    matcher._ensure_index_for_corridor(coords, margin=0.0035)
    assert matcher._index is initial_index, "Active index must be reused for covered corridor"
    assert len(matcher._segment_records) == initial_count


def test_disjoint_bounding_boxes_invalidates_and_reindexes(matcher):
    """Verify geographically disjoint route invalidates distant index and re-indexes new region."""
    # Location A: Chennai South (Tambaram / OMR area)
    coords_a = [
        [80.1500, 12.8500],
        [80.1550, 12.8550],
    ]
    matcher._ensure_index_for_corridor(coords_a, margin=0.0035)
    records_a = len(matcher._segment_records)
    bounds_a = matcher._indexed_bounds
    assert records_a > 0

    # Location B: Chennai North (George Town / Central area ~20km away)
    coords_b = [
        [80.2800, 13.0800],
        [80.2850, 13.0850],
    ]
    matcher._ensure_index_for_corridor(coords_b, margin=0.0035)
    records_b = len(matcher._segment_records)
    bounds_b = matcher._indexed_bounds
    assert records_b > 0
    # Bounds must reflect location B, not location A
    assert bounds_b != bounds_a
    assert bounds_b[0] > 80.20, "Index must now cover location B"


def test_invalidate_index_releases_memory(matcher):
    """Verify invalidate_index resets all internal spatial structures."""
    coords = [
        [80.2100, 12.9800],
        [80.2150, 12.9850],
    ]
    matcher._ensure_index_for_corridor(coords, margin=0.0035)
    assert matcher._index is not None
    assert len(matcher._segment_records) > 0

    matcher.invalidate_index()
    assert matcher._index is None
    assert matcher._index_geoms is None
    assert len(matcher._segment_records) == 0
    assert matcher._indexed_bounds is None
    assert matcher._indexed_boxes == []


def test_long_cross_city_route_corridor_matching(matcher):
    """Verify matching across a realistic cross-city route returns valid matched segments."""
    route_geom = {
        "type": "LineString",
        "coordinates": [
            [80.2184, 12.9863],
            [80.2200, 12.9900],
            [80.2250, 13.0000],
            [80.2300, 13.0100],
            [80.2350, 13.0200],
            [80.2400, 13.0300],
        ]
    }
    match_result = matcher.match_route(route_geom)
    assert match_result is not None
    assert hasattr(match_result, "matched_segments")
    assert len(match_result.matched_segments) > 0, "Cross-city route must find matched segments"
    assert match_result.coverage.matched_length_m > 0
    assert 0.0 <= match_result.coverage.coverage_ratio <= 1.0
