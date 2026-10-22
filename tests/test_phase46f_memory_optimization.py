import pytest
import pandas as pd
import numpy as np
from typing import Dict, Any

from app.ml.loader import SafeMLArtifactLoader
from app.ml.predictor import MLSafetyPredictor, get_ml_safety_predictor
from app.api.dependencies import get_journey_coordinator
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    ScoreStatus,
    MatchedSegmentResult,
    RouteSpatialMatchResponse,
    RouteCoverageMetrics,
)
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES, CATEGORICAL_FEATURES
from app.models.journey import CandidateRoute


def _make_dummy_canonical_features(segment_id: str, is_valid: bool = True) -> Dict[str, Any]:
    row = {"segment_id": segment_id}
    for col in CANONICAL_PREDICTOR_FEATURES:
        if col in CATEGORICAL_FEATURES:
            row[col] = "primary" if col == "road_type" else "asphalt"
        else:
            row[col] = 10.0 if is_valid else np.nan
    return row


def test_artifact_loader_caching_and_isolation():
    """Verify that SafeMLArtifactLoader caches loaded artifacts across calls and can be cleared."""
    m1, p1, mf1 = SafeMLArtifactLoader.load_artifacts(use_cache=True)
    m2, p2, mf2 = SafeMLArtifactLoader.load_artifacts(use_cache=True)

    assert m1 is m2, "Model instance must be identical when cached"
    assert p1 is p2, "Preprocessor instance must be identical when cached"
    assert mf1 is mf2, "Manifest dict must be identical when cached"

    # Test clear_cache
    SafeMLArtifactLoader.clear_cache()
    assert SafeMLArtifactLoader._cached_artifacts is None

    # Reload repopulates cache
    m3, p3, mf3 = SafeMLArtifactLoader.load_artifacts(use_cache=True)
    assert m3 is not None
    assert SafeMLArtifactLoader._cached_artifacts is not None


def test_ml_safety_predictor_singleton():
    """Verify that get_ml_safety_predictor returns the shared singleton instance."""
    pred1 = get_ml_safety_predictor()
    pred2 = get_ml_safety_predictor()
    assert pred1 is pred2, "get_ml_safety_predictor must return a singleton"
    assert pred1.model is not None
    assert pred1.preprocessor is not None


def test_repeated_scoring_consistency_and_no_leakage():
    """Verify that scoring identical inputs yields identical scores, and separate inputs do not leak."""
    predictor = get_ml_safety_predictor()

    row_a = _make_dummy_canonical_features("seg_a", is_valid=True)
    df_a = pd.DataFrame([row_a])[CANONICAL_PREDICTOR_FEATURES]

    pred_a1 = predictor.predict_segments(df_a)
    pred_a2 = predictor.predict_segments(df_a)

    assert np.allclose(pred_a1, pred_a2), "Repeated predictions on identical data must be deterministic"

    # Generate distinct synthetic feature row
    row_b = _make_dummy_canonical_features("seg_b", is_valid=True)
    for col in CANONICAL_PREDICTOR_FEATURES:
        if col not in CATEGORICAL_FEATURES:
            row_b[col] = 500.0
    df_b = pd.DataFrame([row_b])[CANONICAL_PREDICTOR_FEATURES]

    pred_b = predictor.predict_segments(df_b)
    assert not np.allclose(pred_a1, pred_b), "Distinct features must yield distinct predictions"


def test_compute_explainability_toggle_omits_subleg_treeshap():
    """Verify compute_explainability=False produces identical safety scores while omitting SHAP explanations."""
    predictor = get_ml_safety_predictor()
    scoring_service = MLRouteScoringService(predictor=predictor)

    matched_seg = MatchedSegmentResult(
        traversal_index=0,
        leg_index=0,
        segment_id="seg_001",
        way_id=1001,
        road_type="primary",
        match_status=MatchStatus.MATCHED,
        match_method="test",
        match_distance_m=1.0,
        route_start_m=0.0,
        route_end_m=100.0,
        feature_status=FeatureStatus.AVAILABLE,
        canonical_features=_make_dummy_canonical_features("seg_001", is_valid=True),
    )

    match_response = RouteSpatialMatchResponse(
        route_identifier="test_route",
        travel_mode="Road",
        status="SUCCESS",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=100.0,
            unmatched_length_m=0.0,
            coverage_ratio=1.0,
            total_samples=10,
            matched_samples=10,
            unmatched_samples=0,
            ambiguous_samples=0,
        ),
        matched_segments=[matched_seg],
        unmatched_intervals=[],
        diagnostics={},
    )

    # Score with explainability enabled (e.g. for primary route)
    res_with_shap = scoring_service.score_route_match(
        match_response,
        travel_mode="Road",
        route_identifier="test_with_shap",
        compute_explainability=True,
    )

    # Score with explainability disabled (e.g. for dynamic sub-legs)
    res_without_shap = scoring_service.score_route_match(
        match_response,
        travel_mode="Road",
        route_identifier="test_without_shap",
        compute_explainability=False,
    )

    assert res_with_shap.score_status == ScoreStatus.READY
    assert res_without_shap.score_status == ScoreStatus.READY
    assert np.isclose(res_with_shap.safety_score, res_without_shap.safety_score), (
        "Safety scores must be identical regardless of whether TreeSHAP is computed"
    )

    # Explainability attributions are computed when True, bypassed when False
    assert res_with_shap.diagnostics.get("model_attribution") is not None
    assert len(res_with_shap.diagnostics.get("legacy_contributions", {})) > 0

    assert res_without_shap.diagnostics.get("model_attribution") is None
    assert res_without_shap.diagnostics.get("legacy_contributions") == {}


def test_journey_coordinator_dependency_singleton():
    """Verify get_journey_coordinator returns the shared coordinator singleton."""
    coord1 = get_journey_coordinator()
    coord2 = get_journey_coordinator()
    assert coord1 is coord2, "get_journey_coordinator must return a singleton"
    assert isinstance(coord1, JourneyIntelligenceCoordinator)
    assert coord1.ml_predictor is get_ml_safety_predictor()


def test_insufficient_coverage_honesty():
    """Verify low coverage is honestly reported as INSUFFICIENT_COVERAGE rather than READY."""
    predictor = get_ml_safety_predictor()
    scoring_service = MLRouteScoringService(predictor=predictor)

    matched_seg = MatchedSegmentResult(
        traversal_index=0,
        leg_index=0,
        segment_id="seg_low_cov",
        way_id=1002,
        road_type="primary",
        match_status=MatchStatus.MATCHED,
        match_method="test",
        match_distance_m=1.0,
        route_start_m=0.0,
        route_end_m=20.0,
        feature_status=FeatureStatus.AVAILABLE,
        canonical_features=_make_dummy_canonical_features("seg_low_cov", is_valid=True),
    )

    match_response = RouteSpatialMatchResponse(
        route_identifier="low_cov_route",
        travel_mode="Road",
        status="PARTIAL",
        coverage=RouteCoverageMetrics(
            total_route_length_m=100.0,
            matched_length_m=20.0,
            unmatched_length_m=80.0,
            coverage_ratio=0.2, # 20% coverage, strictly below 70%
            total_samples=10,
            matched_samples=2,
            unmatched_samples=8,
            ambiguous_samples=0,
        ),
        matched_segments=[matched_seg],
        unmatched_intervals=[],
        diagnostics={},
    )

    res = scoring_service.score_route_match(
        match_response,
        travel_mode="Road",
        route_identifier="low_cov_route",
        compute_explainability=True,
    )

    assert res.score_status == ScoreStatus.INSUFFICIENT_COVERAGE
    assert res.safety_score is None
    assert res.scoreable_coverage_ratio == 0.2


def test_transit_legs_remain_not_scored():
    """Verify multimodal routes with transit legs do not fabricate road scores for transit legs."""
    predictor = get_ml_safety_predictor()
    scoring_service = MLRouteScoringService(predictor=predictor)

    leg_road = {
        "mode": "walk",
        "summary": "Walk to station",
        "duration_s": 120,
        "distance_m": 50.0,
        "geometry": [[80.2498, 13.0500], [80.2502, 13.0500]],
    }
    leg_transit = {
        "mode": "metro",
        "summary": "Metro Line",
        "duration_s": 600,
        "distance_m": 1000.0,
        "geometry": [[80.2502, 13.0500], [80.2502, 13.0600]],
    }

    candidate = CandidateRoute(
        route_identifier="route_multimodal_test",
        distance=1050.0,
        duration=720.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "travel_mode": "Multimodal",
            "dynamic_segments": [leg_road, leg_transit],
        },
    )

    scored_res = scoring_service.score_candidate_routes([candidate])[0]

    # Transit leg is not road-scoreable, coverage is strictly low (< 70%)
    assert scored_res.safety_score is None
    assert scored_res.score_status == ScoreStatus.INSUFFICIENT_COVERAGE
    # Transit leg is explicitly marked NOT_SCORED without a fabricated safety_score
    transit_seg = candidate.route_metadata["dynamic_segments"][1]
    assert transit_seg.get("score_status") == "NOT_SCORED"
    assert transit_seg.get("safety_score") is None


import threading
from concurrent.futures import ThreadPoolExecutor
from app.api.dependencies import reset_journey_coordinator, _coordinator_lock
from app.ml.predictor import reset_ml_safety_predictor, _predictor_lock
from app.ml.loader import MLArtifactSecurityError, _cache_lock


def test_artifact_loader_concurrent_cold_start_single_initialization(monkeypatch):
    """Verify that multiple concurrent cold-start calls initialize artifacts exactly once."""
    SafeMLArtifactLoader.clear_cache()
    call_count = 0
    original_do_load = SafeMLArtifactLoader._do_load_artifacts

    def mock_do_load(verify_checksum=True):
        nonlocal call_count
        call_count += 1
        # Return a mock tuple rather than loading real 60MB disk artifact multiple times
        return ({"mock": "model"}, {"mock": "prep"}, {"model_version": "2.0.0"})

    monkeypatch.setattr(SafeMLArtifactLoader, "_do_load_artifacts", mock_do_load)

    thread_count = 10
    barrier = threading.Barrier(thread_count)
    results = []

    def worker():
        barrier.wait()
        return SafeMLArtifactLoader.load_artifacts(use_cache=True)

    try:
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker) for _ in range(thread_count)]
            results = [f.result() for f in futures]

        assert call_count == 1, f"Artifacts must be loaded exactly once, was loaded {call_count} times"
        first_res = results[0]
        for res in results[1:]:
            assert res is first_res, "All concurrent callers must receive the exact same cached artifact tuple"
            assert res[0] is first_res[0]
            assert res[1] is first_res[1]
            assert res[2] is first_res[2]
    finally:
        SafeMLArtifactLoader.clear_cache()


def test_artifact_loader_failed_initialization_leaves_cache_empty(monkeypatch):
    """Verify that failed artifact verification or deserialization never leaves a poisoned cache."""
    SafeMLArtifactLoader.clear_cache()

    def mock_failing_load(verify_checksum=True):
        raise MLArtifactSecurityError("Simulated checksum failure")

    monkeypatch.setattr(SafeMLArtifactLoader, "_do_load_artifacts", mock_failing_load)

    with pytest.raises(MLArtifactSecurityError, match="Simulated checksum failure"):
        SafeMLArtifactLoader.load_artifacts(use_cache=True)

    assert SafeMLArtifactLoader._cached_artifacts is None, "Cache must remain None upon load failure"

    # Subsequent valid load succeeds and populates cache
    def mock_succeeding_load(verify_checksum=True):
        return ({"recovered": "model"}, {"recovered": "prep"}, {"model_version": "2.0.0"})

    monkeypatch.setattr(SafeMLArtifactLoader, "_do_load_artifacts", mock_succeeding_load)
    arts = SafeMLArtifactLoader.load_artifacts(use_cache=True)
    assert arts is not None
    assert SafeMLArtifactLoader._cached_artifacts is not None
    SafeMLArtifactLoader.clear_cache()


def test_predictor_singleton_concurrent_cold_start(monkeypatch):
    """Verify concurrent cold-start calls return the same MLSafetyPredictor singleton without duplicate construction."""
    reset_ml_safety_predictor()
    init_count = 0
    real_init = MLSafetyPredictor.__init__

    def mock_init(self, verify_checksum=True):
        nonlocal init_count
        init_count += 1
        self.model = {"mock": "model"}
        self.preprocessor = {"mock": "prep"}
        self.manifest = {"model_version": "2.0.0"}

    monkeypatch.setattr(MLSafetyPredictor, "__init__", mock_init)

    thread_count = 10
    barrier = threading.Barrier(thread_count)
    instances = []

    def worker():
        barrier.wait()
        return get_ml_safety_predictor()

    try:
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker) for _ in range(thread_count)]
            instances = [f.result() for f in futures]

        assert init_count == 1, f"MLSafetyPredictor must be constructed exactly once, got {init_count}"
        first_instance = instances[0]
        for inst in instances[1:]:
            assert inst is first_instance, "All threads must receive the identical predictor singleton"
    finally:
        reset_ml_safety_predictor()


def test_predictor_singleton_failed_initialization_not_poisoned(monkeypatch):
    """Verify that an initialization failure does not leave a poisoned predictor singleton."""
    reset_ml_safety_predictor()

    def mock_failing_init(self, verify_checksum=True):
        raise RuntimeError("Simulated predictor initialization error")

    monkeypatch.setattr(MLSafetyPredictor, "__init__", mock_failing_init)

    with pytest.raises(RuntimeError, match="Simulated predictor initialization error"):
        get_ml_safety_predictor()

    import app.ml.predictor as pred_module
    assert pred_module._shared_ml_predictor is None, "Predictor singleton must remain None after failure"

    # Subsequent successful init works cleanly
    def mock_ok_init(self, verify_checksum=True):
        self.model = {"ok": "model"}
        self.preprocessor = {"ok": "prep"}
        self.manifest = {"model_version": "2.0.0"}

    monkeypatch.setattr(MLSafetyPredictor, "__init__", mock_ok_init)
    pred = get_ml_safety_predictor()
    assert pred is not None
    assert pred_module._shared_ml_predictor is pred
    reset_ml_safety_predictor()


def test_journey_coordinator_concurrent_cold_start(monkeypatch):
    """Verify concurrent calls to get_journey_coordinator return the same coordinator without duplicate initialization."""
    reset_journey_coordinator()
    init_count = 0

    def mock_init(self, **kwargs):
        nonlocal init_count
        init_count += 1
        self.ml_predictor = None

    monkeypatch.setattr(JourneyIntelligenceCoordinator, "__init__", mock_init)

    thread_count = 10
    barrier = threading.Barrier(thread_count)
    instances = []

    def worker():
        barrier.wait()
        return get_journey_coordinator()

    try:
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(worker) for _ in range(thread_count)]
            instances = [f.result() for f in futures]

        assert init_count == 1, f"JourneyIntelligenceCoordinator must be initialized once, got {init_count}"
        first_coord = instances[0]
        for coord in instances[1:]:
            assert coord is first_coord, "All threads must receive the identical coordinator singleton"
    finally:
        reset_journey_coordinator()


def test_journey_coordinator_failed_init_does_not_poison(monkeypatch):
    """Verify that an initialization failure does not leave a poisoned coordinator singleton."""
    reset_journey_coordinator()

    def mock_failing_coord_init(self, **kwargs):
        raise RuntimeError("Simulated coordinator dependency failure")

    monkeypatch.setattr(JourneyIntelligenceCoordinator, "__init__", mock_failing_coord_init)

    with pytest.raises(RuntimeError, match="Simulated coordinator dependency failure"):
        get_journey_coordinator()

    import app.api.dependencies as deps_module
    assert deps_module._shared_journey_coordinator is None, "Coordinator singleton must remain None on failure"

    # Next attempt with clean init succeeds
    def mock_ok_coord_init(self, **kwargs):
        self.ml_predictor = None

    monkeypatch.setattr(JourneyIntelligenceCoordinator, "__init__", mock_ok_coord_init)
    coord = get_journey_coordinator()
    assert coord is not None
    assert deps_module._shared_journey_coordinator is coord
    reset_journey_coordinator()


def test_journey_coordinator_lock_not_held_during_operations():
    """Verify that the coordinator lock is released immediately after singleton initialization and never held during operations."""
    coord = get_journey_coordinator()
    assert coord is not None
    assert not _coordinator_lock.locked(), "Coordinator lock must not be held after initialization"
