from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class EmergencyTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedEmergencyTool"

    @property
    def description(self) -> str:
        return "Specialized tool for emergency services."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Emergency",
            required_inputs=["user_id", "location"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "data": {"emergency_alert": "dispatched"}}
