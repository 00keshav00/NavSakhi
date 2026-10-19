from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.community_tool import CommunityTool

class CommunityAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = CommunityTool()
        return await tool.execute({
            "route_geometry": context.get("route_geometry", [])
        })
