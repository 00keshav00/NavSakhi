from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.api.exceptions import ProviderNotConfiguredError

class NotificationTool(BaseTool):
    @property
    def name(self) -> str:
        return "NotificationTool"

    @property
    def description(self) -> str:
        return "Sends emergency or alert notifications via configured providers."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Notification",
            required_inputs=["message", "recipients"],
            output_schema={"type": "dict", "properties": {"status": "string"}},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects: 'contacts' (list), 'message', 'type'
        """
        raise ProviderNotConfiguredError("NotificationProvider")
