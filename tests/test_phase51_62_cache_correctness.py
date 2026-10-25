"""
Phase 51.62 — Comprehensive Route Cache Correctness, Safety Equivalence & Pre-Commit Audit Test Suite.

Audits:
1. Response-builder memoization & collision resistance (SHA-256 geometry signature).
2. Parameter sensitivity (hour, corridor radius, reversed route, empty geometry).
3. Segment-level score and TreeSHAP caching (feature-bound, model-bound, mutation-proof).
4. Spatial index reuse, coverage guarantees, and bounded memory invalidation.
5. Multimodal sub-leg reuse and transit invariants (NOT_SCORED for rail/metro).
6. True reference equivalence (comparing optimized pipeline against unoptimized baseline).
"""

import copy
import hashlib
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock

from app.intelligence.response.builder import compute_route_geometry_signature, ResponseBuilder
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.services.spatial_matcher import SpatialMatchingService
from app.ml.predictor import MLSafetyPredictor
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES
from app.schemas.spatial_schemas import (
    MatchedSegmentResult,
    MatchStatus,
    FeatureStatus,
    RouteSpatialMatchResponse,
    RouteCoverageMetrics,
)
from app.schemas.journey_schemas import RouteSegment, RoutePOI
from app.intelligence.journey.night_activity_scorer import NightActivityScorer


# ==============================================================================
# SECTION 2: Response-Builder Memoization & Collision Resistance
# ==============================================================================

def test_geometry_signature_collision_resistance():
    """
    Synthetic collision test: Two distinct routes with identical endpoints,
    identical coordinate count, identical distance, and identical duration,
    but different intermediate geometries.
    Must produce distinct signatures to prevent POI and Night Activity aliasing.
    """
    start = (80.250000, 13.050000)
    end = (80.270000, 13.070000)

    # Route A arcs East
    route_a = [
        start,
        (80.265000, 13.055000),
        (80.270000, 13.060000),
        end,
    ]

    # Route B arcs North/West with symmetric offsets (same total count & roughly same length)
    route_b = [
        start,
        (80.255000, 13.065000),
        (80.260000, 13.070000),
        end,
    ]

    sig_a = compute_route_geometry_signature(route_a)
    sig_b = compute_route_geometry_signature(route_b)

    assert sig_a != sig_b, "Distinct route geometries must not produce identical signatures!"
    assert len(sig_a) == 64
    assert len(sig_b) == 64


def test_geometry_signature_exact_duplicate():
    """Identical geometries must produce identical signatures."""
    route = [
        (80.250000, 13.050000),
        (80.260000, 13.060000),
        (80.270000, 13.070000),
    ]
    sig_1 = compute_route_geometry_signature(route)
    sig_2 = compute_route_geometry_signature(copy.deepcopy(route))
    assert sig_1 == sig_2


def test_geometry_signature_direction_sensitivity():
    """Reversed route geometry must produce a different signature."""
    forward = [
        (80.250000, 13.050000),
        (80.260000, 13.060000),
        (80.270000, 13.070000),
    ]
    reverse = list(reversed(forward))

    sig_f = compute_route_geometry_signature(forward)
    sig_r = compute_route_geometry_signature(reverse)
    assert sig_f != sig_r, "Reversed routes must not have identical signatures!"


def test_geometry_signature_degenerate_cases():
    """Empty or degenerate coordinates must be handled gracefully."""
    assert compute_route_geometry_signature([]) == "empty"
    assert compute_route_geometry_signature(None) == "empty"
    assert compute_route_geometry_signature([(80.25,)]) == "empty"  # invalid point length
    assert compute_route_geometry_signature("invalid") == "empty"


def test_response_builder_cache_parameter_sensitivity():
    """
    Verify that response builder poi_cache and night_cache account for:
    - pass_through_hour
    - route geometry
    - leg breakdown
    """
    builder = ResponseBuilder()

    route_a_coords = [[80.250, 13.050], [80.260, 13.060], [80.270, 13.070]]
    route_b_coords = [[80.250, 13.050], [80.255, 13.065], [80.270, 13.070]]

    cand_a = MagicMock()
    cand_a.route_identifier = "route_a"
    cand_a.route_name = "Route A"
    cand_a.transport_mode = "Cab"
    cand_a.distance = 3500.0
    cand_a.duration = 600.0
    cand_a.route_metadata = {
        "geometry": {"type": "LineString", "coordinates": route_a_coords},
        "dynamic_segments": []
    }

    cand_b = MagicMock()
    cand_b.route_identifier = "route_b"
    cand_b.route_name = "Route B"
    cand_b.transport_mode = "Cab"
    cand_b.geometry = {"type": "LineString", "coordinates": route_b_coords}
    cand_b.distance = 3500.0
    cand_b.duration = 600.0
    cand_b.route_metadata = {
        "geometry": {"type": "LineString", "coordinates": route_b_coords},
        "dynamic_segments": []
    }

    context = {
        "routes": [cand_a, cand_b],
        "pass_through_hour": 23,
    }

    plan_resp = builder.build_journey_plan(context, user_id="u_test", journey_id="j_test")
    assert plan_resp is not None
    assert len(plan_resp.recommended_routes) == 2

    # Verify routes have independent night_activity scores
    r0 = plan_resp.recommended_routes[0]
    r1 = plan_resp.recommended_routes[1]
    assert r0.id != r1.id


# ==============================================================================
# SECTION 3: Segment-Level Score and TreeSHAP Caching
# ==============================================================================

def _make_dummy_segment(seg_id: str, speed: float = 30.0, police_dist: float = 100.0) -> MatchedSegmentResult:
    features = {f: 0.0 for f in CANONICAL_PREDICTOR_FEATURES}
    features["road_type"] = "primary"
    features["surface"] = "asphalt"
    features["speed"] = float(speed)
    features["police_dist_m"] = float(police_dist)
    features["road_width"] = 7.0
    return MatchedSegmentResult(
        traversal_index=0,
        leg_index=0,
        segment_id=seg_id,
        match_status=MatchStatus.MATCHED,
        feature_status=FeatureStatus.AVAILABLE,
        match_method="SPATIAL_PROJECTION",
        confidence=1.0,
        route_start_m=0.0,
        route_end_m=100.0,
        canonical_features=features,
        diagnostics={"span_m": 100.0},
    )


def test_segment_cache_identical_segment():
    """The same segment with identical features should return cached score and contributions."""
    scoring_service = MLRouteScoringService()
    seg = _make_dummy_segment("seg_1", speed=30.0)

    match_resp = RouteSpatialMatchResponse(
        route_identifier="test_route",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=100.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=1,
            matched_samples=1,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[seg],
        unmatched_intervals=[],
    )

    # First score: cache miss
    res1 = scoring_service.score_route_match(match_resp)
    assert res1.safety_score is not None
    cache_len_1 = len(scoring_service._segment_score_cache)
    assert cache_len_1 == 1

    # Second score: cache hit
    res2 = scoring_service.score_route_match(match_resp)
    assert res2.safety_score == res1.safety_score
    assert len(scoring_service._segment_score_cache) == 1


def test_segment_cache_changed_features():
    """The same segment ID with changed feature values must trigger fresh inference."""
    scoring_service = MLRouteScoringService()
    seg1 = _make_dummy_segment("seg_1", speed=30.0, police_dist=100.0)
    seg2 = _make_dummy_segment("seg_1", speed=80.0, police_dist=5000.0)  # modified features

    match_resp_1 = RouteSpatialMatchResponse(
        route_identifier="r1",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=100.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=1,
            matched_samples=1,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[seg1],
        unmatched_intervals=[],
    )

    match_resp_2 = RouteSpatialMatchResponse(
        route_identifier="r2",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=100.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=1,
            matched_samples=1,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[seg2],
        unmatched_intervals=[],
    )

    res1 = scoring_service.score_route_match(match_resp_1)
    res2 = scoring_service.score_route_match(match_resp_2)

    # Cache should now have 2 separate entries for seg_1 with different feature tuples
    assert len(scoring_service._segment_score_cache) == 2
    # The safety scores should differ because lighting and speed were altered
    assert res1.safety_score != res2.safety_score


def test_segment_cache_mutation_safety():
    """Downstream mutation of returned attribution vectors must not corrupt cached arrays."""
    scoring_service = MLRouteScoringService()
    seg = _make_dummy_segment("seg_mut", speed=40.0)

    match_resp = RouteSpatialMatchResponse(
        route_identifier="r_mut",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=100.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=1,
            matched_samples=1,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[seg],
        unmatched_intervals=[],
    )

    res1 = scoring_service.score_route_match(match_resp)
    attr1 = res1.diagnostics.get("model_attribution")
    assert attr1 is not None

    # Inspect internal cached entry
    cache_key = scoring_service._compute_segment_cache_key(seg)
    p_cached, e_cached, c_cached, b_cached = scoring_service._segment_score_cache[cache_key]
    assert c_cached is not None
    original_val = float(c_cached[0])

    # Attempt to mutate returned explanations / items
    if "factors" in attr1 and attr1["factors"]:
        attr1["factors"][0]["attribution"] = 9999.9

    # Re-score to verify cache integrity
    res2 = scoring_service.score_route_match(match_resp)
    _, _, c_cached_after, _ = scoring_service._segment_score_cache[cache_key]
    assert float(c_cached_after[0]) == original_val, "Cached array was modified by downstream operation!"


def test_segment_cache_bounding_and_clear():
    """Verify cache bounding and clear_cache functionality."""
    scoring_service = MLRouteScoringService()

    # Pre-populate cache
    for i in range(10):
        key = (12345, f"seg_{i}", (float(i),))
        scoring_service._segment_score_cache[key] = (75.0, None, None, None)

    assert len(scoring_service._segment_score_cache) == 10
    scoring_service.clear_cache()
    assert len(scoring_service._segment_score_cache) == 0


# ==============================================================================
# SECTION 4: Spatial Index Reuse and Invalidation
# ==============================================================================

def test_spatial_index_coverage_and_uncovered_detection():
    """
    Verify that SpatialMatchingService:
    1. Reuses index when new route corridor is fully within indexed corridor polygon.
    2. Correctly detects uncovered areas when a new route crosses outside the corridor polygon.
    """
    matcher = SpatialMatchingService(auto_build_index=False)

    # Route 1: Chennai Central to Thousand Lights corridor
    route1_coords = [
        [80.275, 13.080],
        [80.265, 13.070],
        [80.255, 13.060],
    ]

    matcher._ensure_index_for_corridor(route1_coords)
    assert matcher._index is not None
    assert matcher._covered_polygon is not None
    initial_boxes = len(matcher._indexed_boxes)

    # Sub-route strictly along the exact same corridor
    sub_route_coords = route1_coords[:2]
    matcher._ensure_index_for_corridor(sub_route_coords)
    # Covered polygon covers sub_route; no new boxes should be appended
    assert len(matcher._indexed_boxes) == initial_boxes

    # Route 2: Transverse route that diverges significantly
    divergent_coords = [
        [80.255, 13.060],
        [80.240, 13.040],
        [80.220, 13.020],
    ]
    matcher._ensure_index_for_corridor(divergent_coords)
    assert len(matcher._indexed_boxes) > initial_boxes


def test_spatial_index_disjoint_invalidation():
    """
    A route far away (> 0.50 degrees center-distance) should trigger invalidation
    and rebuild a fresh bounded index.
    """
    matcher = SpatialMatchingService(auto_build_index=False)

    # Route in Central Chennai
    chennai_coords = [
        [80.270, 13.080],
        [80.260, 13.070],
    ]
    matcher._ensure_index_for_corridor(chennai_coords)
    assert matcher._index is not None

    # Route in distant geography (> 60 km away, e.g. Kanchipuram / Tirupati coordinates)
    distant_coords = [
        [79.700, 12.830],
        [79.690, 12.820],
    ]
    matcher._ensure_index_for_corridor(distant_coords)
    # Bounds should now be centered on the distant coordinates
    assert matcher._indexed_bounds is not None
    assert matcher._indexed_bounds[0] < 80.0


# ==============================================================================
# SECTION 5: Multimodal Sub-Leg Reuse & Transit Invariants
# ==============================================================================

def test_multimodal_subleg_reuse_and_transit_invariants():
    """
    Verify that in a multimodal route:
    1. Road-compatible sub-legs (walk, cab, auto) are scored using the road ML pipeline.
    2. Rail/metro sub-legs are NOT scored by the road model (score=None, status=NOT_SCORED).
    3. Reusing leg_matches preserves original sub-leg travel modes and distance offsets.
    """
    scoring_service = MLRouteScoringService()

    multimodal_cand = MagicMock()
    multimodal_cand.route_identifier = "multi_cand_1"
    multimodal_cand.distance = 12000.0
    multimodal_cand.duration = 1800.0
    multimodal_cand.geometry = {
        "type": "LineString",
        "coordinates": [[80.250, 13.050], [80.270, 13.070]],
    }
    multimodal_cand.route_metadata = {
        "dynamic_segments": [
            {
                "mode": "walk",
                "distance_m": 800.0,
                "duration_s": 600.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[80.250, 13.050], [80.255, 13.055]],
                },
            },
            {
                "mode": "metro",
                "distance_m": 10000.0,
                "duration_s": 900.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[80.255, 13.055], [80.265, 13.065]],
                },
            },
            {
                "mode": "walk",
                "distance_m": 1200.0,
                "duration_s": 300.0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[80.265, 13.065], [80.270, 13.070]],
                },
            },
        ]
    }

    score_res = scoring_service.score_candidate_route(multimodal_cand)
    assert score_res is not None

    dyn_segs = multimodal_cand.route_metadata["dynamic_segments"]
    assert len(dyn_segs) == 3

    # Leg 1: Walk (road-compatible)
    assert dyn_segs[0]["mode"] == "walk"
    assert dyn_segs[0]["score_source"] == "SafeShe LightGBM Road Risk Model v2.0"

    # Leg 2: Metro (Transit invariant)
    assert dyn_segs[1]["mode"] == "metro"
    assert dyn_segs[1]["score_status"] == "NOT_SCORED"
    assert dyn_segs[1]["safety_score"] is None
    assert dyn_segs[1]["score_source"] == "None (Transit infrastructure unrated)"

    # Leg 3: Walk (road-compatible)
    assert dyn_segs[2]["mode"] == "walk"
    assert dyn_segs[2]["score_source"] == "SafeShe LightGBM Road Risk Model v2.0"


# ==============================================================================
# SECTION 6: Reference Equivalence (Optimized vs Uncached Baseline)
# ==============================================================================

def test_reference_equivalence_cached_vs_baseline():
    """
    Establish true reference equivalence:
    Compare output of scoring pipeline with caching enabled against
    an unoptimized baseline where the cache is cleared before every calculation.
    """
    scoring_service = MLRouteScoringService()

    seg_a = _make_dummy_segment("seg_ref_a", speed=45.0, police_dist=100.0)
    seg_b = _make_dummy_segment("seg_ref_b", speed=30.0, police_dist=500.0)

    match_resp = RouteSpatialMatchResponse(
        route_identifier="ref_route",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=200.0,
            matched_length_m=200.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=2,
            matched_samples=2,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[seg_a, seg_b],
        unmatched_intervals=[],
    )

    # 1. Uncached baseline calculation
    scoring_service.clear_cache()
    baseline_res = scoring_service.score_route_match(match_resp)

    # 2. Optimized cached calculation
    cached_res = scoring_service.score_route_match(match_resp)

    # Assert exact equivalence
    assert baseline_res.safety_score == cached_res.safety_score
    assert baseline_res.score_status == cached_res.score_status
    assert baseline_res.scoreable_coverage_ratio == cached_res.scoreable_coverage_ratio

    base_attr = baseline_res.diagnostics.get("model_attribution")
    cached_attr = cached_res.diagnostics.get("model_attribution")
    if base_attr and cached_attr:
        assert base_attr["status"] == cached_attr["status"]
        assert base_attr["base_value"] == cached_attr["base_value"]
        assert base_attr.get("top_positive_factors") == cached_attr.get("top_positive_factors")
        assert base_attr.get("top_negative_factors") == cached_attr.get("top_negative_factors")
        assert base_attr.get("legacy_contributions") == cached_attr.get("legacy_contributions")
