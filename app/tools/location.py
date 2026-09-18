from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class LocationTool(BaseTool):
    @property
    def name(self) -> str:
        return "LocationTool"

    @property
    def description(self) -> str:
        return "Resolves user coordinates or performs geocoding."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Geocoding",
            required_inputs=[],
            output_schema={"type": "dict"},
            ranking_score=6
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.providers.real.location import NominatimProvider
        provider = NominatimProvider()
        return await provider.get_current_location(user_id=params.get("user_id", ""))
