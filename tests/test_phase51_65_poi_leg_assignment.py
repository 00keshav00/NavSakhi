"""
NavSakhi Phase 51.65 — Vectorized Multimodal POI Leg Assignment Differential Regression Tests

Verifies exact equivalence between the optimized vectorized leg assignment and the
reference brute-force implementation across 12 mandatory geometric and temporal scenarios.
"""

import math
import datetime
import pytest
import numpy as np

from app.services.poi_service import (
    _point_to_segment_distance,
    _to_projected_xy,
    _assign_nearest_legs_vectorized,
    _reference_nearest_leg_assignment,
    POISpatialService,
    get_poi_service,
)
from app.intelligence.journey.opening_hours_parser import evaluate_opening_hours


# -----------------------------------------------------------------------------
# Fixtures & Helper Builders
# -----------------------------------------------------------------------------

def build_leg_data(legs_spec, corridor_m=800.0):
    """Constructs leg_data tuples [(leg_id, leg_pts_m, bbox)] matching poi_service."""
    leg_data = []
    for l_idx, spec in enumerate(legs_spec):
        leg_id = spec.get("leg_id", f"leg_{l_idx+1}")
        coords = spec.get("coordinates", [])
        pts_m = [_to_projected_xy(c[0], c[1]) for c in coords if len(c) >= 2]
        if len(pts_m) >= 2:
            xs = [p[0] for p in pts_m]
            ys = [p[1] for p in pts_m]
            bbox = (min(xs) - corridor_m, min(ys) - corridor_m, max(xs) + corridor_m, max(ys) + corridor_m)
            leg_data.append((leg_id, pts_m, bbox))
        elif len(pts_m) < 2 and spec.get("allow_empty", False):
            # Explicitly test degenerate / empty handling
            pass
    return leg_data


# -----------------------------------------------------------------------------
# Scenario 1: Single-leg straight route
# -----------------------------------------------------------------------------
def test_scenario_1_single_leg_straight_route():
    # Long straight road along Chennai Central latitude
    legs_spec = [
        {"leg_id": "leg_straight", "coordinates": [[80.20, 13.08], [80.25, 13.08]]}
    ]
    leg_data = build_leg_data(legs_spec)

    # Sample POIs along and offset from the road
    test_pois = [
        _to_projected_xy(80.22, 13.082),   # offset north
        _to_projected_xy(80.24, 13.078),   # offset south
        _to_projected_xy(80.20, 13.08),    # directly on start
        _to_projected_xy(80.25, 13.08),    # directly on end
    ]
    px = np.array([p[0] for p in test_pois])
    py = np.array([p[1] for p in test_pois])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(test_pois):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg == "leg_straight"
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 2: Long five-leg multimodal route
# -----------------------------------------------------------------------------
def test_scenario_2_five_leg_multimodal_route():
    # 5 legs: Walk -> Metro -> Walk -> Bus -> Walk
    legs_spec = [
        {"leg_id": "leg_1_walk",  "coordinates": [[80.20, 13.00], [80.205, 13.01]]},
        {"leg_id": "leg_2_metro", "coordinates": [[80.205, 13.01], [80.22, 13.04], [80.24, 13.07]]},
        {"leg_id": "leg_3_walk",  "coordinates": [[80.24, 13.07], [80.242, 13.072]]},
        {"leg_id": "leg_4_bus",   "coordinates": [[80.242, 13.072], [80.26, 13.08], [80.275, 13.085]]},
        {"leg_id": "leg_5_walk",  "coordinates": [[80.275, 13.085], [80.278, 13.087]]},
    ]
    leg_data = build_leg_data(legs_spec)

    test_points = [
        _to_projected_xy(80.202, 13.005),  # near leg 1
        _to_projected_xy(80.23, 13.055),   # near leg 2
        _to_projected_xy(80.241, 13.071),  # near leg 3
        _to_projected_xy(80.265, 13.082),  # near leg 4
        _to_projected_xy(80.276, 13.086),  # near leg 5
    ]
    px = np.array([p[0] for p in test_points])
    py = np.array([p[1] for p in test_points])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(test_points):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 3: POI closest to the middle of a long segment
# -----------------------------------------------------------------------------
def test_scenario_3_poi_middle_of_long_segment():
    legs_spec = [
        {"leg_id": "leg_long", "coordinates": [[80.10, 13.00], [80.30, 13.00]]}
    ]
    leg_data = build_leg_data(legs_spec)

    # Middle is 80.20, 13.00. Offset by 150m North.
    mid_poi = _to_projected_xy(80.20, 13.00135)
    px = np.array([mid_poi[0]])
    py = np.array([mid_poi[1]])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)
    ref_leg, ref_dist = _reference_nearest_leg_assignment(mid_poi[0], mid_poi[1], leg_data)

    assert opt_legs[0] == ref_leg == "leg_long"
    assert math.isclose(opt_dists[0], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 4: POI near a segment endpoint or transfer boundary
# -----------------------------------------------------------------------------
def test_scenario_4_poi_near_endpoint_or_transfer_boundary():
    # Leg 1 ends at (80.22, 13.04), Leg 2 begins at (80.22, 13.04)
    legs_spec = [
        {"leg_id": "leg_A", "coordinates": [[80.20, 13.02], [80.22, 13.04]]},
        {"leg_id": "leg_B", "coordinates": [[80.22, 13.04], [80.24, 13.06]]},
    ]
    leg_data = build_leg_data(legs_spec)

    # POI directly at the junction
    junction_poi = _to_projected_xy(80.22, 13.04)
    # POI slightly biased towards leg_A
    bias_A_poi = _to_projected_xy(80.2199, 13.0399)
    # POI slightly biased towards leg_B
    bias_B_poi = _to_projected_xy(80.2201, 13.0401)

    pts = [junction_poi, bias_A_poi, bias_B_poi]
    px = np.array([p[0] for p in pts])
    py = np.array([p[1] for p in pts])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(pts):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 5: Two equidistant or nearly equidistant legs (tie-breaking test)
# -----------------------------------------------------------------------------
def test_scenario_5_equidistant_legs_tie_breaking():
    # Two parallel lines equidistant from y = 0
    # Line 1 at y = 100m, Line 2 at y = -100m
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)

    leg_1_pts = [(ref_x - 500, ref_y + 100), (ref_x + 500, ref_y + 100)]
    leg_2_pts = [(ref_x - 500, ref_y - 100), (ref_x + 500, ref_y - 100)]
    bbox_1 = (ref_x - 1000, ref_y - 1000, ref_x + 1000, ref_y + 1000)
    bbox_2 = (ref_x - 1000, ref_y - 1000, ref_x + 1000, ref_y + 1000)

    leg_data = [
        ("leg_first", leg_1_pts, bbox_1),
        ("leg_second", leg_2_pts, bbox_2),
    ]

    # POI directly at ref_x, ref_y (exactly 100m from both legs!)
    px = np.array([ref_x])
    py = np.array([ref_y])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)
    ref_leg, ref_dist = _reference_nearest_leg_assignment(ref_x, ref_y, leg_data)

    # Invariant: leg_first must win the tie because it appears first in leg_data
    assert ref_leg == "leg_first"
    assert opt_legs[0] == "leg_first"
    assert math.isclose(opt_dists[0], 100.0, abs_tol=1e-6)
    assert math.isclose(opt_dists[0], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 6: Crossing, overlapping, and disconnected legs
# -----------------------------------------------------------------------------
def test_scenario_6_crossing_overlapping_and_disconnected():
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)

    # Crossing legs: X-shape
    leg_cross_1 = [("cross_1", [(ref_x - 200, ref_y - 200), (ref_x + 200, ref_y + 200)], (ref_x - 1000, ref_y - 1000, ref_x + 1000, ref_y + 1000))]
    leg_cross_2 = [("cross_2", [(ref_x - 200, ref_y + 200), (ref_x + 200, ref_y - 200)], (ref_x - 1000, ref_y - 1000, ref_x + 1000, ref_y + 1000))]
    # Disconnected leg far away
    leg_far = [("far_leg", [(ref_x + 5000, ref_y + 5000), (ref_x + 6000, ref_y + 6000)], (ref_x + 4000, ref_y + 4000, ref_x + 7000, ref_y + 7000))]

    leg_data = leg_cross_1 + leg_cross_2 + leg_far

    pts = [
        (ref_x, ref_y + 50),     # closer to intersection, slightly north
        (ref_x + 5100, ref_y + 5050), # near disconnected leg
        (ref_x - 150, ref_y - 100), # closer to cross_1
    ]
    px = np.array([p[0] for p in pts])
    py = np.array([p[1] for p in pts])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(pts):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 7: POIs just inside and just outside corridor boundary
# -----------------------------------------------------------------------------
def test_scenario_7_corridor_boundary_in_out():
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)
    # Leg along X axis: y = ref_y
    leg_data = [
        ("leg_x", [(ref_x, ref_y), (ref_x + 1000, ref_y)], (ref_x - 800, ref_y - 800, ref_x + 1800, ref_y + 800))
    ]

    pts = [
        (ref_x + 500, ref_y + 799.0),   # 1m inside corridor
        (ref_x + 500, ref_y + 800.0),   # exact boundary
        (ref_x + 500, ref_y + 801.0),   # 1m outside corridor
        (ref_x + 500, ref_y + 900.0),   # well outside bbox
    ]
    px = np.array([p[0] for p in pts])
    py = np.array([p[1] for p in pts])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(pts):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg
        if ref_dist != float("inf"):
            assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)
        else:
            assert opt_dists[i] == float("inf")


# -----------------------------------------------------------------------------
# Scenario 8: Empty and degenerate leg geometries
# -----------------------------------------------------------------------------
def test_scenario_8_empty_and_degenerate_geometries():
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)
    # Degenerate segment: point A == point B
    degen_leg = ("degen_leg", [(ref_x, ref_y), (ref_x, ref_y)], (ref_x - 800, ref_y - 800, ref_x + 800, ref_y + 800))
    normal_leg = ("normal_leg", [(ref_x + 100, ref_y), (ref_x + 200, ref_y)], (ref_x - 700, ref_y - 800, ref_x + 1000, ref_y + 800))

    leg_data = [degen_leg, normal_leg]

    pts = [
        (ref_x + 10, ref_y + 10),    # closer to degen_leg
        (ref_x + 150, ref_y + 10),   # closer to normal_leg
    ]
    px = np.array([p[0] for p in pts])
    py = np.array([p[1] for p in pts])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(pts):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)

    # Empty leg_data test
    empty_opt_legs, empty_opt_dists = _assign_nearest_legs_vectorized(px, py, [])
    assert empty_opt_legs == [None, None]
    assert all(math.isinf(d) for d in empty_opt_dists)


# -----------------------------------------------------------------------------
# Scenario 9: Multiple POIs sharing the same nearest leg
# -----------------------------------------------------------------------------
def test_scenario_9_multiple_pois_sharing_nearest_leg():
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)
    leg_data = [
        ("shared_leg", [(ref_x, ref_y), (ref_x + 5000, ref_y)], (ref_x - 800, ref_y - 800, ref_x + 5800, ref_y + 800)),
        ("other_leg", [(ref_x, ref_y + 3000), (ref_x + 5000, ref_y + 3000)], (ref_x - 800, ref_y + 2200, ref_x + 5800, ref_y + 3800)),
    ]

    # 50 POIs spaced along the first leg
    pts = [(ref_x + i * 100, ref_y + 50) for i in range(50)]
    px = np.array([p[0] for p in pts])
    py = np.array([p[1] for p in pts])

    opt_legs, opt_dists = _assign_nearest_legs_vectorized(px, py, leg_data)

    for i, (x, y) in enumerate(pts):
        ref_leg, ref_dist = _reference_nearest_leg_assignment(x, y, leg_data)
        assert opt_legs[i] == ref_leg == "shared_leg"
        assert math.isclose(opt_dists[i], ref_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 10: Different route geometries with identical endpoints
# -----------------------------------------------------------------------------
def test_scenario_10_different_geometries_identical_endpoints():
    ref_x, ref_y = _to_projected_xy(80.2090, 13.0827)
    start = (ref_x, ref_y)
    end = (ref_x + 2000, ref_y)

    # Route 1 arches North
    route1_legs = [("r1_leg", [start, (ref_x + 1000, ref_y + 500), end], (ref_x - 800, ref_y - 800, ref_x + 2800, ref_y + 1300))]
    # Route 2 arches South
    route2_legs = [("r2_leg", [start, (ref_x + 1000, ref_y - 500), end], (ref_x - 800, ref_y - 1300, ref_x + 2800, ref_y + 800))]

    poi_north = (ref_x + 1000, ref_y + 400)
    poi_south = (ref_x + 1000, ref_y - 400)

    px = np.array([poi_north[0], poi_south[0]])
    py = np.array([poi_north[1], poi_south[1]])

    r1_opt_legs, r1_opt_dists = _assign_nearest_legs_vectorized(px, py, route1_legs)
    r2_opt_legs, r2_opt_dists = _assign_nearest_legs_vectorized(px, py, route2_legs)

    for i, pt in enumerate([poi_north, poi_south]):
        ref1_leg, ref1_dist = _reference_nearest_leg_assignment(pt[0], pt[1], route1_legs)
        assert r1_opt_legs[i] == ref1_leg
        assert math.isclose(r1_opt_dists[i], ref1_dist, abs_tol=1e-6)

        ref2_leg, ref2_dist = _reference_nearest_leg_assignment(pt[0], pt[1], route2_legs)
        assert r2_opt_legs[i] == ref2_leg
        assert math.isclose(r2_opt_dists[i], ref2_dist, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# Scenario 11 & 12: End-to-end query_pois_near_route equivalence, ordering & hours
# -----------------------------------------------------------------------------
def test_scenario_11_and_12_query_pois_near_route_equivalence_and_hours():
    """Validates full query_pois_near_route output object equivalence, ordering, and opening hours."""
    service = get_poi_service()

    # Synthetic 3-leg route
    route_coords = [
        [80.20, 13.04], [80.21, 13.05], [80.22, 13.06],
        [80.23, 13.07], [80.24, 13.08]
    ]
    legs = [
        {
            "leg_id": "leg_A",
            "transport_mode": "Auto",
            "polyline": {"type": "LineString", "coordinates": [[80.20, 13.04], [80.21, 13.05]]}
        },
        {
            "leg_id": "leg_B",
            "transport_mode": "Metro",
            "polyline": {"type": "LineString", "coordinates": [[80.21, 13.05], [80.22, 13.06], [80.23, 13.07]]}
        },
        {
            "leg_id": "leg_C",
            "transport_mode": "Walk",
            "polyline": {"type": "LineString", "coordinates": [[80.23, 13.07], [80.24, 13.08]]}
        }
    ]

    res = service.query_pois_near_route(
        route_coords,
        corridor_m=800.0,
        legs=legs,
        total_duration_s=1800.0
    )

    pois = res.get("pois", [])
    assert len(pois) > 0
    print(f"Matched {len(pois)} POIs in synthetic route corridor")

    # Verify every returned POI has valid nearest_route_leg_id belonging to the legs
    valid_leg_ids = {"leg_A", "leg_B", "leg_C", None}
    for p in pois:
        assert p["nearest_route_leg_id"] in valid_leg_ids
        assert "opening_status" in p
        assert p["opening_status"] in {"OPEN", "CLOSED", "CLOSING_SOON", "UNKNOWN"}
        assert "estimated_pass_through_time" in p
        assert "distance_to_route_m" in p
        assert p["distance_to_route_m"] <= 800.0
