from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.community import CommunityTool as CoreCommunityTool

class CommunityTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedCommunityTool"

    @property
    def description(self) -> str:
        return "Specialized tool for community reports."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Community",
            required_inputs=["location"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreCommunityTool()
        return await tool.execute(params)
