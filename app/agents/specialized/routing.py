from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.routing_tool import RoutingTool

class RoutingAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = RoutingTool()
        return await tool.execute({
            "source": context.get("source"),
            "destination": context.get("destination")
        })
