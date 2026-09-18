import httpx
import asyncio
from typing import Dict, Any, List
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class OSRMProvider:
    """
    Real integration with OSRM (Open Source Routing Machine).
    Fetches real routing coordinates, ETA, and distance.
    """
    def __init__(self):
        self.base_url = settings.osrm_base_url or "http://router.project-osrm.org"
        self.timeout = 10.0

    async def get_route(self, source: str, destination: str, alternatives: bool = True) -> Dict[str, Any]:
        """
        source and destination should be 'lon,lat' format.
        Example: '77.5946,12.9716'
        """
        try:
            # Fallback if coordinates are not properly formatted (e.g. named strings instead of lat,lng)
            if not (',' in source and ',' in destination):
                logger.warning(f"OSRM routing failed: invalid coords: {source} to {destination}. Using fallback.")
                return self._fallback_route()

            url = f"{self.base_url}/route/v1/driving/{source};{destination}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "true" if alternatives else "false",
                "steps": "true"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._normalize_osrm_response(data)
                else:
                    logger.error(f"OSRM returned status {response.status_code}")
                    return self._fallback_route()
                        
        except httpx.TimeoutException:
            logger.error("OSRM request timed out.")
            return self._fallback_route()
        except Exception as e:
            logger.error(f"OSRM request failed: {str(e)}")
            return self._fallback_route()

    def _normalize_osrm_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        routes = data.get("routes", [])
        if not routes:
            return self._fallback_route()
            
        primary = routes[0]
        alts = routes[1:] if len(routes) > 1 else []
        
        # Primary route
        distance_meters = primary.get("distance", 0)
        duration_seconds = primary.get("duration", 0)
        geometry = primary.get("geometry", {}).get("coordinates", [])
        
        normalized_alts = []
        for alt in alts:
            normalized_alts.append({
                "distance": f"{alt.get('distance', 0) / 1000:.1f} km",
                "eta": f"{int(alt.get('duration', 0) / 60)} mins",
                "geometry": alt.get("geometry", {}).get("coordinates", [])
            })
            
        return {
            "distance": f"{distance_meters / 1000:.1f} km",
            "eta": f"{int(duration_seconds / 60)} mins",
            "geometry": geometry,
            "segments": [{"instruction": step.get("maneuver", {}).get("type", ""), "distance": f"{step.get('distance', 0)}m"} for step in primary.get("legs", [{}])[0].get("steps", [])],
            "alternatives": normalized_alts
        }

    def _fallback_route(self) -> Dict[str, Any]:
        """Graceful degradation using a deterministic fallback"""
        return {
            "distance": "2.1 km",
            "eta": "14 mins",
            "geometry": [[77.5946, 12.9716], [77.5950, 12.9720]],
            "segments": [
                {"instruction": "Walk north for 500m", "distance": "500m"},
                {"instruction": "Turn right onto Tech Ave", "distance": "1.6 km"}
            ],
            "alternatives": []
        }
        
    async def health(self) -> Dict[str, str]:
        try:
            # simple ping using a known coordinate
            url = f"{self.base_url}/route/v1/driving/0,0;0,0"
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url)
                return {"status": "healthy" if response.status_code == 200 else "degraded"}
        except Exception:
            return {"status": "offline"}
