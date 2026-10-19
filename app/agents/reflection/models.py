from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class FailureClassification(BaseModel):
    category: str
    description: str
    is_recoverable: bool

class RecoveryPlan(BaseModel):
    strategy_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class ReflectionInsight(BaseModel):
    insight_type: str
    observation: str
    recommendation: str

class ExecutionOutcome(BaseModel):
    """
    Captures the full state of an execution after the Reasoning phase.
    """
    execution_id: str
    is_success: bool
    failure_classification: Optional[FailureClassification] = None
    recovery_plan: Optional[RecoveryPlan] = None
    insights: List[ReflectionInsight] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)
