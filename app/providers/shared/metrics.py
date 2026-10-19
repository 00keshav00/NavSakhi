import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProviderMetrics:
    """
    Standardized metrics collector for Provider performance.
    """
    @staticmethod
    def log_success(provider_name: str, latency_ms: float) -> None:
        logger.info(f"PROVIDER_SUCCESS | Name: {provider_name} | Latency: {latency_ms}ms")

    @staticmethod
    def log_failure(provider_name: str, error: str, latency_ms: float = 0.0) -> None:
        logger.error(f"PROVIDER_FAILURE | Name: {provider_name} | Error: {error} | Latency: {latency_ms}ms")
        
    @staticmethod
    def log_circuit_trip(provider_name: str) -> None:
        logger.warning(f"CIRCUIT_TRIPPED | Name: {provider_name}")
