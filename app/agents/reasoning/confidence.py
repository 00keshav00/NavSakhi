from app.agents.reasoning.models import DecisionNode

class ConfidenceCalculator:
    """
    Computes a deterministic confidence score based on evidence reliability and fallback states.
    """
    def calculate(self, decision: DecisionNode) -> float:
        """
        Adjusts the initial confidence score based on structural checks.
        """
        score = decision.confidence_score
        
        # Deduct if reasoning trace is too shallow
        if len(decision.reasoning_trace) < 2:
            score -= 0.2
            
        # Ensure score stays within [0.0, 1.0]
        return max(0.0, min(1.0, score))
