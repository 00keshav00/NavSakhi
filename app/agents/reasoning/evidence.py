from typing import Dict, Any, List
from app.agents.context import ExecutionContext

class EvidenceCollector:
    """
    Gathers results from the Tool Manager execution and converts them into structured evidence.
    """
    def collect(self, execution_results: List[Dict[str, Any]], context: ExecutionContext) -> List[Dict[str, Any]]:
        """
        Parses raw execution results into structured evidence items.
        """
        evidence_list = []
        for result in execution_results:
            evidence_item = {
                "source_tool": result.get("tool_name", "unknown"),
                "status": result.get("status", "unknown"),
                "data": result.get("data", {}),
                "timestamp": result.get("timestamp", None)
            }
            evidence_list.append(evidence_item)
            # Optionally store back into context collected evidence
            context.collected_evidence[evidence_item["source_tool"]] = evidence_item
        return evidence_list
