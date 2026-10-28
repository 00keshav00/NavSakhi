from pydantic import BaseModel, Field
from typing import List, Optional

class AgentStatus(BaseModel):
    status: str
    current_task: str

class ReasoningContext(BaseModel):
    summary: List[str]
    confidence: Optional[float] = None
    decision_source: str
    provider_summary: str
    response_source: Optional[str] = None  # "gemini" | "fallback" | "rule_based"
    intent_category: Optional[str] = None
    gemini_attempted: Optional[bool] = None
    model_identifier: Optional[str] = None
    attempt_count: Optional[int] = None
    provider_latency_ms: Optional[float] = None
    outcome_category: Optional[str] = None  # "success" | "rate_limited" | "timeout" | "invalid_response" | "unavailable" | "skipped"
    correlation_id: Optional[str] = None
    last_failed_model: Optional[str] = None
    failed_model_candidates: List[str] = Field(default_factory=list)
    safety_blocked_candidate: Optional[str] = None

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
    response_source: Optional[str] = None
