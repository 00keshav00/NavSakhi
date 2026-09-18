from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.api.exceptions import ProviderNotConfiguredError

class GeospatialTool(BaseTool):
    @property
    def name(self) -> str:
        return "GeospatialTool"

    @property
    def description(self) -> str:
        return "Performs geospatial calculations (e.g. safe zones, geofencing)."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Geospatial Analysis",
            required_inputs=["coordinates"],
            output_schema={"type": "dict", "properties": {"in_safe_zone": "bool"}},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects: 'location', 'poi_type' (e.g., 'police', 'hospital')
        """
        raise ProviderNotConfiguredError("PlacesProvider")
