from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.models.journey import (
    Location, 
    JourneyState,
    JourneyPlan,
    JourneyProgress,
    ActiveAlert,
    JourneyMetadata,
    TransportMode
)

class JourneyCreate(BaseModel):
    source: str
    destination: str
    preferences: Optional[List[str]] = None
    travel_time: Optional[str] = None

import math

class RouteSegment(BaseModel):
    leg_id: Optional[str] = Field(None, description="Stable unique leg identifier")
    sequence: Optional[int] = Field(None, description="Sequence order within the route (1-based)")
    segment_name: str = Field(..., description="e.g. Origin -> Metro Station")
    transport_mode: str = Field(..., description="Walking, Metro, Auto, etc.")
    polyline: Any = Field(..., description="GeoJSON Feature for this segment")
    color: str = Field(..., description="Hex color code for rendering")
    distance: str = Field(..., description="e.g. 1.2 km")
    eta: str = Field(..., description="e.g. 8 mins")
    environmental_risk: int = Field(0, description="Environmental risk score 0-100")
    adjusted_safety_score: Optional[float] = Field(None, description="Segment safety score [0-100] or null")
    reason: str = Field(..., description="Reason for the adjusted safety score")
    key_safety_observations: str = Field("", description="Backwards compatibility")
    safety_score: Optional[float] = Field(None, description="Segment safety score [0-100] or null")
    score_status: Optional[str] = Field(None, description="READY, NOT_SCORED, INSUFFICIENT_COVERAGE")
    scoreable_coverage_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="Coverage ratio")
    score_source: Optional[str] = Field(None, description="Scoring source or assessment model")
    score_disclosure: Optional[str] = Field(None, description="Truthful score provenance and limitation disclosure")
    distance_m: Optional[float] = Field(None, description="Exact distance in meters")
    duration_s: Optional[float] = Field(None, description="Exact duration in seconds")
    origin: Optional[str] = Field(None, description="Leg starting point / station name")
    destination: Optional[str] = Field(None, description="Leg arrival point / station name")
    geometry_complete: Optional[bool] = Field(True, description="Whether leg has verified network geometry")


class RoutePOI(BaseModel):
    """Verified safety facility record located along a route corridor."""
    poi_id: str = Field(..., description="Stable unique identifier for the facility")
    osm_id: Optional[int] = Field(None, description="OpenStreetMap element identifier")
    name: str = Field(..., description="Genuine facility name or category label")
    category: str = Field(..., description="Facility category (police, hospital, clinic, pharmacy, fire_station)")
    category_label: str = Field(..., description="Human-readable category title")
    latitude: float = Field(..., description="WGS84 latitude coordinate")
    longitude: float = Field(..., description="WGS84 longitude coordinate")
    distance_to_route_m: float = Field(..., description="Shortest orthogonal distance to route geometry in meters")
    nearest_route_leg_id: Optional[str] = Field(None, description="Identifier of the nearest journey leg")
    proximity_tier: str = Field("ALONG_CORRIDOR", description="IMMEDIATELY_BESIDE (<=100m) or ALONG_CORRIDOR")
    is_emergency: bool = Field(False, description="Whether facility provides emergency medical or rescue services")
    operator: Optional[str] = Field(None, description="Facility managing organization or authority")
    source: str = Field("OpenStreetMap (ODbL 1.0)", description="Authoritative data source and license")
    last_verified_at: Optional[str] = Field(None, description="Verification or dataset update timestamp")


class FeatureContributionItem(BaseModel):
    """Individual feature contribution to safety score proxy."""
    feature: str = Field(..., description="Clean feature title")
    raw_feature: Optional[str] = Field(None, description="Underlying transformed feature name")
    attribution: float = Field(..., description="Signed contribution value (+ increases safety score, - decreases)")
    direction: str = Field("SAFETY_ENHANCING", description="SAFETY_ENHANCING or RISK_INCREASING")


class RouteModelAttribution(BaseModel):
    """Authentic LightGBM TreeSHAP route-level feature attribution."""
    method: str = Field("LightGBM TreeSHAP (native pred_contrib, length-weighted traversal aggregation)")
    base_value: float = Field(..., description="Expected baseline score across training population")
    safety_score: Optional[float] = Field(None, description="Predicted safety proxy score [0, 100]")
    reconstructed_score: Optional[float] = Field(None, description="Sum of base value and all feature attributions")
    reconstruction_error: Optional[float] = Field(None, description="Absolute difference between model prediction and attribution sum")
    is_mathematically_reconstructed: bool = Field(True, description="True if error < 0.05")
    target: str = Field("safety_score (Synthetic Environmental Proxy [0, 100])")
    top_positive_factors: List[FeatureContributionItem] = Field(default_factory=list)
    top_negative_factors: List[FeatureContributionItem] = Field(default_factory=list)
    status: str = Field("VALIDATED_ATTRIBUTION", description="VALIDATED_ATTRIBUTION, UNAVAILABLE, or NOT_SCORED")


class RouteFare(BaseModel):
    """Structured fare and cost metadata distinguishing official, estimated, and unavailable prices."""
    fare_type: str = Field("FARE_UNAVAILABLE", description="OFFICIAL_FARE, ESTIMATED_FARE, FARE_UNAVAILABLE, NOT_APPLICABLE, METERED_VARIABLE")
    currency: Optional[str] = Field("INR", description="Currency ISO code")
    amount: Optional[float] = Field(None, description="Exact numerical amount if verified or estimated")
    display_text: str = Field(..., description="Display string e.g. '₹ 40' or 'Fare unavailable'")
    source_label: str = Field("", description="Authoritative source or limitation disclosure")
    is_official: bool = Field(False, description="True only when backed by authoritative published tariff")


class MultimodalRoute(BaseModel):
    id: str = ""
    rank: int
    route_name: str = Field(..., description="e.g. Route A")
    travel_mode_chain: str = Field("", description="e.g. Walk -> Metro -> Auto")
    mode: str = Field(..., description="Overall mode category")
    eta: str
    cost: str
    fare: Optional[RouteFare] = Field(None, description="Structured fare metadata")
    distance: str
    environmental_risk: int = Field(0, description="Overall environmental risk")
    safety_score: Optional[float] = Field(None, description="Traversal-length-weighted LightGBM safety proxy score [0-100] or null")
    overall_safety_score: Optional[float] = Field(None, description="Numeric safety score [0-100] or null (backward compatible)")
    model_explainability: Dict[str, str] = Field(default_factory=dict, description="Feature contributions from ML model (legacy string dict)")
    model_attribution: Optional[RouteModelAttribution] = Field(None, description="Genuine LightGBM TreeSHAP feature attribution")
    nearby_pois: List[RoutePOI] = Field(default_factory=list, description="Verified facilities within route corridor")
    recommendation_reason: List[str] = Field(default_factory=list, description="Why this route is recommended")
    strengths: List[str] = Field(default_factory=list, description="Backwards compatibility")
    segments: List[RouteSegment]
    is_recommended: bool = False
    ranking_labels: List[str] = []
    score_status: Optional[str] = Field(None, description="Score readiness status (READY, INSUFFICIENT_COVERAGE, etc.)")
    scoreable_coverage_ratio: Optional[float] = Field(None, ge=0.0, le=1.0, description="Ratio of route length with valid ML features")
    score_basis: Optional[str] = Field("matched_road_segments_only", description="Measurement basis for the safety score")
    model_version: Optional[str] = Field("2.0.0", description="Frozen model version")
    target_disclosure: Optional[str] = Field(
        "Synthetic environmental safety proxy (100.0 - risk_score_raw); not verified crime or victimization ground truth.",
        description="Target disclosure statement"
    )

    from pydantic import model_validator

    @model_validator(mode="after")
    def validate_score_consistency(self) -> "MultimodalRoute":
        status = self.score_status
        score = self.safety_score

        if status == "READY":
            if score is None or math.isnan(score) or math.isinf(score):
                raise ValueError("Route with READY status must have a finite numeric safety_score.")
            if not (0.0 <= score <= 100.0):
                raise ValueError(f"safety_score must be between 0.0 and 100.0, got {score}")
            if self.scoreable_coverage_ratio is not None and self.scoreable_coverage_ratio < 0.70:
                raise ValueError(f"Route with READY status must have coverage >= 0.70, got {self.scoreable_coverage_ratio}")
            # Keep overall_safety_score synchronized
            self.overall_safety_score = score
        elif status is not None:
            # Non-ready statuses (INSUFFICIENT_COVERAGE, NO_SCOREABLE_SEGMENTS, FEATURE_DATA_UNAVAILABLE, INFERENCE_ERROR, UNSUPPORTED_GEOGRAPHY)
            if score is not None:
                raise ValueError(f"Route with non-ready status '{status}' must have safety_score=None, got {score}")
            self.overall_safety_score = None

        if self.scoreable_coverage_ratio is not None:
            if math.isnan(self.scoreable_coverage_ratio) or math.isinf(self.scoreable_coverage_ratio):
                raise ValueError("scoreable_coverage_ratio must be a finite number.")
            if not (0.0 <= self.scoreable_coverage_ratio <= 1.0):
                raise ValueError(f"scoreable_coverage_ratio must be between 0.0 and 1.0, got {self.scoreable_coverage_ratio}")

        return self


class AIRecommendation(BaseModel):
    title: str
    summary: str
    confidence: Optional[float] = Field(None, description="Confidence metric (deprecated static placeholder omitted)")
    reasoning: str
    warnings: List[str]
    suggested_actions: List[str]

class SessionInfo(BaseModel):
    created_at: str
    status: str

class JourneyInformation(BaseModel):
    source: str
    destination: str
    distance: float = Field(..., ge=0.0, description="Total journey distance in meters")
    estimated_duration: float = Field(..., ge=0.0, description="Estimated duration in seconds")

class WeatherSummary(BaseModel):
    condition: str
    temperature: int
    hazards: List[str]

class CommunitySummary(BaseModel):
    reports_along_route: int
    severity_level: str

class JourneyPlanResponse(BaseModel):
    journey_id: str
    session_info: SessionInfo
    journey_information: JourneyInformation
    recommended_routes: List[MultimodalRoute]
    weather_summary: WeatherSummary
    community_summary: CommunitySummary
    alerts: List[str]
    ai_recommendation: AIRecommendation
    source_loc: Optional[List[float]] = None
    dest_loc: Optional[List[float]] = None
    zero_distance: Optional[bool] = False
    warnings: Optional[List[str]] = None

class JourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(default="")
    user_id: str = Field(default="")
    source: Location
    destination: Location
    created_timestamp: datetime
    started_timestamp: Optional[datetime] = None
    completed_timestamp: Optional[datetime] = None
    
    plan: Optional[JourneyPlan] = None
    state: JourneyState
    progress: Optional[JourneyProgress] = None
    alerts: List[ActiveAlert] = []
    metadata: JourneyMetadata
    
    from pydantic import model_validator
    
    @model_validator(mode="before")
    @classmethod
    def coerce_objectids(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "_id" in values and "id" not in values:
                values["id"] = values["_id"]
            for key in ("id", "user_id", "_id"):
                if key in values and values[key] is not None:
                    values[key] = str(values[key])
        return values

class LocationUpdate(BaseModel):
    location: Location
