from typing import List, Optional
from app.agents.reasoning.models import DecisionNode

class DecisionGenerator:
    """
    Selects the primary outcome from the evaluated alternatives.
    """
    def generate(self, alternatives: List[DecisionNode]) -> Optional[DecisionNode]:
        """
        Selects the alternative with the highest confidence score.
        """
        if not alternatives:
            return None
            
        # Sort alternatives by confidence score in descending order
        sorted_alts = sorted(alternatives, key=lambda alt: alt.confidence_score, reverse=True)
        
        return sorted_alts[0]
