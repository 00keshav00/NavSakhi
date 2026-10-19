# Provider Layer Audit

**Location:** `app/providers/`
**Purpose:** Abstract away external APIs (Google Maps, OSRM, Twilio, OpenAI, OpenWeather) into unified Python dataclasses, allowing the underlying technology to be swapped without modifying the Agent or Service logic.

## 1. Routing Provider
- **File:** `app/providers/routing/`
- **Purpose:** Calculate physical paths between GPS coordinates.
- **Status:** **Placeholder.** Currently generates static/hardcoded GeoJSON LineString coordinates rather than calling OSRM or Google Directions API.

## 2. Weather Provider
- **File:** `app/providers/weather/`
- **Purpose:** Fetch live meteorological data.
- **Status:** **Placeholder.** Currently returns randomized dummy weather data instead of querying OpenWeather API.

## 3. Location Provider
- **File:** `app/providers/location/`
- **Purpose:** Geocoding (Address to GPS) and Reverse Geocoding.
- **Status:** **Placeholder.** Hardcoded responses.

## 4. Reports Provider (Community)
- **File:** `app/providers/reports/`
- **Purpose:** Fetch community hazards.
- **Status:** **Working.** This provider successfully maps to the `CommunityRepository` to execute MongoDB `$near` queries.

## 5. Notification Provider
- **File:** `app/providers/communications/` (Assumed location based on typical architecture, likely handles SMS).
- **Purpose:** Dispatch SMS and Push notifications for SOS triggers.
- **Status:** **Placeholder.** SMS dispatch is mocked via console logs.

## 6. AI/LLM Provider
- **File:** `app/providers/ai/provider.py`
- **Purpose:** LLM Integration.
- **Method:** `AIPipelineProvider.explain_decision()`
- **Status:** **Placeholder.** Contains a marked `[LLM MODEL BOUNDARY]`. Currently returns hardcoded strings explaining safety scores instead of hitting OpenAI/Anthropic APIs.
