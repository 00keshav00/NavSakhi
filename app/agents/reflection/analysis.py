from typing import Dict, Any, Tuple
from app.agents.reasoning.models import ReasoningState

class OutcomeAnalyzer:
    """
    Evaluates the ReasoningState to determine if the execution met its objectives.
    """
    def analyze(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        Returns (is_success, reason).
        """
        if not state:
            return False, "No reasoning state provided."
            
        if not state.is_validated:
            return False, "Reasoning state failed validation."
            
        if not state.selected_decision:
            return False, "No decision was selected during reasoning."
            
        # Example condition: If confidence is high enough, consider it a success.
        # This mirrors real analysis of the result quality.
        if state.selected_decision.confidence_score >= 0.5:
            return True, "Execution succeeded with high confidence."
            
        return False, "Execution succeeded but with low confidence."

class SuccessEvaluator:
    """
    Validates successful paths and extracts positive baseline metrics.
    """
    def evaluate(self, state: ReasoningState) -> str:
        if state.selected_decision:
            return f"Successful execution of {state.selected_decision.outcome_id} with score {state.selected_decision.confidence_score}."
        return "Unknown success path."
