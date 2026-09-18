from app.agents.reasoning.models import ReasoningState
from app.agents.reflection.models import FailureClassification

class FailureClassifier:
    """
    Deterministically maps error conditions to known failure archetypes.
    """
    def classify(self, state: ReasoningState, reason: str) -> FailureClassification:
        """
        Classifies the failure based on the reasoning state and reason string.
        """
        if "validation" in reason.lower():
            return FailureClassification(
                category="ValidationFailure",
                description="The decision failed to meet the required confidence threshold.",
                is_recoverable=True
            )
            
        if "decision" in reason.lower():
            return FailureClassification(
                category="DecisionFailure",
                description="The reasoning engine could not generate a valid decision.",
                is_recoverable=True
            )
            
        return FailureClassification(
            category="UnknownFailure",
            description=reason,
            is_recoverable=False
        )
