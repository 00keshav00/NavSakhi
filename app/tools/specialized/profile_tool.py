from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.profile import ProfileTool as CoreProfileTool

class ProfileTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedProfileTool"

    @property
    def description(self) -> str:
        return "Specialized tool for profile data."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Profile",
            required_inputs=["user_id"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreProfileTool()
        return await tool.execute(params)
