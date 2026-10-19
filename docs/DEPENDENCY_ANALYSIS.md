# SafeShe Dependency Analysis

This document catalogs the third-party dependencies utilized by the SafeShe backend.

## Python Packages (via `requirements.txt`)

| Package | Purpose | Runtime Role |
|---------|---------|--------------|
| **`fastapi`** | Core Web Framework | High-performance ASGI framework powering all HTTP and WS routes. |
| **`uvicorn`** | ASGI Server | The web server that runs FastAPI in production. |
| **`pydantic`** | Data Validation | Core validation library used across `models/`, `schemas/`, and Settings. |
| **`pydantic-settings`** | Configuration | Manages `.env` parsing mapping environment variables to the `Settings` class. |
| **`motor`** | Database Driver | The official asynchronous Python driver for MongoDB. |
| **`email-validator`** | Utility | Validates email strings during User registration via Pydantic integration. |
| **`python-dotenv`** | Utility | Loads `.env` file variables into the system environment. |
| **`httpx`** | HTTP Client | Asynchronous HTTP client used by Providers to talk to external APIs (OSRM, Weather). |
| **`pytest` & `pytest-asyncio`** | Testing | Used for executing the integration test suite located in `/tests`. |

## Third-Party External APIs (Providers)

| Provider | Purpose | Status in Code |
|----------|---------|----------------|
| **OpenStreetMap (OSRM)** | Routing | Implemented via `OSRMRoutingProvider`. |
| **Nominatim** | Geocoding | Implemented via `NominatimLocationProvider`. |
| **OpenWeather** | Weather Data | Implemented via `OpenWeatherProvider`. |
| **Ollama** | Local LLM Engine | Supported via `llm_provider.py`, though heavily stubbed in the Agent execution loop. |

## Version Compatibility
*Note: The `requirements.txt` file currently does not pin versions (e.g., `fastapi==0.103.2`).* 

**Risk**: Because versions are unpinned, a fresh `pip install -r requirements.txt` will pull the latest version of all dependencies. If FastAPI releases a breaking change to Pydantic v2 support, or Motor updates its driver logic, the application may fail to boot. 

**Recommendation**: Freeze requirements into a `requirements.lock` or specify exact versions in `requirements.txt`.
