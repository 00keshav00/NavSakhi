from typing import Dict, Any
from app.agents.context import ExecutionContext

class ConstraintDetector:
    """
    Identifies every condition that affects execution.
    Extracts User, Environmental, and Runtime constraints.
    """
    def detect(self, context: ExecutionContext) -> Dict[str, Any]:
        constraints = {}
        # Incorporate known constraints passed from the context
        if context.constraints:
            constraints.update(context.constraints)
            
        # Example dynamic extraction:
        goal = context.goal.lower()
        if "walking" in goal:
            constraints["transport_mode"] = "walking"
        if "night" in goal:
            constraints["time_of_day"] = "night"
            
        return constraints
