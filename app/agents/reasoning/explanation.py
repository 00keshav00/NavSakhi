from app.agents.reasoning.models import DecisionNode

class ExplanationGenerator:
    """
    Formulates a human-readable rationale for the decision.
    """
    def generate(self, decision: DecisionNode) -> str:
        """
        Converts the reasoning trace into a coherent explanation.
        """
        if not decision:
            return "No decision could be generated."
            
        explanation = f"Decision: {decision.description}\nRationale:\n"
        for step in decision.reasoning_trace:
            explanation += f"- {step}\n"
            
        return explanation
