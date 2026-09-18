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

class RouteSegment(BaseModel):
    segment_name: str = Field(..., description="e.g. Origin -> Metro Station")
    transport_mode: str = Field(..., description="Walking, Metro, Auto, etc.")
    polyline: Any = Field(..., description="GeoJSON Feature for this segment")
    color: str = Field(..., description="Hex color code for rendering")
    distance: str = Field(..., description="e.g. 1.2 km")
    eta: str = Field(..., description="e.g. 8 mins")
    environmental_risk: int = Field(0, description="Environmental risk score 0-100")
    adjusted_safety_score: str = Field(..., description="e.g. 46 / 100")
    reason: str = Field(..., description="Reason for the adjusted safety score")
    key_safety_observations: str = Field("", description="Backwards compatibility")
    safety_score: str = Field("", description="Backwards compatibility")

class MultimodalRoute(BaseModel):
    id: str = ""
    rank: int
    route_name: str = Field(..., description="e.g. Route A")
    travel_mode_chain: str = Field("", description="e.g. Walk -> Metro -> Auto")
    mode: str = Field(..., description="Overall mode category")
    eta: str
    cost: str
    distance: str
    environmental_risk: int = Field(0, description="Overall environmental risk")
    overall_safety_score: str = Field(..., description="e.g. 87/100")
    model_explainability: Dict[str, str] = Field(default_factory=dict, description="Feature contributions from ML model")
    recommendation_reason: List[str] = Field(default_factory=list, description="Why this route is recommended")
    strengths: List[str] = Field(default_factory=list, description="Backwards compatibility")
    weaknesses: List[str] = Field(default_factory=list, description="Backwards compatibility")
    segments: List[RouteSegment]
    is_recommended: bool = False
    ranking_labels: List[str] = []

class AIRecommendation(BaseModel):
    title: str
    summary: str
    confidence: int
    reasoning: str
    warnings: List[str]
    suggested_actions: List[str]

class SessionInfo(BaseModel):
    created_at: str
    status: str

class JourneyInformation(BaseModel):
    source: str
    destination: str
    distance: float
    estimated_duration: float

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
