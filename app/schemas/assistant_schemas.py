from pydantic import BaseModel
from typing import List, Optional

class AgentStatus(BaseModel):
    status: str
    current_task: str

class ReasoningContext(BaseModel):
    summary: List[str]
    confidence: float
    decision_source: str
    provider_summary: str

class JourneyContextState(BaseModel):
    active_journey: bool
    source: Optional[str] = None
    destination: Optional[str] = None
    safety_score: Optional[float] = None
    eta: Optional[str] = None
    weather: Optional[str] = None
    community_alerts: Optional[int] = None
    emergency_status: Optional[str] = None

class ProviderHealthStatus(BaseModel):
    name: str
    status: str

class MemoryState(BaseModel):
    recent_journeys: List[str]
    pinned_info: List[str]

class AssistantResponse(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: str
    agent_status: AgentStatus
    reasoning: ReasoningContext
    context: JourneyContextState
    provider_health: List[ProviderHealthStatus]
    memory: MemoryState
    quick_suggestions: List[str]
