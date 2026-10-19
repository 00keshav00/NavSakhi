from typing import Dict, Any, List
from app.agents.reasoning.models import DecisionNode

class AlternativeEvaluation:
    """
    Analyzes multiple evidence paths to generate potential decision alternatives.
    """
    def evaluate(self, reasoning_context: Dict[str, Any]) -> List[DecisionNode]:
        """
        Creates alternative decision nodes based on evidence.
        (Deterministic mock logic for this architecture milestone).
        """
        alternatives = []
        evidence_list = reasoning_context.get("evidence", [])
        
        if not evidence_list:
            alternatives.append(DecisionNode(
                outcome_id="fallback_01",
                description="No evidence available. Default fallback.",
                confidence_score=0.1,
                reasoning_trace=["Analyzed evidence.", "Found no data.", "Generated fallback."]
            ))
            return alternatives

        for i, ev in enumerate(evidence_list):
            alternatives.append(DecisionNode(
                outcome_id=f"alt_{i}",
                description=f"Action based on {ev.get('source_tool')}",
                confidence_score=0.5 + (0.1 * i),  # Mock deterministic score
                reasoning_trace=[f"Extracted {ev.get('source_tool')} data.", "Formulated alternative."],
                metadata=ev.get("data", {})
            ))
            
        return alternatives
