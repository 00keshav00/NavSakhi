from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.transit_tool import TransitTool

class TransitAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = TransitTool()
        return await tool.execute({
            "source": context.get("source"),
            "destination": context.get("destination")
        })
