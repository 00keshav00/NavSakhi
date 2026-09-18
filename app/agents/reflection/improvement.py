from app.agents.reflection.models import ExecutionOutcome, ReflectionInsight

class SelfImprovementGenerator:
    """
    Synthesizes recommendations for capability or prompt tuning.
    """
    def generate(self, outcome: ExecutionOutcome) -> ReflectionInsight:
        """
        Analyzes the outcome and provides an improvement insight.
        """
        if outcome.is_success:
            return ReflectionInsight(
                insight_type="success_pattern",
                observation="Execution succeeded with standard pipeline.",
                recommendation="Maintain current capability mappings."
            )
        else:
            return ReflectionInsight(
                insight_type="failure_pattern",
                observation=f"Execution failed due to: {outcome.failure_classification.category if outcome.failure_classification else 'Unknown'}",
                recommendation="Review tool fallback capabilities or adjust confidence thresholds."
            )
