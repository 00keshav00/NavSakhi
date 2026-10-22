"""
Regression tests for Vercel Preview and Production CORS authorization in NavSakhi.
Verifies exact origin matching, regex pattern boundaries, preflight OPTIONS requests,
and rejection of spoofed / unrelated origins.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_production_origin_allowed():
    """Production origin https://nav-sakhi.vercel.app must receive explicit Access-Control-Allow-Origin."""
    response = client.get(
        "/health",
        headers={"Origin": "https://nav-sakhi.vercel.app"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://nav-sakhi.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_observed_preview_host_1_allowed():
    """Branch preview host must receive explicit Access-Control-Allow-Origin via allow_origin_regex."""
    origin = "https://nav-sakhi-git-feature-phase46k3-bou-adbb8e-00keshav00s-projects.vercel.app"
    response = client.get(
        "/health",
        headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_observed_preview_host_2_allowed():
    """Deployment-hash preview host must receive explicit Access-Control-Allow-Origin via allow_origin_regex."""
    origin = "https://nav-sakhi-2upd8mv40-00keshav00s-projects.vercel.app"
    response = client.get(
        "/health",
        headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_options_request():
    """CORS preflight OPTIONS request from preview origin must return 200 with required headers."""
    origin = "https://nav-sakhi-2upd8mv40-00keshav00s-projects.vercel.app"
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type, authorization",
    }
    response = client.options("/api/v1/journeys/", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_unrelated_origin_rejected():
    """Arbitrary *.vercel.app projects must NOT receive Access-Control-Allow-Origin."""
    unrelated_origin = "https://other-project-00keshav00s-projects.vercel.app"
    response = client.get(
        "/health",
        headers={"Origin": unrelated_origin}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_spoofed_origin_prefix_rejected():
    """Origins spoofing the nav-sakhi prefix (e.g. evil-nav-sakhi) must NOT receive Access-Control-Allow-Origin."""
    spoofed_origin = "https://evil-nav-sakhi-00keshav00s-projects.vercel.app"
    response = client.get(
        "/health",
        headers={"Origin": spoofed_origin}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_spoofed_domain_rejected():
    """Origins on attacker domains must NOT receive Access-Control-Allow-Origin."""
    attacker_origin = "https://nav-sakhi.attacker.com"
    response = client.get(
        "/health",
        headers={"Origin": attacker_origin}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_insecure_http_preview_rejected():
    """Insecure http:// preview origins must NOT receive Access-Control-Allow-Origin."""
    http_origin = "http://nav-sakhi-2upd8mv40-00keshav00s-projects.vercel.app"
    response = client.get(
        "/health",
        headers={"Origin": http_origin}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
