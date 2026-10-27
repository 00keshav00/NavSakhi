from typing import Dict, Any, Optional, List, Tuple
import logging
from app.tools.base import BaseTool, ToolMetadata
from app.services.poi_service import get_poi_service

logger = logging.getLogger(__name__)

class POITool(BaseTool):
    """
    Specialized tool providing grounded retrieval of verified public facilities
    and mapped commercial establishments from the unified Chennai POI spatial dataset.
    """
    @property
    def name(self) -> str:
        return "SpecializedPOITool"

    @property
    def description(self) -> str:
        return "Queries verified public facilities and commercial establishments mapped in Chennai."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="POIQuery",
            required_inputs=[],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a POI query given:
        - lon, lat (and optional radius_m, category, max_results)
        - OR place / location_name (geocoded to lon, lat)
        - OR corridor_coords (list of [lon, lat] pairs)
        """
        poi_service = get_poi_service()
        lon = params.get("lon")
        lat = params.get("lat")
        category = params.get("category")
        radius_m = float(params.get("radius_m") or 1200.0)
        max_results = int(params.get("max_results") or 15)

        corridor_coords = params.get("corridor_coords")
        if corridor_coords and isinstance(corridor_coords, list):
            return poi_service.query_pois_near_route(
                corridor_coords,
                corridor_m=radius_m
            )

        place = params.get("place") or params.get("location_name")
        if (lon is None or lat is None) and place:
            resolved = await self.resolve_place(place)
            if resolved:
                lon, lat = resolved

        if lon is None or lat is None:
            return {
                "pois": [],
                "status": "LOCATION_MISSING",
                "total_found": 0,
                "disclosure": "Location coordinates or place name required to query nearby establishments."
            }

        return poi_service.query_pois_near_point(
            float(lon),
            float(lat),
            radius_m=radius_m,
            category=category,
            max_results=max_results
        )

    async def resolve_place(self, place_name: str) -> Optional[Tuple[float, float]]:
        """Resolves common Chennai neighborhoods and places into (lon, lat) coordinates."""
        if not place_name or not isinstance(place_name, str):
            return None

        CHENNAI_HUBS: Dict[str, Tuple[float, float]] = {
            "t nagar": (80.2337, 13.0418),
            "t. nagar": (80.2337, 13.0418),
            "thyagaraya nagar": (80.2337, 13.0418),
            "adyar": (80.2570, 13.0012),
            "guindy": (80.2184, 13.0067),
            "central": (80.2757, 13.0827),
            "chennai central": (80.2757, 13.0827),
            "egmore": (80.2611, 13.0784),
            "velachery": (80.2180, 12.9815),
            "marina": (80.2824, 13.0500),
            "marina beach": (80.2824, 13.0500),
            "anna nagar": (80.2120, 13.0850),
            "mylapore": (80.2680, 13.0330),
            "tambaram": (80.1200, 12.9249),
            "alwarpet": (80.2520, 13.0330),
            "triplicane": (80.2740, 13.0580),
            "nungambakkam": (80.2410, 13.0580),
            "kodambakkam": (80.2240, 13.0520),
            "thiruvanmiyur": (80.2590, 12.9830),
            "porur": (80.1580, 13.0380),
            "koyambedu": (80.1930, 13.0690),
            "besant nagar": (80.2670, 13.0000),
            "saidapet": (80.2220, 13.0210),
            "chromepet": (80.1440, 12.9510),
            "vit chennai": (80.1554, 12.8406),
            "vit": (80.1554, 12.8406),
            "kandigai": (80.1450, 12.8360),
            "panagal park": (80.2337, 13.0418),
        }
        cleaned = place_name.strip().lower()
        for hub, coords in CHENNAI_HUBS.items():
            if hub == cleaned or hub in cleaned or cleaned in hub:
                return coords

        try:
            from app.providers.location.provider import LocationProvider
            provider = LocationProvider()
            loc = await provider.forward_geocode(place_name)
            if loc and loc.coordinates and len(loc.coordinates) >= 2:
                return (loc.coordinates[0], loc.coordinates[1])
        except Exception as e:
            logger.debug(f"Forward geocode fallback error for '{place_name}': {e}")
        return None
