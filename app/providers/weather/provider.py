from typing import Dict, Any
from app.intelligence.journey.providers import WeatherProvider
from app.models.journey import Location, WeatherState
from app.providers.shared.http_client import SharedHTTPClient
from app.providers.shared.retry import with_retry
from app.providers.shared.cache import ProviderCache
from app.providers.shared.exceptions import ProviderResponseMappingError
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class OpenWeatherProvider(WeatherProvider):
    def __init__(self):
        self.base_url = settings.weather_api_url or "https://api.openweathermap.org/data/2.5"
        self.api_key = settings.weather_api_key or "demo_key"
        self.http = SharedHTTPClient(timeout_ms=5000)

    @staticmethod
    def _map_to_domain(vendor_data: Dict[str, Any]) -> WeatherState:
        try:
            return WeatherState(
                temperature=vendor_data.get("main", {}).get("temp"),
                condition=vendor_data.get("weather", [{}])[0].get("main", "UNKNOWN"),
                humidity=vendor_data.get("main", {}).get("humidity"),
                visibility=vendor_data.get("visibility"),
                wind_speed=vendor_data.get("wind", {}).get("speed")
            )
        except Exception as e:
            raise ProviderResponseMappingError(f"Failed to map weather data: {str(e)}")

    @ProviderCache.cached(ttl_seconds=settings.weather_cache_ttl)
    @with_retry(max_retries=2, base_delay_ms=200)
    async def get_weather(self, location: Location) -> WeatherState:
        url = f"{self.base_url}/weather"
        params = {
            "lat": location.coordinates[1],
            "lon": location.coordinates[0],
            "appid": self.api_key
        }
        
        try:
            raw_response = await self.http.get(url, params=params)
            return self._map_to_domain(raw_response)
        except Exception as e:
            logger.error(f"OpenWeatherProvider Error: {str(e)}")
            raise
