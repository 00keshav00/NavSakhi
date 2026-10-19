from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.profile_tool import ProfileTool

class ProfileAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = ProfileTool()
        return await tool.execute({
            "user_id": context.get("user_id")
        })
