from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    """Status of spatial snapping for a route segment."""
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"


class FeatureStatus(str, Enum):
    """Readiness status of the canonical ML feature row for a matched segment."""
    AVAILABLE = "AVAILABLE"
    MISSING_ROW = "MISSING_ROW"
    INCOMPLETE = "INCOMPLETE"
    INVALID_VALUES = "INVALID_VALUES"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MatchedSegmentResult(BaseModel):
    """Audit and downstream record for a road segment matched along a route."""
    traversal_index: int = Field(..., description="0-indexed position in route traversal order")
    leg_index: int = Field(0, description="0-indexed route leg or multimodal stage")
    segment_id: Optional[str] = Field(None, description="Authoritative 16-character hex segment identifier")
    way_id: Optional[int] = Field(None, description="Parent OSM way identifier")
    road_type: Optional[str] = Field(None, description="OSM highway classification")
    match_status: MatchStatus = Field(..., description="Spatial matching status")
    match_method: str = Field(..., description="Algorithm used (e.g., 'strtree_metric_proximity', 'heading_aligned_proximity')")
    match_distance_m: Optional[float] = Field(None, description="Displacement distance in meters between route and reference segment")
    heading_delta_deg: Optional[float] = Field(None, description="Angular heading divergence in degrees, if available")
    route_start_m: float = Field(0.0, description="Starting distance along the route polyline in meters")
    route_end_m: float = Field(0.0, description="Ending distance along the route polyline in meters")
    ambiguity_candidates: List[str] = Field(default_factory=list, description="Candidate segment_ids when match_status is AMBIGUOUS")
    feature_status: FeatureStatus = Field(FeatureStatus.NOT_APPLICABLE, description="Readiness status of canonical predictor features")
    canonical_features: Optional[Dict[str, Any]] = Field(None, description="The 41 canonical predictor features if feature_status is AVAILABLE")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Audit and validation diagnostics")


class UnmatchedInterval(BaseModel):
    """Portion of route that could not be matched to a reference road segment."""
    start_distance_m: float = Field(..., description="Offset in meters from route origin")
    end_distance_m: float = Field(..., description="Offset in meters from route origin")
    length_m: float = Field(..., description="Length of unmatched interval in meters")
    reason: str = Field(..., description="Reason: NO_CANDIDATE_WITHIN_THRESHOLD or AMBIGUOUS_CONFLICT")
    leg_index: int = Field(0, description="Route leg index")


class RouteCoverageMetrics(BaseModel):
    """Spatial coverage metrics for a matched route."""
    total_route_length_m: float = Field(..., description="Total length of the route in meters (projected metric CRS)")
    matched_length_m: float = Field(..., description="Total length of matched route portions in meters")
    unmatched_length_m: float = Field(..., description="Total length of unmatched route portions in meters")
    coverage_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of matched length to total length [0.0, 1.0]")
    total_samples: int = Field(..., description="Number of discrete points evaluated along route")
    matched_samples: int = Field(..., description="Number of points that resolved to a matched segment")
    unmatched_samples: int = Field(..., description="Number of points with no nearby road within threshold")
    ambiguous_samples: int = Field(..., description="Number of points with conflicting candidates")


class RouteSpatialMatchResponse(BaseModel):
    """Complete response from the spatial matching service for a route."""
    route_identifier: str = Field(..., description="Unique route identifier")
    travel_mode: str = Field("Road", description="Travel mode (e.g., Road, Multimodal, Walk)")
    status: str = Field(..., description="Overall match status: SUCCESS, PARTIAL, or FAILED")
    coverage: RouteCoverageMetrics = Field(..., description="Route coverage statistics")
    matched_segments: List[MatchedSegmentResult] = Field(default_factory=list, description="Ordered road segments in traversal sequence")
    unmatched_intervals: List[UnmatchedInterval] = Field(default_factory=list, description="Unmatched sections along the route")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Diagnostics, coordinate checks, and index metadata")


class ScoreStatus(str, Enum):
    """Readiness status for ML route safety scoring."""
    READY = "READY"
    INSUFFICIENT_COVERAGE = "INSUFFICIENT_COVERAGE"
    NO_SCOREABLE_SEGMENTS = "NO_SCOREABLE_SEGMENTS"
    FEATURE_DATA_UNAVAILABLE = "FEATURE_DATA_UNAVAILABLE"
    INFERENCE_ERROR = "INFERENCE_ERROR"
    UNSUPPORTED_GEOGRAPHY = "UNSUPPORTED_GEOGRAPHY"


class SegmentScoringResult(BaseModel):
    """Scoring audit record for a single segment traversal along a route."""
    traversal_index: int = Field(..., description="0-indexed position in route traversal sequence")
    leg_index: int = Field(0, description="0-indexed route leg")
    segment_id: Optional[str] = Field(None, description="Authoritative 16-character hex segment identifier")
    span_length_m: float = Field(..., description="Traversal span length in meters represented by this segment")
    safety_score: Optional[float] = Field(None, description="Frozen LightGBM predicted environmental safety proxy [0-100]")
    match_status: MatchStatus = Field(..., description="Spatial match status")
    feature_status: FeatureStatus = Field(..., description="Feature table readiness status")
    is_scoreable: bool = Field(..., description="True if segment was included in length-weighted score aggregation")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Segment diagnostics")


class RouteScoreResult(BaseModel):
    """Result of genuine ML inference and traversal-length-weighted score aggregation for a route."""
    route_identifier: str = Field(..., description="Route identifier")
    travel_mode: str = Field("Road", description="Travel mode category")
    safety_score: Optional[float] = Field(None, description="Traversal-length-weighted safety proxy score (None if not READY)")
    score_status: ScoreStatus = Field(..., description="Score readiness status")
    scoreable_length_m: float = Field(0.0, description="Total length of validly scored road sections in meters")
    total_route_length_m: float = Field(0.0, description="Total length of route in meters")
    scoreable_coverage_ratio: float = Field(0.0, ge=0.0, le=1.0, description="Ratio of scoreable length to total route length")
    min_coverage_threshold: float = Field(0.70, description="Configured minimum coverage ratio required for READY status")
    score_basis: str = Field("matched_road_segments_only", description="Scope basis of the score")
    is_synthetic_proxy: bool = Field(True, description="Indicates score is a synthetic proxy, not ground-truth crime")
    model_version: str = Field("2.0.0", description="Frozen model version")
    target_disclosure: str = Field(
        "Synthetic environmental safety proxy (100.0 - risk_score_raw); not verified crime or victimization ground truth.",
        description="Scientific and legal target disclosure"
    )
    scored_segments: List[SegmentScoringResult] = Field(default_factory=list, description="All segment traversals with scores")
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="Audit diagnostics, batch counts, and timing")

