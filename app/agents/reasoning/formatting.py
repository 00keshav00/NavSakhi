from typing import Dict, Any
from app.agents.reasoning.models import DecisionNode
from app.agents.reasoning.explanation import ExplanationGenerator

class StructuredOutputGenerator:
    """
    Maps the validated decision to the expected domain response models.
    """
    def generate(self, decision: DecisionNode) -> Dict[str, Any]:
        """
        Structures the raw decision into a dictionary ready for API responses or downstream agents.
        """
        return {
            "outcome_id": decision.outcome_id,
            "description": decision.description,
            "confidence_score": decision.confidence_score,
            "metadata": decision.metadata
        }

class ResponseFormatter:
    """
    The final presentation layer mapping output to API schemas.
    """
    def __init__(self):
        self.explanation_generator = ExplanationGenerator()
        
    def format_response(self, decision: DecisionNode, structured_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combines structured output with human-readable explanations.
        """
        return {
            "data": structured_output,
            "explanation": self.explanation_generator.generate(decision)
        }
