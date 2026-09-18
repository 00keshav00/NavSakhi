# SafeShe Providers Documentation

This document maps all external integration points (Providers) defined within `app/providers/` and how they are injected via `app/api/dependencies.py`.

## Architectural Role
Providers in SafeShe wrap external HTTP APIs (e.g. OSRM, OpenWeather) to decouple the internal Intelligence and Service layers from vendor-specific payload structures. They are managed by the `ProviderRegistry`.

---

## 1. Routing Provider
- **Interface**: `BaseMapsProvider` (or `RoutingProvider`)
- **Current Implementation**: `OSRMRoutingProvider`
- **Status**: **Fully Implemented**
- **Purpose**: Calculates geospatial routes between a source and destination.
- **Methods**: `get_routes(source, destination, mode)`
- **Inputs**: GeoJSON points and string mode (e.g. "WALK").
- **Outputs**: Parsed OSRM geometries and distance/duration metrics.
- **Fallback/Mock**: None natively, but acts as a fallback for missing ML metrics.

## 2. Location Provider
- **Interface**: `LocationProvider`
- **Current Implementation**: `NominatimLocationProvider`
- **Status**: **Fully Implemented**
- **Purpose**: Geocoding (Text to Lat/Lng) and Reverse Geocoding.
- **Methods**: `geocode(address)`, `reverse_geocode(lat, lng)`
- **External API**: OpenStreetMap Nominatim
- **Caching**: TTL of 86400 seconds (24 hours) as defined in settings.

## 3. Weather Provider
- **Interface**: `BaseWeatherProvider` (or `WeatherProvider`)
- **Current Implementation**: `OpenWeatherProvider`
- **Status**: **Fully Implemented**
- **Purpose**: Fetches real-time weather conditions that feed into the ML safety model.
- **Methods**: `get_weather(location)`
- **Inputs**: GeoJSON point.
- **Outputs**: Dictionary with `condition` (e.g., Clear, Rain) and `temperature_c`.

## 4. Transit Provider
- **Interface**: `TransitProvider`
- **Current Implementation**: `PlaceholderTransitProvider`
- **Status**: **Stubbed / Mocked**
- **Purpose**: Should provide metro/bus schedules.
- **Current Logic**: Returns an empty or hardcoded array. The class name explicitly denotes it as a placeholder. Requires future integration with Google Transit or local GTFS feeds.

## 5. Reports Provider
- **Interface**: `ReportsProvider`
- **Current Implementation**: `MongoReportsProvider`
- **Status**: **Fully Implemented**
- **Purpose**: Queries the internal MongoDB database for geospatial community reports near a specific route or point.
- **Database Dependency**: Relies on the `2dsphere` index created in `init_db.py`.

## 6. LLM Provider
- **Interface**: `BaseLLMProvider`
- **Current Implementation**: Configurable via settings (`Ollama` or raw API).
- **Status**: **Partially Implemented (Stubbed in Agent Base)**
- **Purpose**: Text generation for the AI Assistant and Plan Explainers.
- **Current Logic**: While the provider exists, `BaseAgent.execute_tools` mocks the LLM execution in the current milestone, bypassing real API calls to ensure rapid development testing.

## Summary
The provider architecture uses strict Dependency Injection. To switch from `OSRMRoutingProvider` to Google Maps, one only needs to create `GoogleRoutingProvider` and update the return type in `app/api/dependencies.py::get_routing_provider()`.
