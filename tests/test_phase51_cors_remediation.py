"""
NavSakhi Phase 51.48 CORS Remediation Offline Test Suite

Validates:
1. Preview deployment origins (e.g. dynamic hashes, git branch previews) under
   the 00keshav00s-projects.vercel.app namespace succeed with appropriate CORS headers.
2. Production origin https://nav-sakhi.vercel.app remains allowed.
3. Canonical project preview alias https://nav-sakhi-00keshav00s-projects.vercel.app is allowed.
4. Local development origins remain allowed.
5. Arbitrary, unanchored, and malicious origins are strictly rejected.
6. Preflight OPTIONS requests succeed with Authorization and Content-Type allowed.
7. Wildcard '*' is never emitted as Access-Control-Allow-Origin with credentials.
8. Exception and 404 responses maintain CORS headers for allowed origins.
9. Configuration override via CORS_ORIGIN_REGEX behaves as expected.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config.settings import Settings


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_cors_settings_default_regex():
    """Default regex must specifically match NavSakhi preview deployments."""
    s = Settings(_env_file=None)
    assert s.effective_cors_origin_regex is not None
    assert "nav-sakhi" in s.effective_cors_origin_regex
    assert "00keshav00s-projects" in s.effective_cors_origin_regex


def test_cors_settings_override_and_disable():
    """CORS regex can be overridden or disabled via environment settings."""
    s_custom = Settings(_env_file=None, cors_origin_regex=r"^https:\/\/custom\.domain\.com$")
    assert s_custom.effective_cors_origin_regex == r"^https:\/\/custom\.domain\.com$"

    s_disabled = Settings(_env_file=None, cors_origin_regex="disabled")
    assert s_disabled.effective_cors_origin_regex is None

    s_none = Settings(_env_file=None, cors_origin_regex="none")
    assert s_none.effective_cors_origin_regex is None


def test_preview_hash_origin_preflight_options(client):
    """
    Reported browser failure origin:
    https://nav-sakhi-1no2t69ek-00keshav00s-projects.vercel.app
    Must receive status 200 with matching Access-Control-Allow-Origin and allowed headers.
    """
    origin = "https://nav-sakhi-1no2t69ek-00keshav00s-projects.vercel.app"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "content-type" in allow_headers


def test_branch_preview_origin_preflight_options(client):
    """
    Observed git branch preview origin:
    https://nav-sakhi-git-release-phase51-rende-64c23c-00keshav00s-projects.vercel.app
    Must receive status 200 with matching Access-Control-Allow-Origin.
    """
    origin = "https://nav-sakhi-git-release-phase51-rende-64c23c-00keshav00s-projects.vercel.app"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_canonical_preview_origin_preflight_options(client):
    """Canonical team preview origin https://nav-sakhi-00keshav00s-projects.vercel.app."""
    origin = "https://nav-sakhi-00keshav00s-projects.vercel.app"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_production_origin_allowed(client):
    """Production frontend origin https://nav-sakhi.vercel.app."""
    origin = "https://nav-sakhi.vercel.app"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin

    # Normal GET request
    get_res = client.get("/api/v1/health", headers={"Origin": origin})
    assert get_res.status_code == 200
    assert get_res.headers.get("access-control-allow-origin") == origin


def test_local_development_origins_allowed(client):
    """Localhost and loopback origins."""
    for origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        response = client.get("/api/v1/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


def test_unrelated_and_malicious_origins_rejected(client):
    """
    Origins that do NOT match the NavSakhi scope must be rejected without CORS headers.
    """
    disallowed_origins = [
        "https://evil.vercel.app",
        "https://other-project-00keshav00s-projects.vercel.app",
        "https://nav-sakhi.evil.com",
        "https://evil-nav-sakhi-00keshav00s-projects.vercel.app",
        "http://nav-sakhi-1no2t69ek-00keshav00s-projects.vercel.app", # insecure HTTP
    ]

    for origin in disallowed_origins:
        # Preflight OPTIONS must be rejected (400) without Access-Control-Allow-Origin
        res = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.headers.get("access-control-allow-origin") is None

        # Direct GET must NOT return Access-Control-Allow-Origin for disallowed origins
        res_get = client.get("/api/v1/health", headers={"Origin": origin})
        assert res_get.headers.get("access-control-allow-origin") is None


def test_cors_headers_preserved_on_exceptions(client):
    """
    When an API error occurs (404, 422, 500), CORS headers must still be returned
    to allowed origins so the browser does not mask the error as a CORS violation.
    """
    origin = "https://nav-sakhi-1no2t69ek-00keshav00s-projects.vercel.app"
    response = client.get("/api/v1/nonexistent-endpoint-test-404", headers={"Origin": origin})
    assert response.status_code == 404
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_never_emits_wildcard_origin(client):
    """
    With allow_credentials=True, Access-Control-Allow-Origin must NEVER be '*'
    under any circumstances.
    """
    for origin in [
        "https://nav-sakhi-1no2t69ek-00keshav00s-projects.vercel.app",
        "https://nav-sakhi.vercel.app",
        "http://localhost:3000",
    ]:
        res = client.get("/api/v1/health", headers={"Origin": origin})
        allow_origin = res.headers.get("access-control-allow-origin")
        assert allow_origin != "*"
        assert allow_origin == origin
