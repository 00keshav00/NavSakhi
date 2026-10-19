import logging
import math
import time
from typing import List, Dict, Any, Optional, Set, Tuple

import numpy as np
import pandas as pd

from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    ScoreStatus,
    MatchedSegmentResult,
    SegmentScoringResult,
    RouteScoreResult,
    RouteSpatialMatchResponse,
)
from app.services.spatial_matcher import SpatialMatchingService
from app.ml.predictor import MLSafetyPredictor
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES

logger = logging.getLogger(__name__)

# Modes that physically traverse roads and are semantically compatible with the road-segment ML model
ROAD_COMPATIBLE_MODES: Set[str] = {
    "walk",
    "walking",
    "cab",
    "driving",
    "auto",
    "two_wheeler",
    "four_wheeler",
    "taxi",
    "car",
    "bicycle",
    "pedestrian",
    "personal vehicle",
    "road",
}

# Modes that operate on separate transit rights-of-way (tracks, viaducts, tunnels)
TRANSIT_MODES: Set[str] = {
    "metro",
    "suburban",
    "train",
    "mrts",
    "bus",
    "transit",
}


class MLRouteScoringService:
    """
    Integrates genuine frozen LightGBM inference into SafeShe route scoring.
    
    Pipeline:
    Candidate Route -> Spatial Snapping -> Feature Bridging -> LightGBM Batch Inference
    -> Traversal-Length-Weighted Aggregation -> Score Readiness Verification.
    """

    def __init__(
        self,
        spatial_matcher: Optional[SpatialMatchingService] = None,
        predictor: Optional[MLSafetyPredictor] = None,
        min_scoreable_coverage: float = 0.70,
        road_compatible_modes: Optional[Set[str]] = None,
    ):
        self.spatial_matcher = spatial_matcher or SpatialMatchingService(auto_build_index=False)
        self.predictor = predictor or MLSafetyPredictor()
        self.min_scoreable_coverage = float(min_scoreable_coverage)
        self.road_compatible_modes = set(road_compatible_modes) if road_compatible_modes else ROAD_COMPATIBLE_MODES

    # --- Core Route Scoring ---

    def score_route_match(
        self,
        match_response: RouteSpatialMatchResponse,
        travel_mode: str = "Road",
        route_identifier: str = "route_0",
        transit_unscored_length_m: float = 0.0,
    ) -> RouteScoreResult:
        """
        Executes genuine frozen-model inference on matched segments and aggregates scores
        using traversal-length-weighted averaging.
        """
        t0 = time.perf_counter()
        total_route_length_m = match_response.coverage.total_route_length_m + transit_unscored_length_m

        if total_route_length_m <= 0.0 or (len(match_response.matched_segments) == 0 and transit_unscored_length_m <= 0.0):
            return RouteScoreResult(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                safety_score=None,
                score_status=ScoreStatus.NO_SCOREABLE_SEGMENTS,
                scoreable_length_m=0.0,
                total_route_length_m=0.0,
                scoreable_coverage_ratio=0.0,
                min_coverage_threshold=self.min_scoreable_coverage,
                diagnostics={"error": "Route has zero length or no evaluated segments"},
            )

        # Check if entire route failed matching (e.g. outside Chennai reference network)
        if match_response.status == "FAILED" and match_response.coverage.matched_samples == 0:
            return RouteScoreResult(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                safety_score=None,
                score_status=ScoreStatus.UNSUPPORTED_GEOGRAPHY,
                scoreable_length_m=0.0,
                total_route_length_m=round(total_route_length_m, 2),
                scoreable_coverage_ratio=0.0,
                min_coverage_threshold=self.min_scoreable_coverage,
                diagnostics={
                    "reason": "Route lacks matching reference road segments (outside supported geography or beyond threshold)"
                },
            )

        # Filter to scoreable segments: MATCHED + AVAILABLE feature row
        eligible_items: List[Tuple[int, MatchedSegmentResult]] = []
        for idx, seg in enumerate(match_response.matched_segments):
            if (
                seg.match_status == MatchStatus.MATCHED
                and seg.feature_status == FeatureStatus.AVAILABLE
                and seg.canonical_features is not None
            ):
                eligible_items.append((idx, seg))

        scored_segment_results: List[SegmentScoringResult] = []

        if not eligible_items:
            # Determine reason
            has_matched = any(s.match_status == MatchStatus.MATCHED for s in match_response.matched_segments)
            status = ScoreStatus.FEATURE_DATA_UNAVAILABLE if has_matched else ScoreStatus.NO_SCOREABLE_SEGMENTS

            # Populate audit segment records
            for seg in match_response.matched_segments:
                span_len = float(seg.diagnostics.get("span_m") or max(0.0, seg.route_end_m - seg.route_start_m))
                scored_segment_results.append(
                    SegmentScoringResult(
                        traversal_index=seg.traversal_index,
                        leg_index=seg.leg_index,
                        segment_id=seg.segment_id,
                        span_length_m=round(span_len, 2),
                        safety_score=None,
                        match_status=seg.match_status,
                        feature_status=seg.feature_status,
                        is_scoreable=False,
                        diagnostics=seg.diagnostics,
                    )
                )

            return RouteScoreResult(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                safety_score=None,
                score_status=status,
                scoreable_length_m=0.0,
                total_route_length_m=round(total_route_length_m, 2),
                scoreable_coverage_ratio=0.0,
                min_coverage_threshold=self.min_scoreable_coverage,
                scored_segments=scored_segment_results,
                diagnostics={"eligible_segments_count": 0},
            )

        # Batch ML inference
        try:
            # Build DataFrame strictly preserving input row order
            feature_dicts = [seg.canonical_features for _, seg in eligible_items]
            batch_df = pd.DataFrame(feature_dicts)

            # Ensure all canonical features exist in exact schema order
            batch_df = batch_df[CANONICAL_PREDICTOR_FEATURES]

            # Execute real frozen LightGBM inference and TreeSHAP attribution
            predictions = self.predictor.predict_segments(batch_df)
            explanations = self.predictor.explain_segments(batch_df)

            if len(predictions) != len(eligible_items):
                raise RuntimeError(
                    f"Predictor returned {len(predictions)} predictions for {len(eligible_items)} input rows"
                )

        except Exception as e:
            logger.error(f"Frozen ML predictor inference failed: {e}")
            return RouteScoreResult(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                safety_score=None,
                score_status=ScoreStatus.INFERENCE_ERROR,
                scoreable_length_m=0.0,
                total_route_length_m=round(total_route_length_m, 2),
                scoreable_coverage_ratio=0.0,
                min_coverage_threshold=self.min_scoreable_coverage,
                diagnostics={"inference_error": str(e), "model_attribution": None, "legacy_contributions": {}},
            )

        # Map predictions and explanations back to segments and compute length-weighted mean
        eligible_pred_map: Dict[int, float] = {
            eligible_items[k][0]: float(predictions[k]) for k in range(len(eligible_items))
        }
        eligible_expl_map: Dict[int, Any] = {
            eligible_items[k][0]: (explanations[k] if explanations and k < len(explanations) else None)
            for k in range(len(eligible_items))
        }

        weighted_score_sum = 0.0
        scoreable_length_total = 0.0

        for idx, seg in enumerate(match_response.matched_segments):
            span_len = float(seg.diagnostics.get("span_m") or max(0.0, seg.route_end_m - seg.route_start_m))
            # Fallback if span_len is 0
            if span_len <= 0.0:
                span_len = max(1.0, float(seg.diagnostics.get("length_m", 10.0)))

            if idx in eligible_pred_map:
                pred_score = eligible_pred_map[idx]
                seg_expl = eligible_expl_map.get(idx)
                weighted_score_sum += pred_score * span_len
                scoreable_length_total += span_len
                scored_segment_results.append(
                    SegmentScoringResult(
                        traversal_index=seg.traversal_index,
                        leg_index=seg.leg_index,
                        segment_id=seg.segment_id,
                        span_length_m=round(span_len, 2),
                        safety_score=round(pred_score, 2),
                        match_status=seg.match_status,
                        feature_status=seg.feature_status,
                        is_scoreable=True,
                        diagnostics={
                            **seg.diagnostics,
                            "predicted_score": round(pred_score, 2),
                            "feature_attribution": seg_expl,
                        },
                    )
                )
            else:
                scored_segment_results.append(
                    SegmentScoringResult(
                        traversal_index=seg.traversal_index,
                        leg_index=seg.leg_index,
                        segment_id=seg.segment_id,
                        span_length_m=round(span_len, 2),
                        safety_score=None,
                        match_status=seg.match_status,
                        feature_status=seg.feature_status,
                        is_scoreable=False,
                        diagnostics=seg.diagnostics,
                    )
                )

        scoreable_coverage_ratio = float(scoreable_length_total / total_route_length_m) if total_route_length_m > 0 else 0.0
        scoreable_coverage_ratio = max(0.0, min(1.0, scoreable_coverage_ratio))

        # Check coverage policy and compute route-level TreeSHAP attribution
        route_model_attribution = None
        legacy_contributions: Dict[str, str] = {}

        if scoreable_length_total <= 0.0:
            final_safety_score = None
            final_status = ScoreStatus.NO_SCOREABLE_SEGMENTS
        elif scoreable_coverage_ratio < self.min_scoreable_coverage:
            final_safety_score = None
            final_status = ScoreStatus.INSUFFICIENT_COVERAGE
        else:
            final_safety_score = round(float(weighted_score_sum / scoreable_length_total), 2)
            final_status = ScoreStatus.READY

            # Aggregate length-weighted feature attribution across scoreable segments
            try:
                if explanations and all(e is not None for e in explanations):
                    feature_names = self.predictor.preprocessor.get_feature_names_out()
                    base_val = float(explanations[0]["base_value"])
                    
                    X = batch_df[CANONICAL_PREDICTOR_FEATURES]
                    X_trans = self.predictor.preprocessor.transform(X)
                    raw_contrib_matrix = self.predictor.model.booster_.predict(X_trans, pred_contrib=True)[:, :-1]

                    seg_spans = np.array([
                        float(match_response.matched_segments[eligible_items[k][0]].diagnostics.get("span_m") or
                              max(1.0, match_response.matched_segments[eligible_items[k][0]].route_end_m - match_response.matched_segments[eligible_items[k][0]].route_start_m))
                        for k in range(len(eligible_items))
                    ], dtype=np.float64)
                    
                    seg_span_sum = float(np.sum(seg_spans))
                    if seg_span_sum > 0:
                        seg_weights = seg_spans / seg_span_sum
                        weighted_contribs = np.sum(raw_contrib_matrix * seg_weights[:, np.newaxis], axis=0)
                        reconstructed = float(np.sum(weighted_contribs) + base_val)
                        recon_error = abs(reconstructed - final_safety_score)

                        from app.ml.predictor import clean_feature_label
                        pos_factors = []
                        neg_factors = []
                        for f_idx, c_val in enumerate(weighted_contribs):
                            val = float(c_val)
                            if abs(val) < 0.01:
                                continue
                            label = clean_feature_label(feature_names[f_idx])
                            item = {
                                "feature": label,
                                "raw_feature": str(feature_names[f_idx]),
                                "attribution": round(val, 3),
                                "direction": "SAFETY_ENHANCING" if val > 0 else "RISK_INCREASING",
                            }
                            if val > 0:
                                pos_factors.append(item)
                            else:
                                neg_factors.append(item)

                        pos_factors.sort(key=lambda x: x["attribution"], reverse=True)
                        neg_factors.sort(key=lambda x: x["attribution"])

                        for item in (pos_factors[:3] + neg_factors[:2]):
                            sign = "+" if item["attribution"] > 0 else ""
                            legacy_contributions[item["feature"]] = f"{sign}{item['attribution']:.2f}"

                        route_model_attribution = {
                            "method": "LightGBM TreeSHAP (native pred_contrib, length-weighted traversal aggregation)",
                            "base_value": round(base_val, 3),
                            "safety_score": final_safety_score,
                            "reconstructed_score": round(reconstructed, 2),
                            "reconstruction_error": round(recon_error, 4),
                            "is_mathematically_reconstructed": recon_error < 0.05,
                            "target": "safety_score (Synthetic Environmental Proxy [0, 100])",
                            "top_positive_factors": pos_factors[:5],
                            "top_negative_factors": neg_factors[:5],
                            "status": "VALIDATED_ATTRIBUTION",
                        }
            except Exception as e:
                logger.warning(f"Failed to aggregate route TreeSHAP explainability: {e}")
                route_model_attribution = None

        scoring_time_ms = (time.perf_counter() - t0) * 1000.0

        return RouteScoreResult(
            route_identifier=route_identifier,
            travel_mode=travel_mode,
            safety_score=final_safety_score,
            score_status=final_status,
            scoreable_length_m=round(scoreable_length_total, 2),
            total_route_length_m=round(total_route_length_m, 2),
            scoreable_coverage_ratio=round(scoreable_coverage_ratio, 4),
            min_coverage_threshold=self.min_scoreable_coverage,
            score_basis="matched_road_segments_only",
            is_synthetic_proxy=True,
            scored_segments=scored_segment_results,
            diagnostics={
                "scoring_time_ms": round(scoring_time_ms, 2),
                "evaluated_segments_count": len(scored_segment_results),
                "scoreable_segments_count": len(eligible_items),
                "transit_unscored_length_m": round(transit_unscored_length_m, 2),
                "model_attribution": route_model_attribution,
                "legacy_contributions": legacy_contributions,
            },
        )

    # --- Candidate Route Scoring Boundary ---

    def score_candidate_route(self, candidate_route: Any) -> RouteScoreResult:
        """
        Evaluates and scores a single CandidateRoute instance, attaching verified ML scoring
        metadata to candidate_route.route_metadata without synthetic fallbacks.
        """
        route_meta = getattr(candidate_route, "route_metadata", {}) or {}
        route_id = getattr(candidate_route, "route_identifier", "route")
        travel_mode = route_meta.get("travel_mode", "Road")

        # Check for multimodal dynamic_segments
        dynamic_segs = route_meta.get("dynamic_segments")

        if dynamic_segs and isinstance(dynamic_segs, list) and len(dynamic_segs) > 0:
            # Separate road legs from transit legs
            road_legs = []
            transit_unscored_len = 0.0

            for leg_idx, leg in enumerate(dynamic_segs):
                leg_mode = str(leg.get("mode", "unknown")).lower()
                leg_dist = float(leg.get("distance_m", 0.0))

                if leg_mode in self.road_compatible_modes:
                    road_legs.append(leg)
                else:
                    # Transit leg (metro, train, suburban, etc.)
                    # Excluded from road snapping; counted as unscored transit traversal
                    transit_unscored_len += leg_dist

            if road_legs:
                match_res = self.spatial_matcher.match_multimodal_route(road_legs, route_identifier=route_id)
            else:
                # 100% transit route with no road legs
                from app.schemas.spatial_schemas import RouteCoverageMetrics
                match_res = RouteSpatialMatchResponse(
                    route_identifier=route_id,
                    travel_mode="Transit",
                    status="PARTIAL",
                    coverage=RouteCoverageMetrics(
                        total_route_length_m=0.0,
                        matched_length_m=0.0,
                        unmatched_length_m=0.0,
                        coverage_ratio=0.0,
                        total_samples=0,
                        matched_samples=0,
                        unmatched_samples=0,
                        ambiguous_samples=0,
                    ),
                    matched_segments=[],
                    unmatched_intervals=[],
                    diagnostics={"transit_only": True},
                )

            score_res = self.score_route_match(
                match_res,
                travel_mode="Multimodal",
                route_identifier=route_id,
                transit_unscored_length_m=transit_unscored_len,
            )

        else:
            # Single-road route
            geom = route_meta.get("geometry")
            match_res = self.spatial_matcher.match_route(
                geom,
                route_identifier=route_id,
                travel_mode=travel_mode,
            )
            score_res = self.score_route_match(
                match_res,
                travel_mode=travel_mode,
                route_identifier=route_id,
            )

        # Attach to route_metadata
        route_meta["ml_scoring"] = score_res.model_dump()
        route_meta["spatial_match"] = match_res.model_dump()
        route_meta["safety_score"] = score_res.safety_score
        route_meta["score_status"] = score_res.score_status.value
        route_meta["scoreable_coverage_ratio"] = score_res.scoreable_coverage_ratio
        route_meta["score_basis"] = score_res.score_basis
        route_meta["model_explainability"] = score_res.diagnostics.get("model_attribution")
        route_meta["contributions"] = score_res.diagnostics.get("legacy_contributions", {})
        # Score individual legs/segments independently
        dynamic_segs = route_meta.get("dynamic_segments", [])
        if dynamic_segs:
            for s_idx, d_seg in enumerate(dynamic_segs):
                s_mode = str(d_seg.get("mode", "")).lower().strip()
                s_geom = d_seg.get("geometry", {})
                
                # Check if road-compatible
                if any(m in s_mode for m in ["auto", "cab", "walk", "bike", "two_wheeler", "driving", "personal"]):
                    try:
                        seg_match = self.spatial_matcher.match_route(s_geom, travel_mode=s_mode)
                        seg_score_res = self.score_route_match(
                            seg_match,
                            travel_mode=s_mode,
                            route_identifier=f"{route_id}_leg_{s_idx+1}"
                        )
                        d_seg["score_status"] = seg_score_res.score_status.value
                        d_seg["safety_score"] = seg_score_res.safety_score
                        d_seg["scoreable_coverage_ratio"] = seg_score_res.scoreable_coverage_ratio
                        d_seg["score_source"] = "SafeShe LightGBM Road Risk Model v2.0"
                        d_seg["score_disclosure"] = "Synthetic environmental safety proxy (100.0 - risk_score_raw) based on road infrastructure features."
                    except Exception as e:
                        logger.warning(f"Failed to score road leg {s_idx}: {e}")
                        d_seg["score_status"] = "INFERENCE_FAILED"
                        d_seg["safety_score"] = None
                        d_seg["scoreable_coverage_ratio"] = 0.0
                        d_seg["score_source"] = "SafeShe LightGBM Road Risk Model v2.0"
                        d_seg["score_disclosure"] = f"Inference failed: {str(e)}"
                else:
                    # Transit leg (metro, suburban, train, mrts, bus):
                    # STRICT INVARIANT: DO NOT apply road model to railway/metro tracks!
                    d_seg["score_status"] = "NOT_SCORED"
                    d_seg["safety_score"] = None
                    d_seg["scoreable_coverage_ratio"] = 0.0
                    d_seg["score_source"] = "None (Transit infrastructure unrated)"
                    d_seg["score_disclosure"] = "Transit track safety assessment is not modeled by the road-segment LightGBM pipeline."

        candidate_route.route_metadata = route_meta
        return score_res

    def score_candidate_routes(self, candidate_routes: List[Any]) -> List[RouteScoreResult]:
        """
        Scores all candidate routes, attaching ML scores, and sorts routes deterministically:
        1. Routes with READY safety scores (descending safety score).
        2. Routes with unscored/unsupported states (sorted by duration ascending).
        """
        results = []
        for cand in candidate_routes:
            res = self.score_candidate_route(cand)
            results.append(res)

        # Deterministic ranking policy:
        # READY routes sorted by safety_score descending.
        # Unscored routes sorted by duration ascending at the end without fake scores.
        def route_rank_key(cand: Any) -> Tuple[int, float, float]:
            meta = getattr(cand, "route_metadata", {}) or {}
            score = meta.get("safety_score")
            duration = float(getattr(cand, "duration", 0.0))
            if score is not None:
                # Scored routes: rank 1, higher score first, then shorter duration first
                return (1, float(score), -duration)
            else:
                # Unscored routes: rank 0, shorter duration first
                return (0, 0.0, -duration)

        candidate_routes.sort(key=route_rank_key, reverse=True)
        return results
