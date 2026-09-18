from typing import List
from app.agents.context import ExecutionContext

class GoalExtractor:
    """
    Converts the user's unstructured request into one or more explicit, actionable goals.
    """
    def extract(self, context: ExecutionContext, intent: str) -> List[str]:
        # Without an LLM, we map the intent back to a structured objective.
        if intent == "Emergency Assistance":
            return ["Improve immediate user safety", "Locate nearby authorities"]
        elif intent == "Journey Planning":
            return ["Find the safest possible route from origin to destination"]
        elif intent == "Live Monitoring":
            return ["Detect emerging risks on active route"]
        else:
            return ["Provide accurate safety information"]
