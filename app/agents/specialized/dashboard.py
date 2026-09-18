from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.dashboard_tool import DashboardTool

class DashboardAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = DashboardTool()
        return await tool.execute({})
