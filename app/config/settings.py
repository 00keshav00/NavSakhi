from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    app_name: str = "SafeShe"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "Development"
    api_prefix: str = "/api/v1"

    # Database Settings
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "safeshe_db"

    # Integrations (Environment Variables)
    osrm_base_url: Optional[str] = None
    weather_api_key: Optional[str] = None
    weather_api_url: Optional[str] = None
    ollama_base_url: Optional[str] = None
    llm_model_name: Optional[str] = None
    frontend_url: str = "*"
    secret_key: Optional[str] = None
    jwt_config: Optional[str] = None

    # Provider Cache TTL (seconds)
    routing_cache_ttl: int = 3600
    location_cache_ttl: int = 86400
    weather_cache_ttl: int = 1800
    transit_cache_ttl: int = 7200
    reports_cache_ttl: int = 60
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"

    # ML Configuration
    crowd_model_endpoint: Optional[str] = None
    safety_model_endpoint: Optional[str] = None
    prediction_timeout: int = 5
    model_version: Optional[str] = None
    retry_policy: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
