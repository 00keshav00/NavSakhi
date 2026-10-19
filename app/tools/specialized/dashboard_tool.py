from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.dashboard import DashboardTool as CoreDashboardTool

class DashboardTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedDashboardTool"

    @property
    def description(self) -> str:
        return "Specialized tool for dashboard metrics."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Dashboard",
            required_inputs=[],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreDashboardTool()
        return await tool.execute(params)
