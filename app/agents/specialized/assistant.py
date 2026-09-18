from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.reasoning_tool import ReasoningTool

class AssistantAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = ReasoningTool()
        return await tool.execute({
            "context": context
        })
