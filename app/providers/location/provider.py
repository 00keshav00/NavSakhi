from typing import Dict, Any, List
from app.intelligence.journey.providers import LocationProvider
from app.models.journey import Location, POI, Address, RoadInfo, POICollection
from app.providers.shared.http_client import SharedHTTPClient
from app.providers.shared.retry import with_retry
from app.providers.shared.cache import ProviderCache
from app.providers.shared.exceptions import ProviderResponseMappingError
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class NominatimLocationProvider(LocationProvider):
    """
    Concrete implementation of LocationProvider using OSM/Nominatim.
    """
    def __init__(self):
        self.base_url = settings.nominatim_base_url or "https://nominatim.openstreetmap.org"
        self.overpass_url = settings.overpass_base_url or "https://overpass-api.de/api/interpreter"
        self.http = SharedHTTPClient(timeout_ms=5000)

    @staticmethod
    def _map_to_address(vendor_data: Dict[str, Any]) -> Address:
        try:
            return Address(
                display_name=vendor_data.get("display_name", "Unknown Location"),
                metadata=vendor_data
            )
        except Exception as e:
            raise ProviderResponseMappingError(f"Failed to map address: {str(e)}")

    @ProviderCache.cached(ttl_seconds=settings.location_cache_ttl)
    @with_retry(max_retries=3, base_delay_ms=200)
    async def reverse_geocode(self, location: Location) -> Address:
        url = f"{self.base_url}/reverse"
        params = {
            "lat": location.coordinates[1],
            "lon": location.coordinates[0],
            "format": "json"
        }
        headers = {"User-Agent": "SafeShe/1.0"}
        
        try:
            raw_response = await self.http.get(url, params=params, headers=headers)
            return self._map_to_address(raw_response)
        except Exception as e:
            logger.error(f"NominatimLocationProvider Error: {str(e)}")
            raise

    @ProviderCache.cached(ttl_seconds=settings.location_cache_ttl)
    @with_retry(max_retries=3, base_delay_ms=200)
    async def forward_geocode(self, address: str) -> Location:
        url = f"{self.base_url}/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "SafeShe/1.0"}
        
        try:
            raw_response = await self.http.get(url, params=params, headers=headers)
            if not raw_response or not isinstance(raw_response, list) or len(raw_response) == 0:
                raise ProviderResponseMappingError(f"No results found for address: {address}")
                
            first_result = raw_response[0]
            lat = float(first_result.get("lat"))
            lon = float(first_result.get("lon"))
            return Location(coordinates=[lon, lat])
        except Exception as e:
            logger.error(f"NominatimLocationProvider Forward Geocode Error: {str(e)}")
            raise

    @ProviderCache.cached(ttl_seconds=settings.location_cache_ttl)
    @with_retry(max_retries=3, base_delay_ms=500)
    async def get_nearby_pois(self, location: Location, poi_type: str, radius_m: int = 500) -> POICollection:
        # Translating standard poi types into Overpass OSM tags
        tag_map = {
            "hospital": 'node["amenity"="hospital"]',
            "police": 'node["amenity"="police"]',
            "restaurant": 'node["amenity"="restaurant"]',
            "bus_stop": 'node["highway"="bus_stop"]',
            "metro": 'node["railway"="station"]'
        }
        osm_query = tag_map.get(poi_type, f'node["amenity"="{poi_type}"]')
        lat, lon = location.coordinates[1], location.coordinates[0]
        
        query = f'[out:json][timeout:5];{osm_query}(around:{radius_m},{lat},{lon});out;'
        
        try:
            raw_response = await self.http.get(self.overpass_url, params={"data": query})
            elements = raw_response.get("elements", [])
            
            pois = []
            for el in elements:
                if "lat" in el and "lon" in el:
                    poi_loc = Location(coordinates=[float(el["lon"]), float(el["lat"])])
                    name = el.get("tags", {}).get("name", f"Unknown {poi_type}")
                    pois.append(POI(
                        name=name,
                        poi_type=poi_type,
                        location=poi_loc,
                        metadata=el.get("tags", {})
                    ))
            return POICollection(items=pois, metadata={"count": len(pois), "radius_m": radius_m})
        except Exception as e:
            logger.error(f"NominatimLocationProvider POI Error: {str(e)}")
            raise

    @ProviderCache.cached(ttl_seconds=settings.location_cache_ttl)
    @with_retry(max_retries=3, base_delay_ms=200)
    async def get_road_type(self, location: Location) -> RoadInfo:
        url = f"{self.base_url}/reverse"
        params = {
            "lat": location.coordinates[1],
            "lon": location.coordinates[0],
            "format": "json",
            "zoom": 18
        }
        headers = {"User-Agent": "SafeShe/1.0"}
        
        try:
            raw_response = await self.http.get(url, params=params, headers=headers)
            road_type = raw_response.get("type", "unknown")
            return RoadInfo(road_type=road_type, metadata=raw_response)
        except Exception as e:
            logger.error(f"NominatimLocationProvider Road Type Error: {str(e)}")
            raise

