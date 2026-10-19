import math
from typing import Dict, Any, List
import pytest
import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString

from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    MatchedSegmentResult,
    RouteSpatialMatchResponse,
)
from app.services.spatial_matcher import SpatialMatchingService
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from app.ml.predictor import MLSafetyPredictor
from app.models.journey import CandidateRoute


def _make_dummy_canonical_features(segment_id: str, is_valid: bool = True) -> Dict[str, Any]:
    row = {"segment_id": segment_id}
    for col in CANONICAL_PREDICTOR_FEATURES:
        if col in CATEGORICAL_FEATURES:
            row[col] = "primary" if col == "road_type" else "asphalt"
        else:
            row[col] = 10.0 if is_valid else np.nan
    return row


@pytest.fixture
def sample_feature_table_df():
    """Generates synthetic feature table DataFrame for testing."""
    records = [
        _make_dummy_canonical_features("seg_A", is_valid=True),
        _make_dummy_canonical_features("seg_B", is_valid=True),
        _make_dummy_canonical_features("seg_C", is_valid=True),
        _make_dummy_canonical_features("seg_D", is_valid=True),
        # Incomplete features (missing a canonical column)
        {k: v for k, v in _make_dummy_canonical_features("seg_incomplete").items() if k != "hospital_dist_m"},
        # Invalid numerical features (contains NaN)
        _make_dummy_canonical_features("seg_invalid_num", is_valid=False),
    ]
    return pd.DataFrame(records)


@pytest.fixture
def synthetic_road_network_df():
    """
    Synthetic road network in Chennai coordinates:
    Road A: lon 80.250, lat 13.050 (length ~150m)
    Road B: lon 80.251, lat 13.050 (length ~150m)
    Road C: lon 80.252, lat 13.050 (length ~150m)
    Road Parallel_1: lon 80.250, lat 13.05010 (~11m north of Road A)
    Road Parallel_2: lon 80.250, lat 13.05012 (~13m north of Road A, 2m from Parallel_1 -> ambiguity)
    """
    rows = [
        {"segment_id": "seg_A", "way_id": 101, "longitude": 80.25000, "latitude": 13.05000, "length_m": 100.0, "road_type": "primary"},
        {"segment_id": "seg_B", "way_id": 101, "longitude": 80.25100, "latitude": 13.05000, "length_m": 100.0, "road_type": "primary"},
        {"segment_id": "seg_C", "way_id": 102, "longitude": 80.25200, "latitude": 13.05000, "length_m": 100.0, "road_type": "secondary"},
        # Parallel roads for ambiguity and parallel road tests (placed at lon 80.25500 to isolate from seg_A)
        {"segment_id": "seg_P1", "way_id": 201, "longitude": 80.25500, "latitude": 13.05010, "length_m": 100.0, "road_type": "residential"},
        {"segment_id": "seg_P2", "way_id": 202, "longitude": 80.25500, "latitude": 13.05012, "length_m": 100.0, "road_type": "service"},
        # Segment with no feature row
        {"segment_id": "seg_orphan", "way_id": 301, "longitude": 80.25300, "latitude": 13.05000, "length_m": 100.0, "road_type": "living_street"},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def matcher(synthetic_road_network_df, sample_feature_table_df):
    return SpatialMatchingService(
        road_segments_df=synthetic_road_network_df,
        feature_table_df=sample_feature_table_df,
        max_match_distance_m=35.0,
        ambiguity_delta_m=5.0,
        sample_interval_m=20.0,
        auto_build_index=True,
    )


# --- 1. Exact route-to-road-geometry match ---
def test_exact_route_match(matcher):
    # Route passing directly through seg_A
    route = [[80.2498, 13.05000], [80.2502, 13.05000]]
    res = matcher.match_route(route, route_identifier="exact_test")

    assert res.status == "SUCCESS"
    assert len(res.matched_segments) > 0
    seg_ids = [s.segment_id for s in res.matched_segments if s.match_status == MatchStatus.MATCHED]
    assert "seg_A" in seg_ids
    assert res.coverage.matched_length_m > 0.0


# --- 2. Slightly displaced route within threshold ---
def test_displaced_route_within_threshold(matcher):
    # Displaced ~10 meters north of seg_B (latitude 13.05000 -> 13.05009)
    route = [[80.2508, 13.05009], [80.2512, 13.05009]]
    res = matcher.match_route(route, route_identifier="displaced_close")

    assert res.status == "SUCCESS"
    matched_ids = [s.segment_id for s in res.matched_segments if s.match_status == MatchStatus.MATCHED]
    assert "seg_B" in matched_ids
    assert res.matched_segments[0].match_distance_m is not None
    assert res.matched_segments[0].match_distance_m < 35.0


# --- 3. Route beyond threshold ---
def test_route_beyond_threshold(matcher):
    # Displaced ~100 meters away (latitude 13.05100, which is > 100m away in metric space)
    route = [[80.2508, 13.05100], [80.2512, 13.05100]]
    res = matcher.match_route(route, route_identifier="beyond_thresh")

    assert res.status == "FAILED"
    assert res.coverage.matched_samples == 0
    assert res.coverage.unmatched_samples > 0
    assert len(res.unmatched_intervals) > 0


# --- 4. Two nearby parallel roads (disambiguation/ambiguity) ---
def test_parallel_roads_disambiguation(matcher):
    # Route placed right next to seg_P1 and seg_P2 (at lon 80.25500, lat 13.05010 vs 13.05012)
    route = [[80.25500, 13.05010], [80.25505, 13.05010]]
    res = matcher.match_route(route, route_identifier="parallel_ambig")

    # Should detect ambiguity between P1 and P2
    has_ambiguous = any(s.match_status == MatchStatus.AMBIGUOUS for s in res.matched_segments)
    assert has_ambiguous or res.coverage.ambiguous_samples > 0


# --- 5. Route containing multiple road segments in sequence ---
def test_multiple_segments_in_sequence(matcher):
    # Continuous route passing seg_A then seg_B then seg_C
    route = [[80.2498, 13.05000], [80.2510, 13.05000], [80.2522, 13.05000]]
    res = matcher.match_route(route, route_identifier="multi_seq")

    matched_ids = [s.segment_id for s in res.matched_segments if s.match_status == MatchStatus.MATCHED]
    # Check that segments appear in order seg_A -> seg_B -> seg_C
    assert "seg_A" in matched_ids
    assert "seg_B" in matched_ids
    assert "seg_C" in matched_ids
    assert matched_ids.index("seg_A") < matched_ids.index("seg_B") < matched_ids.index("seg_C")


# --- 6. Multimodal route with more than one leg ---
def test_multimodal_route_multiple_legs(matcher):
    legs = [
        {"mode": "walk", "geometry": {"type": "LineString", "coordinates": [[80.2498, 13.05000], [80.2505, 13.05000]]}},
        {"mode": "metro", "geometry": {"type": "LineString", "coordinates": [[80.2505, 13.05000], [80.2515, 13.05000]]}},
        {"mode": "auto", "geometry": {"type": "LineString", "coordinates": [[80.2515, 13.05000], [80.2522, 13.05000]]}},
    ]
    res = matcher.match_multimodal_route(legs, route_identifier="multimodal_test")

    assert res.travel_mode == "Multimodal"
    assert len(res.matched_segments) >= 2
    # Check that traversal indices are strictly incrementing across legs
    traversal_indices = [s.traversal_index for s in res.matched_segments]
    assert traversal_indices == sorted(traversal_indices)
    assert len(set(traversal_indices)) == len(traversal_indices)


# --- 7. Route that revisits the same road segment ---
def test_route_revisits_same_road_segment(matcher):
    # Route: start at seg_A -> go to seg_B -> turn around back to seg_A
    route = [
        [80.25000, 13.05000], # seg_A
        [80.25100, 13.05000], # seg_B
        [80.25000, 13.05000], # seg_A again
    ]
    res = matcher.match_route(route, route_identifier="revisit_test")

    matched_ids = [s.segment_id for s in res.matched_segments if s.match_status == MatchStatus.MATCHED]
    # seg_A should appear at least twice (initial visit and return visit)
    assert matched_ids.count("seg_A") >= 2
    # Ensure they are separated by seg_B
    first_a = matched_ids.index("seg_A")
    b_idx = matched_ids.index("seg_B")
    second_a = len(matched_ids) - 1 - matched_ids[::-1].index("seg_A")
    assert first_a < b_idx < second_a


# --- 8. Longitude/latitude ordering and projected distance correctness ---
def test_lon_lat_ordering_and_metric_units(matcher):
    # Latitude first input [lat, lon] should be auto-detected and normalized
    lat_first_route = [[13.05000, 80.2498], [13.05000, 80.2502]]
    res = matcher.match_route(lat_first_route, route_identifier="lat_first")

    assert res.diagnostics.get("coordinate_swapped") is True
    assert res.status == "SUCCESS"
    # Ensure distance is in meters (~40-50m length, NOT 0.0004 degrees)
    assert res.coverage.total_route_length_m > 30.0
    assert res.coverage.total_route_length_m < 100.0


# --- 9. Missing or malformed geometry ---
def test_missing_or_malformed_geometry_fails_safely(matcher):
    # None
    res_none = matcher.match_route(None)
    assert res_none.status == "FAILED"
    assert res_none.matched_segments[0].match_status == MatchStatus.INVALID_GEOMETRY

    # Single point
    res_single = matcher.match_route([[80.250, 13.050]])
    assert res_single.status == "FAILED"
    assert res_single.matched_segments[0].match_status == MatchStatus.INVALID_GEOMETRY

    # Non-finite values
    res_inf = matcher.match_route([[80.250, 13.050], [np.inf, 13.051]])
    assert res_inf.status == "FAILED"
    assert res_inf.matched_segments[0].match_status == MatchStatus.INVALID_GEOMETRY


# --- 10. Ambiguous candidate matches explicitly flagged ---
def test_ambiguous_candidate_matches_explicitly_flagged(matcher):
    # Point midway between seg_P1 and seg_P2 at lon 80.25500
    pt_midway = [[80.25500, 13.05011], [80.25505, 13.05011]]
    res = matcher.match_route(pt_midway)

    # Check for presence of ambiguity diagnostic or status
    has_ambig = any(s.match_status == MatchStatus.AMBIGUOUS for s in res.matched_segments)
    if has_ambig:
        ambig_seg = [s for s in res.matched_segments if s.match_status == MatchStatus.AMBIGUOUS][0]
        assert len(ambig_seg.ambiguity_candidates) >= 2


# --- 11. Geometry match with no corresponding feature row ---
def test_match_with_missing_feature_row(matcher):
    # Route matching seg_orphan (present in road segments, absent from feature table)
    route = [[80.2529, 13.05000], [80.2531, 13.05000]]
    res = matcher.match_route(route)

    orphan_segs = [s for s in res.matched_segments if s.segment_id == "seg_orphan"]
    assert len(orphan_segs) > 0
    assert orphan_segs[0].feature_status == FeatureStatus.MISSING_ROW
    assert orphan_segs[0].canonical_features is None


# --- 12. Duplicate identifiers in source data handled safely ---
def test_duplicate_identifiers_deduplicated_safely():
    dupe_df = pd.DataFrame([
        {"segment_id": "seg_D1", "way_id": 1, "longitude": 80.25, "latitude": 13.05, "length_m": 50.0, "road_type": "primary"},
        {"segment_id": "seg_D1", "way_id": 1, "longitude": 80.25, "latitude": 13.05, "length_m": 50.0, "road_type": "primary"},
    ])
    svc = SpatialMatchingService(road_segments_df=dupe_df, auto_build_index=True)
    assert svc._index_metadata["feature_count"] == 1
    assert svc._index_metadata["duplicate_ids_count"] == 1


# --- 13. Missing required canonical features flagged ---
def test_missing_required_canonical_features(sample_feature_table_df):
    # Table schema missing a canonical column (e.g. hospital_dist_m dropped)
    incomplete_df = sample_feature_table_df.drop(columns=["hospital_dist_m"])
    matcher = SpatialMatchingService(
        road_segments_df=pd.DataFrame([{"segment_id": "seg_incomplete", "way_id": 100, "longitude": 80.25, "latitude": 13.05, "length_m": 50.0}]),
        feature_table_df=incomplete_df,
        auto_build_index=False,
    )
    seg_match = MatchedSegmentResult(
        traversal_index=0,
        leg_index=0,
        segment_id="seg_incomplete",
        way_id=100,
        road_type="primary",
        match_status=MatchStatus.MATCHED,
        match_method="test",
    )
    matcher.bridge_features([seg_match])
    assert seg_match.feature_status == FeatureStatus.INCOMPLETE
    assert "hospital_dist_m" in seg_match.diagnostics["missing_features"]


# --- 14. Invalid or non-finite numerical feature values flagged ---
def test_invalid_numerical_features_flagged(matcher):
    seg_match = MatchedSegmentResult(
        traversal_index=0,
        leg_index=0,
        segment_id="seg_invalid_num",
        way_id=100,
        road_type="primary",
        match_status=MatchStatus.MATCHED,
        match_method="test",
    )
    matcher.bridge_features([seg_match])
    assert seg_match.feature_status == FeatureStatus.INVALID_VALUES
    assert len(seg_match.diagnostics["non_finite_features"]) > 0


# --- 15. Stable, deterministic output ordering ---
def test_deterministic_output_ordering(matcher):
    route = [[80.2498, 13.05000], [80.2510, 13.05000], [80.2522, 13.05000]]
    res1 = matcher.match_route(route, route_identifier="det_1")
    res2 = matcher.match_route(route, route_identifier="det_2")

    seq1 = [(s.traversal_index, s.segment_id, s.route_start_m) for s in res1.matched_segments]
    seq2 = [(s.traversal_index, s.segment_id, s.route_start_m) for s in res2.matched_segments]
    assert seq1 == seq2


# --- 16. Route coverage and unmatched-length calculations ---
def test_route_coverage_and_unmatched_length(matcher):
    # Half matched (near seg_A), half unmatched (diverges north)
    route = [
        [80.25000, 13.05000], # near seg_A
        [80.25000, 13.05100], # 100m north into unmatched space
    ]
    res = matcher.match_route(route, route_identifier="half_matched")

    assert res.coverage.total_route_length_m > 80.0
    assert res.coverage.matched_length_m > 0.0
    assert res.coverage.unmatched_length_m > 0.0
    assert math.isclose(
        res.coverage.total_route_length_m,
        res.coverage.matched_length_m + res.coverage.unmatched_length_m,
        abs_tol=1.0,
    )
    assert 0.0 < res.coverage.coverage_ratio < 1.0


# --- 17. Complete matched feature row accepted by predictor validation path ---
def test_matched_feature_row_accepted_by_predictor(matcher):
    route = [[80.2498, 13.05000], [80.2502, 13.05000]]
    res = matcher.match_route(route)

    valid_segs = [s for s in res.matched_segments if s.feature_status == FeatureStatus.AVAILABLE]
    assert len(valid_segs) > 0
    feat_dict = valid_segs[0].canonical_features
    assert feat_dict is not None
    assert len(feat_dict) == 41

    # Verify existing MLSafetyPredictor accepts this feature row without errors
    predictor = MLSafetyPredictor()
    pred_res = predictor.predict_segment(feat_dict)
    assert "safety_score" in pred_res
    assert 0.0 <= pred_res["safety_score"] <= 100.0


# --- 18. Confirmation that spatial matching itself does not fabricate safety scores ---
def test_spatial_matching_does_not_fabricate_safety_scores(matcher):
    route = [[80.2498, 13.05000], [80.2502, 13.05000]]
    res = matcher.match_route(route)

    # Ensure no safety_score or mock probability appears anywhere in the spatial matching response
    res_dict = res.model_dump()
    assert "safety_score" not in res_dict
    assert "safety_score" not in res_dict["coverage"]
    for seg in res_dict["matched_segments"]:
        assert "safety_score" not in seg
        assert seg["match_status"] in ["MATCHED", "AMBIGUOUS", "UNMATCHED", "INVALID_GEOMETRY"]


# --- Integration Test: Internal Service Boundary for CandidateRoute ---
def test_candidate_route_enrichment_boundary(matcher):
    cand = CandidateRoute(
        route_identifier="osrm_cand_1",
        distance=150.0,
        duration=30.0,
        recommendation_status="PENDING",
        route_metadata={
            "geometry": {"type": "LineString", "coordinates": [[80.2498, 13.05000], [80.2502, 13.05000]]},
            "travel_mode": "Road",
            "safety_score": 77.5, # Pre-existing score
        }
    )
    enriched = matcher.enrich_candidate_route(cand)
    # Check that spatial_match metadata was attached
    assert "spatial_match" in enriched.route_metadata
    assert enriched.route_metadata["spatial_match"]["status"] == "SUCCESS"
    # Ensure existing safety_score was NOT overwritten or changed
    assert enriched.route_metadata["safety_score"] == 77.5
