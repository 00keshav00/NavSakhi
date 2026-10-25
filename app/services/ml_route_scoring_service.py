import copy
import logging
import math
import time
from collections import OrderedDict
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
        self._segment_score_cache: OrderedDict[Any, Tuple[float, Optional[Dict[str, Any]], Optional[np.ndarray], Optional[float]]] = OrderedDict()

    def clear_cache(self) -> None:
        """Clears the segment score and TreeSHAP cache."""
        self._segment_score_cache.clear()

    def _compute_segment_cache_key(self, seg: MatchedSegmentResult) -> Optional[Tuple[Any, ...]]:
        """
        Computes a deterministic cache key binding:
        1. Model instance ID (ensuring model rotations invalidate cache)
        2. Segment ID
        3. Canonical feature vector tuple (ensuring altered features trigger fresh inference)
        """
        seg_id = str(seg.segment_id) if seg.segment_id else None
        if not seg_id or not seg.canonical_features:
            return None
        model_id = id(self.predictor.model) if (self.predictor and self.predictor.model) else None
        feat_tuple = tuple(seg.canonical_features.get(f) for f in CANONICAL_PREDICTOR_FEATURES)
        return (model_id, seg_id, feat_tuple)

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

        # Batch ML inference with segment-level score & attribution caching
        try:
            uncached_items: List[Tuple[int, MatchedSegmentResult]] = []
            for item in eligible_items:
                cache_key = self._compute_segment_cache_key(item[1])
                if not cache_key or cache_key not in self._segment_score_cache:
                    uncached_items.append(item)

            if uncached_items:
                uncached_feature_dicts = [seg.canonical_features for _, seg in uncached_items]
                uncached_df = pd.DataFrame(uncached_feature_dicts)[CANONICAL_PREDICTOR_FEATURES]
                uncached_preds = self.predictor.predict_segments(uncached_df)
                uncached_expls = self.predictor.explain_segments(uncached_df)

                # Extract raw contribution vectors and base value for route TreeSHAP aggregation
                raw_contribs = None
                base_vals = None
                if (
                    self.predictor.model is not None
                    and hasattr(self.predictor.model, "booster_")
                    and self.predictor.preprocessor is not None
                ):
                    try:
                        X_uncached = self.predictor.preprocessor.transform(uncached_df)
                        full_contrib = self.predictor.model.booster_.predict(X_uncached, pred_contrib=True)
                        raw_contribs = full_contrib[:, :-1]
                        base_vals = full_contrib[:, -1]
                    except Exception as ce:
                        logger.debug(f"Direct raw contribution extraction failed: {ce}")

                for u_idx, (_, seg) in enumerate(uncached_items):
                    cache_key = self._compute_segment_cache_key(seg)
                    if cache_key:
                        p_val = float(uncached_preds[u_idx])
                        e_val = copy.deepcopy(uncached_expls[u_idx]) if uncached_expls and u_idx < len(uncached_expls) and uncached_expls[u_idx] is not None else None
                        c_val = raw_contribs[u_idx].copy() if raw_contribs is not None and u_idx < len(raw_contribs) and raw_contribs[u_idx] is not None else None
                        b_val = float(base_vals[u_idx]) if base_vals is not None and u_idx < len(base_vals) and base_vals[u_idx] is not None else None

                        # Bounded cache eviction (max 50,000 segments)
                        if len(self._segment_score_cache) >= 50000:
                            self._segment_score_cache.popitem(last=False)
                        self._segment_score_cache[cache_key] = (p_val, e_val, c_val, b_val)

            # Reconstruct predictions, explanations, and raw contribution matrix in exact eligible_items order
            predictions: List[float] = []
            explanations: List[Any] = []
            raw_contrib_rows: List[np.ndarray] = []
            base_val_candidate: Optional[float] = None

            for _, seg in eligible_items:
                cache_key = self._compute_segment_cache_key(seg)
                if cache_key and cache_key in self._segment_score_cache:
                    p_val, e_val, c_val, b_val = self._segment_score_cache[cache_key]
                    self._segment_score_cache.move_to_end(cache_key)
                    # Defensive copies to prevent downstream operations from corrupting cached values
                    e_val = copy.deepcopy(e_val) if e_val is not None else None
                    c_val = c_val.copy() if c_val is not None else None
                else:
                    df_single = pd.DataFrame([seg.canonical_features])[CANONICAL_PREDICTOR_FEATURES]
                    p_val = float(self.predictor.predict_segments(df_single)[0])
                    e_expl = self.predictor.explain_segments(df_single)
                    e_val = copy.deepcopy(e_expl[0]) if e_expl else None
                    c_val = None
                    b_val = None

                predictions.append(p_val)
                explanations.append(e_val)
                if c_val is not None:
                    raw_contrib_rows.append(c_val)
                if b_val is not None and base_val_candidate is None:
                    base_val_candidate = b_val

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
                    base_val = base_val_candidate if base_val_candidate is not None else float(explanations[0]["base_value"])
                    
                    if len(raw_contrib_rows) == len(eligible_items):
                        raw_contrib_matrix = np.array(raw_contrib_rows, dtype=np.float64)
                    else:
                        feature_dicts = [seg.canonical_features for _, seg in eligible_items]
                        batch_df = pd.DataFrame(feature_dicts)[CANONICAL_PREDICTOR_FEATURES]
                        X_trans = self.predictor.preprocessor.transform(batch_df)
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
                    leg_with_idx = dict(leg)
                    leg_with_idx["_dynamic_seg_idx"] = leg_idx
                    road_legs.append(leg_with_idx)
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
            leg_matches_dict = match_res.diagnostics.get("leg_matches", {}) if match_res and hasattr(match_res, "diagnostics") and isinstance(match_res.diagnostics, dict) else {}
            for s_idx, d_seg in enumerate(dynamic_segs):
                s_mode = str(d_seg.get("mode", "")).lower().strip()
                s_geom = d_seg.get("geometry", {})
                
                # Check if road-compatible
                if any(m in s_mode for m in ["auto", "cab", "walk", "bike", "two_wheeler", "driving", "personal"]):
                    try:
                        seg_match = leg_matches_dict.get(s_idx)
                        if seg_match is not None:
                            seg_match = seg_match.model_copy(deep=True)
                        else:
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
        # Pre-warm spatial index for combined corridor across all candidate routes
        try:
            all_journey_coords = []
            for cand in candidate_routes:
                c_meta = getattr(cand, "route_metadata", {}) or {}
                dyn = c_meta.get("dynamic_segments")
                if dyn and isinstance(dyn, list):
                    for leg in dyn:
                        g = leg.get("geometry")
                        if isinstance(g, dict) and "coordinates" in g:
                            all_journey_coords.extend(g["coordinates"])
                        elif isinstance(g, (list, tuple)):
                            all_journey_coords.extend(g)
                g = c_meta.get("geometry") or getattr(cand, "geometry", None)
                if isinstance(g, dict) and "coordinates" in g:
                    all_journey_coords.extend(g["coordinates"])
                elif isinstance(g, (list, tuple)):
                    all_journey_coords.extend(g)
            valid_coords = [c for c in all_journey_coords if isinstance(c, (list, tuple)) and len(c) >= 2]
            if valid_coords and hasattr(self.spatial_matcher, "_ensure_index_for_corridor"):
                self.spatial_matcher._ensure_index_for_corridor(valid_coords)
        except Exception as e:
            logger.debug(f"Candidate corridor pre-warming notice: {e}")

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
