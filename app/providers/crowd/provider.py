from app.intelligence.journey.providers import CrowdProvider
from app.models.journey import Location
from app.providers.shared.http_client import SharedHTTPClient
from app.providers.shared.config import ProviderConfig
from app.providers.shared.circuit_breaker import CircuitBreaker
from app.providers.shared.retry import with_retry
from app.providers.shared.cache import ProviderCache
from app.providers.crowd.mapper import CrowdMapper

crowd_circuit = CircuitBreaker(failure_threshold=4, recovery_timeout_sec=45)

class FirebaseCrowdProvider(CrowdProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.http = SharedHTTPClient(timeout_ms=config.timeout_ms)

    @ProviderCache.cached(ttl_seconds=120) # 2 mins cache
    @with_retry(max_retries=2)
    @crowd_circuit
    async def get_crowd_density(self, location: Location) -> float:
        url = f"{self.config.base_url}/density"
        params = {
            "lat": location.coordinates[1],
            "lng": location.coordinates[0],
            "radius_m": 500
        }
        raw_response = await self.http.get(url, params=params)
        return CrowdMapper.map_to_domain(raw_response)
