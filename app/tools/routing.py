from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class RoutingTool(BaseTool):
    @property
    def name(self) -> str:
        return "RoutingTool"

    @property
    def description(self) -> str:
        return "Calculates navigation routes from origin to destination."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Routing",
            required_inputs=["origin", "destination"],
            output_schema={"type": "dict", "properties": {"route_id": "string", "distance": "float"}},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects: 'source', 'destination'
        """
        from app.providers.real.routing import OSRMProvider
        provider = OSRMProvider()
        return await provider.get_route(
            source=params.get("source", ""),
            destination=params.get("destination", "")
        )
