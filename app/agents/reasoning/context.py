from typing import Dict, Any, List
from app.agents.context import ExecutionContext

class ContextBuilder:
    """
    Combines Memory Architecture context with collected evidence into a unified reasoning state.
    """
    def build(self, context: ExecutionContext, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds the comprehensive context dictionary.
        """
        built_context = {
            "goal": context.goal,
            "agent_identity": context.agent_identity,
            "memory": context.assembled_context,
            "evidence": evidence,
            "constraints": context.constraints
        }
        return built_context
