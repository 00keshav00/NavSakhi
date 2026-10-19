from typing import Dict, Any, Type, Optional
from app.intelligence.journey.providers import (
    RoutingProvider, WeatherProvider, SafetyProvider, 
    CrowdProvider, ReportsProvider, TransitProvider, LocationProvider
)

class ProviderRegistry:
    """
    Dedicated registry to register, resolve, and manage provider lifecycles.
    """
    def __init__(self):
        self._providers: Dict[str, Any] = {}

    def register(self, capability: str, provider_instance: Any) -> None:
        """Registers an initialized provider instance under a capability."""
        self._providers[capability] = provider_instance

    def resolve(self, capability: str) -> Any:
        """Resolves an active provider by capability."""
        if capability not in self._providers:
            raise KeyError(f"No provider registered for capability: {capability}")
        return self._providers[capability]

    def resolve_routing(self) -> RoutingProvider:
        return self.resolve("routing")

    def resolve_weather(self) -> WeatherProvider:
        return self.resolve("weather")

    def resolve_safety(self) -> SafetyProvider:
        return self.resolve("safety")

    def resolve_crowd(self) -> CrowdProvider:
        return self.resolve("crowd")
        
    def resolve_reports(self) -> ReportsProvider:
        return self.resolve("reports")

    def resolve_transit(self) -> TransitProvider:
        return self.resolve("transit")
        
    def resolve_location(self) -> LocationProvider:
        return self.resolve("location")
