from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

class AgentMessage(BaseModel):
    """
    Represents formal communication between agents.
    """
    message_id: str
    sender_id: str
    receiver_id: str
    intent: str
    payload: Dict[str, Any]
    timestamp: str

class CollaborationContext(BaseModel):
    """
    Shared state accessible by all agents within a session.
    """
    shared_memory: Dict[str, Any] = Field(default_factory=dict)
    resolved_conflicts: List[Dict[str, Any]] = Field(default_factory=list)

class CollaborationSession(BaseModel):
    """
    Tracks the state, involved agents, and shared context of a specific collaboration instance.
    """
    session_id: str
    initiator_id: str
    participants: List[str] = Field(default_factory=list)
    context: CollaborationContext = Field(default_factory=CollaborationContext)
    status: str = "active"
    history: List[AgentMessage] = Field(default_factory=list)
