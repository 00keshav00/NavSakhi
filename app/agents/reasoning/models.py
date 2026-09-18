from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DecisionNode(BaseModel):
    """
    Represents a specific outcome or decision path.
    """
    outcome_id: str
    description: str
    confidence_score: float = 0.0
    reasoning_trace: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReasoningState(BaseModel):
    """
    The deterministic state of reasoning during an agent's evaluation cycle.
    """
    execution_id: str
    context: Dict[str, Any]
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    alternatives: List[DecisionNode] = Field(default_factory=list)
    selected_decision: Optional[DecisionNode] = None
    is_validated: bool = False
