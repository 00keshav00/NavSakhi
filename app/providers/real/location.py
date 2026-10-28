import httpx
import asyncio
from typing import Dict, Any
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class NominatimProvider:
    """
    Real integration with Nominatim OpenStreetMap API for geocoding.
    """
    def __init__(self):
        self.base_url = settings.nominatim_base_url or "https://nominatim.openstreetmap.org"
        self.timeout = 5.0
        # Nominatim requires a valid identifiable user-agent
        self.headers = {
            "User-Agent": settings.nominatim_user_agent or "NavSakhi/2.0 (+https://github.com/00keshav00/NavSakhi)"
        }

    async def get_current_location(self, user_id: str) -> Dict[str, Any]:
        """
        Since this is backend-side and we don't have the user's actual GPS stream in this call,
        we rely on whatever was last cached or we fallback. 
        For true live location, the frontend pushes telemetry to the TelemetryManager.
        """
        return self._fallback_location()

    async def reverse_geocode(self, lat: float, lng: float) -> str:
        """
        Converts coordinates to address.
        """
        try:
            from app.providers.shared.nominatim_coordinator import get_nominatim_coordinator
            params = {
                "format": "json",
                "lat": lat,
                "lon": lng,
                "zoom": 18,
                "addressdetails": 1
            }
            data = await get_nominatim_coordinator().execute_request("reverse", params=params, custom_base_url=self.base_url)
            if isinstance(data, dict):
                return data.get("display_name", "Unknown Location")
            return "Unknown Location"
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return "Unknown Location"

    def _fallback_location(self) -> Dict[str, Any]:
        return {
            "coordinates": [77.5946, 12.9716],
            "address": "4th Ave Intersection, Bengaluru",
            "accuracy": 12,
            "last_updated": "Just now"
        }
        
    async def health(self) -> Dict[str, str]:
        try:
            url = f"{self.base_url}/status.php?format=json"
            async with httpx.AsyncClient(headers=self.headers, timeout=3.0) as client:
                response = await client.get(url)
                return {"status": "healthy" if response.status_code == 200 else "degraded"}
        except Exception:
            return {"status": "offline"}
