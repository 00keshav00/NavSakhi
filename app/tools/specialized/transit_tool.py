from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class TransitTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedTransitTool"

    @property
    def description(self) -> str:
        return "Specialized tool for transit schedules."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Transit",
            required_inputs=["location"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "data": {"transit_options": []}}
