"""
Test suite for Phase 51.97: Spatial Matcher Corridor Index Optimization and Latency Safeguards.
Verifies that:
1. _is_coords_covered accurately detects when candidate coordinates fall within indexed bounds.
2. When coordinates are already covered, redundant corridor queries and index rebuilds are avoided.
3. When coordinates fall outside, _ensure_index_for_corridor is triggered to expand coverage.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.intelligence.journey.spatial_matcher import SpatialMatchingService



def test_is_coords_covered_evaluation():
    """Verify _is_coords_covered handles initialized and uninitialized states."""
    matcher = SpatialMatchingService(auto_build_index=False)

    # 1. Uninitialized index returns False
    coords = [[80.25, 13.05], [80.26, 13.06]]
    assert matcher._is_coords_covered(coords) is False

    # 2. Set mock index and bounds: bounds = (min_lon, min_lat, max_lon, max_lat)
    matcher._index = MagicMock()
    matcher._segment_records = [MagicMock()]
    matcher._indexed_bounds = (80.20, 13.00, 80.30, 13.10)

    # Fully inside: returns True
    inside_coords = [[80.22, 13.02], [80.28, 13.08]]
    assert matcher._is_coords_covered(inside_coords) is True

    # Partially/fully outside: returns False
    outside_coords = [[80.15, 13.02], [80.28, 13.08]] # min_lon 80.15 < 80.20
    assert matcher._is_coords_covered(outside_coords) is False

    outside_lat = [[80.22, 12.95], [80.28, 13.08]] # min_lat 12.95 < 13.00
    assert matcher._is_coords_covered(outside_lat) is False


def test_match_route_skips_ensure_index_when_covered():
    """Verify match_route skips _ensure_index_for_corridor when coords are already covered."""
    matcher = SpatialMatchingService(auto_build_index=False)
    matcher._index = MagicMock()
    matcher._segment_records = [MagicMock()]
    matcher._indexed_bounds = (80.20, 13.00, 80.30, 13.10)

    with patch.object(matcher, "_ensure_index_for_corridor") as mock_ensure:
        with patch.object(matcher, "normalize_route_geometry", side_effect=ValueError("test_halt")):
            route_input = {"coordinates": [[80.22, 13.02], [80.28, 13.08]]}
            matcher.match_route(route_input)
            mock_ensure.assert_not_called()


def test_match_route_calls_ensure_index_when_not_covered():
    """Verify match_route invokes _ensure_index_for_corridor when coords extend outside."""
    matcher = SpatialMatchingService(auto_build_index=False)
    matcher._index = MagicMock()
    matcher._segment_records = [MagicMock()]
    matcher._indexed_bounds = (80.20, 13.00, 80.30, 13.10)

    with patch.object(matcher, "_ensure_index_for_corridor") as mock_ensure:
        with patch.object(matcher, "normalize_route_geometry", side_effect=ValueError("test_halt")):
            route_input = {"coordinates": [[80.15, 13.02], [80.28, 13.08]]}
            matcher.match_route(route_input)
            mock_ensure.assert_called_once()

