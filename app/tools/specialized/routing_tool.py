from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.routing import RoutingTool as CoreRoutingTool

class RoutingTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedRoutingTool"

    @property
    def description(self) -> str:
        return "Specialized tool for route calculations."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Routing",
            required_inputs=["source", "destination"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreRoutingTool()
        return await tool.execute(params)
