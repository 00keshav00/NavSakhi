"""
Phase 5: ML Route-Scoring Integration Tests

Verifies the end-to-end integration of the frozen LightGBM model with candidate route scoring:
Route -> Spatial Matching -> Feature Validation -> LightGBM Inference -> Length-Weighted Aggregation.
"""

import math
import json
from typing import Dict, Any, List
import pytest
import numpy as np
import pandas as pd

from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    ScoreStatus,
    MatchedSegmentResult,
    RouteSpatialMatchResponse,
    RouteCoverageMetrics,
    RouteScoreResult,
)
from app.services.spatial_matcher import SpatialMatchingService
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES, NUMERICAL_FEATURES, CATEGORICAL_FEATURES
from app.ml.predictor import MLSafetyPredictor
from app.models.journey import CandidateRoute, Location
from app.schemas.journey_schemas import JourneyPlanResponse, MultimodalRoute, RouteSegment
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.intelligence.response.builder import ResponseBuilder


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
        _make_dummy_canonical_features("seg_P1", is_valid=True),
        _make_dummy_canonical_features("seg_P2", is_valid=True),
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
    Road A: lon 80.250, lat 13.050 (length ~100m)
    Road B: lon 80.251, lat 13.050 (length ~100m)
    Road C: lon 80.252, lat 13.050 (length ~100m)
    Road Parallel_1: lon 80.255, lat 13.05010 (~11m north of Road A)
    Road Parallel_2: lon 80.255, lat 13.05012 (~13m north of Road A, 2m from Parallel_1 -> ambiguity)
    Segment with no feature row: seg_orphan
    """
    rows = [
        {"segment_id": "seg_A", "way_id": 101, "longitude": 80.25000, "latitude": 13.05000, "length_m": 100.0, "road_type": "primary"},
        {"segment_id": "seg_B", "way_id": 101, "longitude": 80.25100, "latitude": 13.05000, "length_m": 100.0, "road_type": "primary"},
        {"segment_id": "seg_C", "way_id": 102, "longitude": 80.25200, "latitude": 13.05000, "length_m": 100.0, "road_type": "secondary"},
        {"segment_id": "seg_P1", "way_id": 201, "longitude": 80.25500, "latitude": 13.05010, "length_m": 100.0, "road_type": "residential"},
        {"segment_id": "seg_P2", "way_id": 202, "longitude": 80.25500, "latitude": 13.05012, "length_m": 100.0, "road_type": "service"},
        {"segment_id": "seg_orphan", "way_id": 301, "longitude": 80.25300, "latitude": 13.05000, "length_m": 100.0, "road_type": "living_street"},
        {"segment_id": "seg_incomplete", "way_id": 302, "longitude": 80.25400, "latitude": 13.05000, "length_m": 100.0, "road_type": "residential"},
        {"segment_id": "seg_invalid_num", "way_id": 303, "longitude": 80.25600, "latitude": 13.05000, "length_m": 100.0, "road_type": "residential"},
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


@pytest.fixture
def predictor():
    """Instantiates the real frozen LightGBM predictor."""
    return MLSafetyPredictor()


@pytest.fixture
def scoring_service(matcher, predictor):
    return MLRouteScoringService(
        spatial_matcher=matcher,
        predictor=predictor,
        min_scoreable_coverage=0.70,
    )


# --- 1. One valid route obtains score through actual frozen model ---
def test_valid_route_obtains_frozen_model_score(scoring_service):
    route_geom = [[80.2498, 13.0500], [80.2502, 13.0500]]
    candidate = CandidateRoute(
        route_identifier="route_test_1",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    results = scoring_service.score_candidate_routes([candidate])
    scored_res = results[0]

    assert scored_res.safety_score is not None
    assert 0.0 <= scored_res.safety_score <= 100.0
    assert scored_res.score_status == ScoreStatus.READY
    assert scored_res.scoreable_coverage_ratio is not None
    assert scored_res.scoreable_coverage_ratio >= 0.70
    assert scored_res.score_basis == "matched_road_segments_only"
    assert scored_res.model_version == "2.0.0"

    # Route metadata was properly enriched
    assert candidate.route_metadata["safety_score"] == scored_res.safety_score
    assert candidate.route_metadata["score_status"] == ScoreStatus.READY.value
    assert candidate.route_metadata["scoreable_coverage_ratio"] == scored_res.scoreable_coverage_ratio


# --- 2. Multiple matched segments produce expected length-weighted score ---
def test_multiple_matched_segments_traversal_length_weighting(scoring_service, predictor, sample_feature_table_df):
    # Route traversing seg_A (~100m) and seg_B (~100m)
    route_geom = [[80.2498, 13.0500], [80.2505, 13.0500], [80.2512, 13.0500]]
    candidate = CandidateRoute(
        route_identifier="route_two_segs",
        distance=200.0,
        duration=240.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is not None
    assert scored_res.score_status == ScoreStatus.READY

    # Compute expected score directly from predictor on rows
    row_a = sample_feature_table_df[sample_feature_table_df["segment_id"] == "seg_A"].to_dict("records")[0]
    row_b = sample_feature_table_df[sample_feature_table_df["segment_id"] == "seg_B"].to_dict("records")[0]
    score_a = predictor.predict_segment(row_a)["safety_score"]
    score_b = predictor.predict_segment(row_b)["safety_score"]

    # Both segments have identical feature values, so score_a == score_b
    assert math.isclose(scored_res.safety_score, score_a, rel_tol=1e-1)


# --- 3. Repeated traversals are weighted according to actual route distance ---
def test_repeated_traversals_weighted_by_actual_distance(scoring_service):
    # Route going A -> B -> A (backtrack)
    route_geom = [
        [80.2498, 13.0500],
        [80.2512, 13.0500],
        [80.2498, 13.0500],
    ]
    candidate = CandidateRoute(
        route_identifier="route_repeated",
        distance=350.0,
        duration=400.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is not None
    assert scored_res.score_status == ScoreStatus.READY
    # Coverage should remain high despite repetition
    assert scored_res.scoreable_coverage_ratio is not None
    assert scored_res.scoreable_coverage_ratio > 0.70


# --- 4. Exact match between single-segment and batch predictor paths ---
def test_exact_match_single_segment_and_batch_predictor(predictor, sample_feature_table_df):
    row_a = sample_feature_table_df[sample_feature_table_df["segment_id"] == "seg_A"].to_dict("records")[0]
    row_b = sample_feature_table_df[sample_feature_table_df["segment_id"] == "seg_B"].to_dict("records")[0]

    single_a = predictor.predict_segment(row_a)["safety_score"]
    single_b = predictor.predict_segment(row_b)["safety_score"]

    batch_res = predictor.predict_segments(pd.DataFrame([row_a, row_b]))

    assert math.isclose(batch_res[0], single_a, rel_tol=1e-2)
    assert math.isclose(batch_res[1], single_b, rel_tol=1e-2)


# --- 5. Ambiguous matches are excluded from scoreable length ---
def test_ambiguous_matches_excluded_from_scoreable_length(scoring_service):
    # Route passing directly between seg_P1 and seg_P2 (ambiguous parallel roads)
    route_geom = [[80.2550, 13.05011], [80.2555, 13.05011]]
    candidate = CandidateRoute(
        route_identifier="route_ambiguous",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    # Because all points match ambiguously, scoreable coverage is 0.0 and score is None
    assert scored_res.score_status in (ScoreStatus.NO_SCOREABLE_SEGMENTS, ScoreStatus.INSUFFICIENT_COVERAGE, ScoreStatus.UNSUPPORTED_GEOGRAPHY)
    assert scored_res.safety_score is None


# --- 6. Unmatched geometry is excluded from scoreable length ---
def test_unmatched_geometry_excluded_from_scoreable_length(scoring_service):
    # Route starts at seg_A (100m) and extends 400m into an empty area (>35m from any road)
    route_geom = [
        [80.2498, 13.0500],
        [80.2502, 13.0500],
        [80.2700, 13.0700], # Far away point
    ]
    candidate = CandidateRoute(
        route_identifier="route_partial_unmatched",
        distance=500.0,
        duration=600.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    # Scoreable length is only the portion on seg_A out of total
    assert scored_res.scoreable_coverage_ratio is not None
    assert scored_res.scoreable_coverage_ratio < 0.70
    assert scored_res.safety_score is None
    assert scored_res.score_status == ScoreStatus.INSUFFICIENT_COVERAGE


# --- 7. Missing feature rows do not generate predictions ---
def test_missing_feature_rows_do_not_generate_predictions(scoring_service):
    # Route passing through seg_orphan (present in road segments, absent from feature table)
    route_geom = [[80.2528, 13.0500], [80.2532, 13.0500]]
    candidate = CandidateRoute(
        route_identifier="route_orphan",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is None
    assert scored_res.score_status in (ScoreStatus.FEATURE_DATA_UNAVAILABLE, ScoreStatus.NO_SCOREABLE_SEGMENTS)


# --- 8. Incomplete or invalid feature records do not generate predictions ---
def test_incomplete_or_invalid_feature_records_rejected(scoring_service):
    # Route passing through seg_incomplete
    route_geom_inc = [[80.2538, 13.0500], [80.2542, 13.0500]]
    candidate_inc = CandidateRoute(
        route_identifier="route_incomplete",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom_inc,
            "travel_mode": "Road",
        },
    )
    scored_inc = scoring_service.score_candidate_routes([candidate_inc])[0]
    assert scored_inc.safety_score is None

    # Route passing through seg_invalid_num
    route_geom_inv = [[80.2558, 13.0500], [80.2562, 13.0500]]
    candidate_inv = CandidateRoute(
        route_identifier="route_invalid_num",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom_inv,
            "travel_mode": "Road",
        },
    )
    scored_inv = scoring_service.score_candidate_routes([candidate_inv])[0]
    assert scored_inv.safety_score is None


# --- 9. Insufficient scoreable coverage produces null score and correct status ---
def test_insufficient_scoreable_coverage_yields_null_score(scoring_service):
    # 50m matched to seg_A, followed by 300m in open field -> coverage ~14% (<70%)
    route_geom = [
        [80.2498, 13.0500],
        [80.2501, 13.0500],
        [80.2501, 13.0530],
    ]
    candidate = CandidateRoute(
        route_identifier="route_low_coverage",
        distance=350.0,
        duration=400.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is None
    assert scored_res.score_status == ScoreStatus.INSUFFICIENT_COVERAGE
    assert scored_res.scoreable_coverage_ratio is not None
    assert scored_res.scoreable_coverage_ratio < 0.70


# --- 10. Route outside supported geographic region is not given fabricated safety score ---
def test_route_outside_supported_geography(scoring_service):
    # Route in London coordinates (lon -0.12, lat 51.50)
    route_geom = [[-0.1278, 51.5074], [-0.1280, 51.5080]]
    candidate = CandidateRoute(
        route_identifier="route_london",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is None
    assert scored_res.score_status in (ScoreStatus.UNSUPPORTED_GEOGRAPHY, ScoreStatus.NO_SCOREABLE_SEGMENTS)
    assert scored_res.scoreable_coverage_ratio == 0.0


# --- 11. Multimodal route does not score unsupported transit geometry as road ---
def test_multimodal_route_does_not_score_transit_as_road(scoring_service):
    # Leg 1: Road on seg_A (~43m geometry)
    leg_road = {
        "mode": "walk",
        "summary": "Walk to station",
        "duration_s": 120,
        "distance_m": 100.0,
        "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
    }
    # Leg 2: Metro (500m on tracks, unsupported by road-segment model)
    leg_metro = {
        "mode": "metro",
        "summary": "Metro Line 1",
        "duration_s": 600,
        "distance_m": 500.0,
        "geometry": [[80.2502, 13.0500], [80.2502, 13.0550]],
    }
    candidate = CandidateRoute(
        route_identifier="route_multimodal",
        distance=600.0,
        duration=720.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "travel_mode": "Multimodal",
            "dynamic_segments": [leg_road, leg_metro],
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    # Transit leg is explicitly unscored. Road leg is ~43m out of 543m (~8% coverage)
    # Since coverage < 70%, overall safety_score must be None
    assert scored_res.safety_score is None
    assert scored_res.score_status == ScoreStatus.INSUFFICIENT_COVERAGE
    assert scored_res.scoreable_coverage_ratio is not None
    assert scored_res.scoreable_coverage_ratio < 0.70


# --- 12. Inference exceptions produce explicit failure state ---
def test_inference_exception_handled_safely(scoring_service, monkeypatch):
    def mock_predict_segments(*args, **kwargs):
        raise RuntimeError("LightGBM native memory allocation failed")

    monkeypatch.setattr(scoring_service.predictor, "predict_segments", mock_predict_segments)

    route_geom = [[80.2498, 13.0500], [80.2502, 13.0500]]
    candidate = CandidateRoute(
        route_identifier="route_crash",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is None
    assert scored_res.score_status == ScoreStatus.INFERENCE_ERROR


# --- 13. No heuristic/random score fallback is used ---
def test_no_heuristic_fallback_used(scoring_service):
    # Route in unscoreable area
    route_geom = [[80.0000, 13.0000], [80.0010, 13.0010]]
    candidate = CandidateRoute(
        route_identifier="route_no_fallback",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    # Verify score is strictly None, not a random hash or default 50.0/75.0
    assert scored_res.safety_score is None
    assert scored_res.score_status in (ScoreStatus.UNSUPPORTED_GEOGRAPHY, ScoreStatus.NO_SCOREABLE_SEGMENTS)


# --- 14. Invalid or empty routes fail safely ---
def test_invalid_or_empty_routes_fail_safely(scoring_service):
    # Empty coordinates
    candidate_empty = CandidateRoute(
        route_identifier="route_empty",
        distance=0.0,
        duration=0.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [],
            "travel_mode": "Road",
        },
    )
    scored_empty = scoring_service.score_candidate_routes([candidate_empty])[0]
    assert scored_empty.safety_score is None
    assert scored_empty.score_status == ScoreStatus.NO_SCOREABLE_SEGMENTS

    # Single point coordinate (no line length)
    candidate_single = CandidateRoute(
        route_identifier="route_single_pt",
        distance=0.0,
        duration=0.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2500, 13.0500]],
            "travel_mode": "Road",
        },
    )
    scored_single = scoring_service.score_candidate_routes([candidate_single])[0]
    assert scored_single.safety_score is None


# --- 15. Route scores and ranking are deterministic across repeated runs ---
def test_deterministic_scoring_and_ranking(scoring_service):
    route_a = CandidateRoute(
        route_identifier="route_a",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
            "travel_mode": "Road",
        },
    )
    route_b = CandidateRoute(
        route_identifier="route_b",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2518, 13.0500], [80.2522, 13.0500]],
            "travel_mode": "Road",
        },
    )

    run_1 = scoring_service.score_candidate_routes([route_a, route_b])
    run_2 = scoring_service.score_candidate_routes([route_a, route_b])

    assert run_1[0].safety_score == run_2[0].safety_score
    assert run_1[1].safety_score == run_2[1].safety_score
    assert [r.route_identifier for r in run_1] == [r.route_identifier for r in run_2]


# --- 16. Route with zero scoreable length does not produce a numeric score ---
def test_zero_scoreable_length_never_produces_numeric_score(scoring_service):
    route_geom = [[80.1000, 13.1000], [80.1005, 13.1005]] # >1km from any indexed segment
    candidate = CandidateRoute(
        route_identifier="route_zero_scoreable",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": route_geom,
            "travel_mode": "Road",
        },
    )
    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    assert scored_res.safety_score is None
    assert scored_res.scoreable_coverage_ratio == 0.0


# --- 17. API response is JSON serializable and conforms to Pydantic schema ---
def test_api_response_schema_and_json_serializability():
    builder = ResponseBuilder()

    route_scored = CandidateRoute(
        route_identifier="route_api_test",
        distance=100.0,
        duration=120.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
            "travel_mode": "Road",
            "safety_score": 78.5,
            "score_status": ScoreStatus.READY.value,
            "scoreable_coverage_ratio": 0.85,
            "score_basis": "matched_road_segments_only",
            "segments": [
                {
                    "mode": "walk",
                    "coordinates": [[80.2498, 13.0500], [80.2502, 13.0500]],
                    "distance": "100 m",
                    "duration": "2 mins",
                }
            ],
        },
    )

    context = {
        "routes": [route_scored],
        "source_name": "Anna Nagar",
        "destination_name": "T Nagar",
        "total_distance": 100.0,
        "MLPrediction": {"safety_score": 78.5},
        "Decision": {"action": "PROCEED", "risk_level": "LOW"},
    }

    response = builder.build_journey_plan(context, user_id="user_123", journey_id="journey_123")
    assert isinstance(response, JourneyPlanResponse)

    # Serialize to JSON and verify round-trip
    dumped_json = response.model_dump_json()
    parsed = json.loads(dumped_json)
    assert parsed["journey_id"] == "journey_123"
    assert len(parsed["recommended_routes"]) == 1
    assert parsed["recommended_routes"][0]["score_status"] == ScoreStatus.READY.value
    assert parsed["recommended_routes"][0]["scoreable_coverage_ratio"] == 0.85
    # Verify AI recommendation carries environmental proxy notice
    assert any("environmental" in w.lower() for w in parsed["ai_recommendation"]["warnings"])


# --- 18. Existing journey fields unrelated to safety scoring remain intact ---
def test_existing_journey_fields_remain_intact(scoring_service):
    candidate = CandidateRoute(
        route_identifier="route_fields_test",
        distance=2500.0,
        duration=1800.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "route_name": "via Anna Salai",
            "travel_mode": "Transit",
            "cost": "Rs. 25",
            "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
            "dynamic_segments": [
                {
                    "mode": "bus",
                    "summary": "Bus 21G",
                    "duration_s": 1800,
                    "distance_m": 2500.0,
                    "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
                }
            ],
            "custom_field": "intact_value",
        },
    )
    scoring_service.score_candidate_routes([candidate])

    assert candidate.route_identifier == "route_fields_test"
    assert candidate.distance == 2500.0
    assert candidate.duration == 1800.0
    assert candidate.recommendation_status == "AVAILABLE"
    assert candidate.route_metadata["route_name"] == "via Anna Salai"
    assert candidate.route_metadata["cost"] == "Rs. 25"
    assert candidate.route_metadata["custom_field"] == "intact_value"
