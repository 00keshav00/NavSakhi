from typing import List
from app.agents.context import ExecutionContext

class InformationRequirementAnalyzer:
    """
    Determines what information is required to satisfy the extracted goals.
    This step maps goals to required capabilities, not concrete tools.
    """
    def analyze(self, context: ExecutionContext, goals: List[str]) -> List[str]:
        requirements = []
        for goal in goals:
            goal_lower = goal.lower()
            if "route" in goal_lower:
                requirements.extend(["Routing", "Geospatial Analysis"])
            if "safety" in goal_lower or "safest" in goal_lower:
                requirements.extend(["Safety Prediction", "Community Intelligence", "Weather Retrieval", "Crowd Estimation"])
            if "emergency" in goal_lower or "authorities" in goal_lower:
                requirements.extend(["Geospatial Analysis", "Notification"])
            if "monitor" in goal_lower or "risks" in goal_lower:
                requirements.extend(["Routing", "Community Intelligence", "Weather Retrieval"])

        # Return unique capabilities
        return list(dict.fromkeys(requirements))
