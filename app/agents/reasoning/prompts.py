from typing import Dict, Any

class PromptBuilder:
    """
    Dynamically structures the finalized context into deterministic prompt schemas.
    NOTE: Replaces the legacy app/agents/prompts/templates.py
    """
    def build_prompt(self, reasoning_context: Dict[str, Any]) -> str:
        """
        Builds a structured string/schema ready for an LLM (without executing one).
        """
        prompt = f"Goal: {reasoning_context.get('goal')}\n"
        prompt += f"Identity: {reasoning_context.get('agent_identity')}\n"
        
        prompt += "\nEvidence:\n"
        for ev in reasoning_context.get("evidence", []):
            prompt += f"- {ev.get('source_tool')}: {ev.get('data')}\n"
            
        prompt += "\nConstraints:\n"
        for k, v in reasoning_context.get("constraints", {}).items():
            prompt += f"- {k}: {v}\n"
            
        return prompt
