from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.location import LocationTool as CoreLocationTool

class LocationTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedLocationTool"

    @property
    def description(self) -> str:
        return "Specialized tool for geocoding and location."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Location",
            required_inputs=[],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreLocationTool()
        return await tool.execute(params)
