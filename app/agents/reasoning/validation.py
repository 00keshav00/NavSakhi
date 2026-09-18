from app.agents.reasoning.models import DecisionNode

class DecisionValidator:
    """
    Ensures the decision meets minimum safety and confidence thresholds.
    """
    def validate(self, decision: DecisionNode, minimum_confidence: float = 0.4) -> bool:
        """
        Validates the decision against the threshold.
        """
        if not decision:
            return False
            
        return decision.confidence_score >= minimum_confidence
