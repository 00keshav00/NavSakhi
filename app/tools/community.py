from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class CommunityTool(BaseTool):
    @property
    def name(self) -> str:
        return "CommunityTool"

    @property
    def description(self) -> str:
        return "Retrieves community incident reports and verified safe zones."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="CommunityReports",
            required_inputs=["route_geometry"],
            output_schema={"type": "dict", "properties": {"total_reports": "integer"}},
            ranking_score=7
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.providers.real.community import MongoCommunityProvider
        provider = MongoCommunityProvider()
        return await provider.get_community_reports(
            route_geometry=params.get("route_geometry", [])
        )
