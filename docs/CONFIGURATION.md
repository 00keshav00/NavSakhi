# SafeShe Configuration Documentation

This document provides a complete static analysis of the `app/config/` directory, which governs global application settings, constants, and logging.

## 1. `app/config/settings.py`

- **Purpose**: The central configuration registry for the backend, reading from `.env` using Pydantic Settings.
- **Language**: Python
- **Type**: Configuration Provider
- **Imports**: `pydantic_settings.BaseSettings`, `pydantic_settings.SettingsConfigDict`, `typing.Optional`
- **Classes**: `Settings(BaseSettings)`
- **Global Variables**: `settings` (Instance of Settings)
- **Status**: Used globally.

### Implemented Configuration Fields
**App Settings**
- `app_name`: "SafeShe"
- `app_version`: "1.0.0"
- `debug`: boolean flag (default False)
- `api_prefix`: "/api/v1"

**Database**
- `mongodb_uri`: "mongodb://localhost:27017"
- `database_name`: "safeshe_db"

**Integrations (Environment Variables expected from `.env`)**
- `osrm_base_url`
- `weather_api_key`
- `weather_api_url`
- `ollama_base_url`
- `llm_model_name`
- `frontend_url` (default "*")
- `secret_key`
- `jwt_config`

**Provider Cache TTL (Seconds)**
- `routing_cache_ttl`: 3600 (1 hour)
- `location_cache_ttl`: 86400 (24 hours)
- `weather_cache_ttl`: 1800 (30 mins)
- `transit_cache_ttl`: 7200 (2 hours)
- `reports_cache_ttl`: 60 (1 minute)

**ML / AI Integrations**
- `crowd_model_endpoint`
- `safety_model_endpoint`
- `prediction_timeout`: 5
- `model_version`
- `retry_policy`: 3

## 2. `app/config/constants.py`

- **Purpose**: Defines application-wide enums and magic numbers.
- **Language**: Python
- **Type**: Constants Definition
- **Imports**: `enum.Enum`
- **Status**: Used heavily by routers and schemas for validation.

### Enums
- `JourneyStatus`: `SAFE`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`
- `ReportType`: `POOR_LIGHTING`, `HARASSMENT`, `ROAD_BLOCK`, `ACCIDENT`, `FLOOD`, `CONSTRUCTION`
- `SafetyLevel`: `SAFE`, `MODERATE`, `HIGH_RISK`

### SystemConstants Class
- `DEFAULT_SEARCH_RADIUS_KM` = 5.0
- `NEARBY_DISTANCE_METERS` = 500
- `MAX_REPORTS_RETURNED` = 50
- `JOURNEY_UPDATE_INTERVAL_SEC` = 30

## 3. `app/config/logging_config.py`

- **Purpose**: Configures the standard Python logging library.
- **Language**: Python
- **Type**: Logging Utility
- **Imports**: `logging`, `sys`, `app.config.settings.settings`
- **Functions**: `setup_logging()`
- **Global Variables**: `logger`
- **Status**: Used across all services to emit logs.

### Business Logic
- Checks `settings.debug` to set log level to `DEBUG` or `INFO`.
- Configures a `StreamHandler` pointing to `sys.stdout`.
- Configures a `FileHandler` pointing to `backend.log`.
- Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.
