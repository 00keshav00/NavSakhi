from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    app_name: str = "NavSakhi"
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
    gemini_api_key: Optional[str] = None
    frontend_url: str = "*"
    allowed_origins: Optional[str] = None
    secret_key: Optional[str] = None
    jwt_config: Optional[str] = None
    jwt_secret_key: str = "safeshe_jwt_secret_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    @property
    def effective_jwt_secret(self) -> str:
        return self.secret_key or self.jwt_secret_key

    @property
    def cors_origins(self) -> list[str]:
        """
        Builds the sanitized list of allowed CORS origins.
        Preserves local development origins and appends configured production domains.
        Filters out '*' to ensure credentialed requests remain secure.
        """
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        if self.allowed_origins:
            for o in self.allowed_origins.split(","):
                cleaned = o.strip()
                if cleaned and cleaned != "*" and cleaned not in origins:
                    origins.append(cleaned)
        if self.frontend_url:
            for o in self.frontend_url.split(","):
                cleaned = o.strip()
                if cleaned and cleaned != "*" and cleaned not in origins:
                    origins.append(cleaned)
        return origins

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
