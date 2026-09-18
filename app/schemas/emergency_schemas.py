from pydantic import BaseModel
from typing import Optional, List, Tuple

class SOSTrigger(BaseModel):
    current_location: str
    journey_id: Optional[str] = None

class SOSResponse(BaseModel):
    session_id: str

class EmergencyContact(BaseModel):
    id: str
    name: str
    relationship: str
    notification_status: str

class EmergencyTimelineEvent(BaseModel):
    id: str
    timestamp: str
    status: str
    description: str

class EmergencySafeZone(BaseModel):
    id: str
    type: str
    name: str
    distance: str
    eta: str
    coordinates: Tuple[float, float]

class LiveLocation(BaseModel):
    coordinates: Tuple[float, float]
    address: str
    accuracy: int
    last_updated: str

class AgentStatus(BaseModel):
    action: str
    recommendation: str
    context: str
    confidence: int
    reason: str

class JourneyStatus(BaseModel):
    active_journey: bool
    destination: str
    distance_remaining: str
    safety_score: int

class EmergencyResponse(BaseModel):
    session_id: str
    status: str
    live_location: LiveLocation
    agent_status: AgentStatus
    timeline: List[EmergencyTimelineEvent]
    contacts: List[EmergencyContact]
    safe_zones: List[EmergencySafeZone]
    journey_status: JourneyStatus
