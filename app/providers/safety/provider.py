from app.intelligence.journey.providers import SafetyProvider
from app.models.journey import Location
from app.providers.shared.http_client import SharedHTTPClient
from app.providers.shared.config import ProviderConfig
from app.providers.shared.circuit_breaker import CircuitBreaker
from app.providers.shared.retry import with_retry
from app.providers.shared.cache import ProviderCache
from app.providers.safety.mapper import SafetyMapper

safety_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout_sec=30)

class MachineLearningSafetyProvider(SafetyProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.http = SharedHTTPClient(timeout_ms=config.timeout_ms)

    @ProviderCache.cached(ttl_seconds=300)
    @with_retry(max_retries=2)
    @safety_circuit
    async def get_safety_score(self, location: Location) -> float:
        url = f"{self.config.base_url}/predict/safety"
        payload = {
            "latitude": location.coordinates[1],
            "longitude": location.coordinates[0]
        }
        raw_response = await self.http.get(url, params=payload)
        return SafetyMapper.map_to_domain(raw_response)
