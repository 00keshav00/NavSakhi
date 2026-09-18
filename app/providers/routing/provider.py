from typing import Dict, Any, List
from app.intelligence.journey.providers import RoutingProvider
from app.models.journey import Location, CandidateRoute
from app.providers.shared.http_client import SharedHTTPClient
from app.providers.shared.retry import with_retry
from app.providers.shared.cache import ProviderCache
from app.providers.shared.exceptions import ProviderResponseMappingError
from app.providers.routing.models import VendorRouteResponse
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class OSRMRoutingProvider(RoutingProvider):
    """
    Concrete implementation of RoutingProvider using OSRM.
    """
    def __init__(self):
        # Using SafeShe's existing configuration system
        self.base_url = settings.osrm_base_url or "http://router.project-osrm.org"
        self.http = SharedHTTPClient(timeout_ms=5000)

    @staticmethod
    def _map_to_domain(vendor_data: Dict[str, Any]) -> List[CandidateRoute]:
        try:
            response = VendorRouteResponse(**vendor_data)
            candidates = []
            for i, route in enumerate(response.routes):
                candidates.append(CandidateRoute(
                    route_identifier=f"vendor_route_{hash(str(route))}_{i}",
                    distance=route.get("distance", 0.0),
                    duration=route.get("duration", 0.0),
                    recommendation_status="PENDING",
                    route_metadata={"geometry": route.get("geometry")}
                ))
            return candidates
        except Exception as e:
            raise ProviderResponseMappingError(f"Failed to map route: {str(e)}")

    # Property allows the decorator to dynamically read from settings during class load if needed,
    # but since it's a decorator, we evaluate settings.routing_cache_ttl right now.
    @ProviderCache.cached(ttl_seconds=settings.routing_cache_ttl)
    @with_retry(max_retries=3, base_delay_ms=200)
    async def get_routes(self, source: Location, destination: Location, mode: str, alternatives: int = 3) -> List[CandidateRoute]:
        url = f"{self.base_url}/route/v1/{mode}/{source.coordinates[0]},{source.coordinates[1]};{destination.coordinates[0]},{destination.coordinates[1]}"
        params = {"overview": "full", "geometries": "geojson", "alternatives": str(alternatives)}
        
        try:
            raw_response = await self.http.get(url, params=params)
            candidates = self._map_to_domain(raw_response)
            return candidates
        except Exception as e:
            logger.error(f"OSRMRoutingProvider Error: {str(e)}")
            raise
