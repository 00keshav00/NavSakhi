# tests/test_phase51_production_security.py
"""
NavSakhi Phase 51.0 Production Packaging & Security Hardening Tests
Verifies fail-closed JWT secrets in production, safe development defaults,
non-wildcard CORS origins, and authoritative health endpoints.
"""

import pytest
from app.config.settings import Settings, KNOWN_INSECURE_JWT_SECRETS
from fastapi.testclient import TestClient
from app.main import app

def test_dev_settings_defaults_to_insecure_key_safely():
    """In development mode, system defaults to standard local dev key for seamless developer setup."""
    s = Settings(_env_file=None, environment="development", secret_key=None, jwt_secret_key=None)
    assert s.effective_jwt_secret == "safeshe_jwt_secret_change_in_production"
    assert "http://localhost:3000" in s.cors_origins
    assert "http://127.0.0.1:3000" in s.cors_origins


def test_prod_settings_missing_secret_fails_closed():
    """In production mode, missing JWT secret must fail closed with ValueError."""
    with pytest.raises(ValueError, match="must be explicitly set in production"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key=None,
            jwt_secret=None,
            jwt_secret_key=None
        )


@pytest.mark.parametrize("bad_secret", list(KNOWN_INSECURE_JWT_SECRETS))
def test_prod_settings_known_insecure_secret_fails_closed(bad_secret):
    """In production mode, known insecure default or placeholder secrets must fail closed."""
    with pytest.raises(ValueError, match="cannot use an insecure or development placeholder"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key=bad_secret
        )


def test_prod_settings_short_secret_fails_closed():
    """In production mode, secrets under 32 characters fail closed."""
    with pytest.raises(ValueError, match="must be at least 32 characters"):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="too_short_less_than_32_chars"
        )


def test_prod_settings_valid_strong_secret_succeeds():
    """In production mode, a strong 32+ character secret succeeds."""
    strong_key = "a_very_strong_production_secret_key_exceeding_32_chars_12345"
    s = Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key=strong_key
    )
    assert s.effective_jwt_secret == strong_key


def test_cors_origins_never_wildcard():
    """CORS origins must never contain '*' to preserve allow_credentials=True compliance."""
    s1 = Settings(_env_file=None, frontend_url="*")
    assert "*" not in s1.cors_origins
    assert "https://nav-sakhi.vercel.app" in s1.cors_origins

    s2 = Settings(_env_file=None, allowed_origins="*")
    assert "*" not in s2.cors_origins
    assert "https://nav-sakhi.vercel.app" in s2.cors_origins

    s3 = Settings(_env_file=None, frontend_url="https://safeshe.vercel.app, https://navsakhi.vercel.app")
    assert "https://safeshe.vercel.app" in s3.cors_origins
    assert "https://navsakhi.vercel.app" in s3.cors_origins
    assert "*" not in s3.cors_origins


def test_authoritative_health_endpoints():
    """Both /health and /api/v1/health must return 200 OK and status 'ok'."""
    client = TestClient(app)
    
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"
    assert "app" in r1.json()

    r2 = client.get("/api/v1/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "ok"
    assert r2.json() == r1.json()
