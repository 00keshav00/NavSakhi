from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum
from app.models.base import MongoBaseModel
from app.models.base import PyObjectId

class TransportMode(str, Enum):
    CAB = "CAB"
    OWN_VEHICLE = "OWN_VEHICLE"
    WALK = "WALK"
    BUS = "BUS"
    METRO = "METRO"
    TRAIN = "TRAIN"
    BICYCLE = "BICYCLE"
    RIDE_SHARE = "RIDE_SHARE"

class JourneyStateEnum(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    REROUTING = "REROUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"

class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class Location(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]

class POI(BaseModel):
    name: str
    poi_type: str
    location: Location
    distance_meters: Optional[float] = None
    metadata: Dict[str, Any] = {}

class Address(BaseModel):
    display_name: str
    metadata: Dict[str, Any] = {}

class RoadInfo(BaseModel):
    road_type: str
    metadata: Dict[str, Any] = {}

class WeatherState(BaseModel):
    temperature: Optional[float] = None
    condition: str = "UNKNOWN"
    humidity: Optional[float] = None
    visibility: Optional[float] = None
    wind_speed: Optional[float] = None

class TransitSegment(BaseModel):
    mode: str
    start_station: str
    end_station: str
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class RouteCollection(BaseModel):
    items: List["CandidateRoute"]
    metadata: Dict[str, Any] = {}

class POICollection(BaseModel):
    items: List[POI]
    metadata: Dict[str, Any] = {}

class TransitCollection(BaseModel):
    items: List[TransitSegment]
    metadata: Dict[str, Any] = {}

class JourneyStateTransition(BaseModel):
    from_state: Optional[JourneyStateEnum] = None
    to_state: JourneyStateEnum
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class JourneyState(BaseModel):
    current_state: JourneyStateEnum = JourneyStateEnum.CREATED
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    state_history: List[JourneyStateTransition] = []

class JourneyScore(BaseModel):
    overall_score: Optional[float] = None
    safety_score: Optional[float] = None
    crowd_score: Optional[float] = None
    weather_score: Optional[float] = None
    confidence: Optional[float] = None

class SelectedRoute(BaseModel):
    route_identifier: str
    distance: float
    duration: float
    geometry_reference: str
    status: str
    safety_score: Optional[float] = None
    crowd_score: Optional[float] = None
    weather_score: Optional[float] = None

class CandidateRoute(BaseModel):
    route_identifier: str
    distance: float
    duration: float
    recommendation_status: str
    route_metadata: Dict[str, Any] = {}

class JourneySegment(BaseModel):
    segment_identifier: str
    transport_mode: TransportMode
    start_location: Location
    end_location: Location
    distance: float
    duration: float
    eta: Optional[datetime] = None
    progress: float = 0.0
    route_geometry: Optional[Any] = None
    status: str = "PENDING"
    safety_information: Dict[str, Any] = Field(default_factory=dict)
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)

class JourneyPlan(BaseModel):
    transport_mode: TransportMode
    selected_route: Optional[SelectedRoute] = None
    alternative_routes: List[CandidateRoute] = []
    recommended_route: Optional[str] = None
    journey_score: Optional[JourneyScore] = None
    weather_state: Optional[WeatherState] = None
    explanation: Optional[str] = None
    journey_segments: List[JourneySegment] = []

class JourneyProgress(BaseModel):
    current_segment: Optional[str] = None
    current_location: Optional[Location] = None
    distance_remaining: float = 0.0
    eta_remaining: float = 0.0
    progress_percentage: float = 0.0

class ActiveAlert(BaseModel):
    alert_identifier: str
    alert_type: str
    severity: str
    message: str
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: AlertStatus = AlertStatus.ACTIVE

class JourneyMetadata(BaseModel):
    created_by: Optional[str] = None
    updated_timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1.0"
    last_sync_timestamp: Optional[datetime] = None

class Journey(MongoBaseModel):
    # Basic Information
    user_id: PyObjectId
    source: Location
    destination: Location
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    started_timestamp: Optional[datetime] = None
    completed_timestamp: Optional[datetime] = None
    
    # Nested Hierarchies
    plan: Optional[JourneyPlan] = None
    state: JourneyState = Field(default_factory=JourneyState)
    progress: Optional[JourneyProgress] = None
    alerts: List[ActiveAlert] = []
    metadata: JourneyMetadata = Field(default_factory=JourneyMetadata)

class RecommendationExplanation(BaseModel):
    primary_reason: str
    tradeoffs: List[str] = []
    advantages: List[str] = []
    limitations: List[str] = []

class JourneyRecommendation(BaseModel):
    primary_route_id: Optional[str] = None
    safest_route_id: Optional[str] = None
    fastest_route_id: Optional[str] = None
    balanced_route_id: Optional[str] = None
    lowest_cost_route_id: Optional[str] = None
    explanation: Optional[RecommendationExplanation] = None
