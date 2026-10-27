from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

KNOWN_INSECURE_JWT_SECRETS = {
    "safeshe_jwt_secret_change_in_production",
    "safeshe_jwt_dev_secret_change_in_production",
    "your_jwt_secret_placeholder",
    "your_secret_key_change_in_production",
    "changeme_in_production",
    "secret",
    "development",
    "dev_secret",
    "change_in_production",
    "placeholder",
}

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
    llm_model_name: Optional[str] = "gemini-3.5-flash-lite"
    gemini_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    gemini_api_key_backup: Optional[str] = None

    # CORS & Frontend Origins
    frontend_url: Optional[str] = None
    allowed_origins: Optional[str] = None
    cors_origin_regex: Optional[str] = None

    DEFAULT_CORS_ORIGIN_REGEX: str = (
        r"^https:\/\/nav-sakhi(-[a-zA-Z0-9_-]+)?-00keshav00s-projects\.vercel\.app$"
    )

    @property
    def effective_cors_origin_regex(self) -> Optional[str]:
        """
        Returns the regex pattern for dynamic frontend preview origins.
        Allows custom regex via CORS_ORIGIN_REGEX environment variable,
        defaulting to the verified NavSakhi Vercel preview deployment pattern.
        Can be disabled by setting CORS_ORIGIN_REGEX to 'none' or 'disabled'.
        """
        if self.cors_origin_regex is not None:
            raw = self.cors_origin_regex.strip()
            if raw.lower() in ["none", "disabled", "false", ""]:
                return None
            return raw
        return self.DEFAULT_CORS_ORIGIN_REGEX

    @property
    def cors_origins(self) -> List[str]:
        """
        Returns the exact list of allowed CORS origins.
        Never emits wildcard '*' to ensure compatibility with allow_credentials=True.
        Always preserves local development origins.
        """
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://nav-sakhi.vercel.app",
            "https://nav-sakhi-00keshav00s-projects.vercel.app",
        ]
        if self.environment.lower() not in ["production", "prod"]:
            origins.extend(["http://localhost:3001", "http://127.0.0.1:3001"])

        if self.frontend_url and self.frontend_url != "*":
            for u in self.frontend_url.split(","):
                clean_u = u.strip().rstrip("/")
                if clean_u and clean_u not in origins and clean_u != "*":
                    origins.append(clean_u)

        if self.allowed_origins:
            for u in self.allowed_origins.split(","):
                clean_u = u.strip().rstrip("/")
                if clean_u and clean_u not in origins and clean_u != "*":
                    origins.append(clean_u)

        return origins

    # Security & JWT Secrets
    secret_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    jwt_config: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    @property
    def effective_jwt_secret(self) -> str:
        # Check explicit jwt keys first, then secret_key
        secret = self.jwt_secret_key or self.jwt_secret or self.secret_key
        if secret:
            return secret
        return "safeshe_jwt_secret_change_in_production"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.environment or "").strip().lower()
        if env in ["production", "prod"]:
            secret = self.jwt_secret_key or self.jwt_secret or self.secret_key
            if not secret:
                raise ValueError(
                    "Production configuration error: JWT_SECRET_KEY (or JWT_SECRET / SECRET_KEY) "
                    "must be explicitly set in production."
                )
            if secret in KNOWN_INSECURE_JWT_SECRETS or "change_in_production" in secret.lower() or "placeholder" in secret.lower():
                raise ValueError(
                    "Production configuration error: JWT_SECRET_KEY cannot use an insecure "
                    "or development placeholder default in production."
                )
            if len(secret) < 32:
                raise ValueError(
                    "Production configuration error: JWT_SECRET_KEY must be at least 32 characters "
                    "in production for cryptographic safety."
                )
        return self

    # Provider Cache TTL (seconds)
    routing_cache_ttl: int = 3600
    location_cache_ttl: int = 86400
    weather_cache_ttl: int = 1800
    transit_cache_ttl: int = 7200
    reports_cache_ttl: int = 60
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "NavSakhi/2.0 (+https://github.com/00keshav00/NavSakhi)"
    nominatim_email: Optional[str] = None
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"

    # ML Configuration
    crowd_model_endpoint: Optional[str] = None
    safety_model_endpoint: Optional[str] = None
    prediction_timeout: int = 5
    model_version: Optional[str] = None
    routing_strategy: str = "STRATEGY_A"
    enable_experimental_strategy_b: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
