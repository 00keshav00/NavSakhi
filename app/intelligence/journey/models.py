from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.models.journey import JourneyStateEnum, TransportMode, CandidateRoute, Location, ActiveAlert, JourneySegment, JourneyProgress

class JourneyContext(BaseModel):
    """
    Shared context model passed throughout the Journey Intelligence Layer.
    """
    journey_id: Optional[str] = None
    user_id: Optional[str] = None
    current_gps: Optional[Location] = None
    source: Optional[Location] = None
    destination: Optional[Location] = None
    current_segment_id: Optional[str] = None
    transport_mode: TransportMode = TransportMode.WALK
    state: JourneyStateEnum = JourneyStateEnum.CREATED
    timestamp: str
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JourneyEvent(BaseModel):
    """
    Represents runtime events entering the Intelligence Layer.
    """
    event_type: str
    context: JourneyContext
    payload: Dict[str, Any] = Field(default_factory=dict)

class RouteEvaluation(BaseModel):
    """
    Internal intelligence model representing an aggregated evaluated route.
    """
    candidate_route: CandidateRoute
    overall_score: float = 0.0
    evaluator_scores: Dict[str, float] = Field(default_factory=dict)
    evaluation_metadata: Dict[str, Any] = Field(default_factory=dict)

class JourneyRecommendation(BaseModel):
    """
    Internal intelligence model representing the final recommendation.
    """
    recommended_route: CandidateRoute
    confidence_score: float = 1.0
    explainability_metrics: Dict[str, Any] = Field(default_factory=dict)
    alternative_routes: List[CandidateRoute] = Field(default_factory=list)
    reasoning: str = ""

class MonitoringResult(BaseModel):
    """
    Internal intelligence model representing the outcome of a monitoring cycle.
    """
    alerts: List[ActiveAlert] = Field(default_factory=list)
    progress_updates: Optional[JourneyProgress] = None
    segment_updates: Optional[JourneySegment] = None
    state_transitions: Optional[JourneyStateEnum] = None
    reroute_required: bool = False
    completion_info: Dict[str, Any] = Field(default_factory=dict)
    monitoring_status: str = "monitoring_completed"
    metadata: Dict[str, Any] = Field(default_factory=dict)
