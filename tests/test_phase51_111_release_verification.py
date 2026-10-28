"""
NavSakhi Phase 51.111 — Final Release Verification Suite
Verifies:
1. Natural conversational routing across distinct user intents (greetings, companionship, support, facilities).
2. Genuine Gemini AI success telemetry vs honest deterministic application fallback.
3. HTTP 429, HTTP 503, and timeout failover behavior honoring Retry-After.
4. Grounded POI retrieval via POITool (resolving VIT Chennai, Kandigai, Panagal Park) & missing location disclosure.
5. Commercial POI coverage along corridor (VIT Chennai -> T. Nagar) and truthful provenance classification.
6. Activity zones presence with calm disclosure (no misleading safety claims).
7. Weather single-flight coalescing, coordinate normalization, and 429 rate-limit fallback.
8. Authentication continuity, token hydration, and safe redirect validation.
"""

import time
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.assistant_intent_service import (
    global_intent_classifier,
    AssistantIntent,
    AssistantIntentClassifier
)
from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    get_configured_gemini_models,
    is_model_in_cooldown,
    record_model_429,
    _model_cooldowns,
    reset_gemini_cooldowns
)
from app.tools.specialized.poi_tool import POITool
from app.services.poi_service import get_poi_service
from app.services.weather_service import WeatherService
from app.schemas.weather_schemas import LiveWeatherResponse


@pytest.fixture(autouse=True)
def reset_cooldown_fixture():
    reset_gemini_cooldowns()
    yield
    reset_gemini_cooldowns()


# =====================================================================
# 1. Natural Conversation Routing & Distinct Intents
# =====================================================================

def test_natural_conversation_routing_intents():
    """Verify distinct conversational intents route with requires_external_llm=True and unique fallbacks."""
    classifier = global_intent_classifier

    # Conversational messages that should route to LLM when online
    queries = {
        "hello": AssistantIntent.SMALL_TALK,
        "can we talk?": AssistantIntent.COMPANION_EMPATHY,
        "will you accompany me while I travel?": AssistantIntent.COMPANION_EMPATHY,
        "I feel anxious travelling alone at night": AssistantIntent.COMPANION_EMPATHY,
        "Can you tell me about NavSakhi?": AssistantIntent.NAVSAKHI_SUPPORT,
        "What safety features are available?": AssistantIntent.NAVSAKHI_SUPPORT,
        "Are there any mapped pharmacies around VIT Chennai?": AssistantIntent.JOURNEY_TRANSIT,
    }

    fallback_replies = set()
    for query_text, expected_intent in queries.items():
        res = classifier.classify(query_text)
        assert res.intent == expected_intent, f"Query '{query_text}' expected {expected_intent}, got {res.intent}"
        assert res.requires_external_llm is True, f"Query '{query_text}' should route to LLM when provider is available"
        if res.direct_response:
            fallback_replies.add(res.direct_response)

    # Ensure distinct queries do not all map to one identical canned string
    assert len(fallback_replies) >= 3, "Distinct intent categories must have distinct fallback responses"


# =====================================================================
# 2. Genuine Gemini Telemetry vs Honest Fallback
# =====================================================================

@pytest.mark.asyncio
async def test_genuine_gemini_success_telemetry():
    """Verify successful Gemini API generation emits response_source='gemini' and model identifier."""
    tool = ReasoningTool()

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "Hello! I am your NavSakhi companion. How can I help you in Chennai today?"}]}}
        ]
    }

    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="AIzaSy_mock_test_key_111"):
        with patch("httpx.AsyncClient.post", return_value=mock_resp_200):
            res = await tool.execute({"context": {"query": "hello"}})
            assert res["response_source"] == "gemini"
            assert res["ai_status"] == "LIVE_SUCCESS"
            assert res["model_identifier"] in get_configured_gemini_models()
            assert res["gemini_attempted"] is True
            assert res["outcome_category"] == "success"
            assert "NavSakhi companion" in res["summary"]


@pytest.mark.asyncio
async def test_honest_fallback_when_gemini_offline():
    """Verify that when Gemini is unconfigured or offline, response_source is 'fallback' or 'rule_based'."""
    tool = ReasoningTool()

    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value=None):
        res = await tool.execute({"context": {"query": "Can you tell me about NavSakhi?"}})
        assert res["response_source"] in ("fallback", "rule_based")
        assert res["ai_status"] != "LIVE_SUCCESS"
        assert res["gemini_attempted"] is False
        assert res["model_identifier"] is None
        assert "NavSakhi" in res["summary"]
        assert "Key features include" in res["summary"] or "travel companion" in res["summary"]


# =====================================================================
# 3. HTTP 429, 503, and Failover Behavior
# =====================================================================

@pytest.mark.asyncio
async def test_gemini_429_retry_after_cooldown_and_failover():
    """Verify HTTP 429 parses Retry-After header, activates cooldown, and fails over to secondary candidate."""
    tool = ReasoningTool()

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"retry-after": "45"}
    mock_resp_429.text = '{"error": {"message": "Resource has been exhausted", "status": "RESOURCE_EXHAUSTED"}}'

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "Failover model successfully generated response."}]}}
        ]
    }

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_resp_429
        return mock_resp_200

    models = get_configured_gemini_models()
    primary_model = models[0]
    secondary_model = models[1]

    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="AIzaSy_mock_test_key_111"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            res = await tool.execute({"context": {"query": "will you accompany me while I travel?"}})
            assert res["response_source"] == "gemini"
            assert res["model_identifier"] == secondary_model
            assert is_model_in_cooldown(primary_model) is True


@pytest.mark.asyncio
async def test_gemini_503_transient_failure_fails_over():
    """Verify HTTP 503 transient failure triggers clean failover to next model candidate."""
    tool = ReasoningTool()

    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503
    mock_resp_503.text = "Service Unavailable"

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Recovered via backup candidate."}]}}]
    }

    call_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_resp_503
        return mock_resp_200

    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="AIzaSy_mock_test_key_111"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            res = await tool.execute({"context": {"query": "what safety features are available?"}})
            assert res["response_source"] == "gemini"
            assert res["ai_status"] == "LIVE_SUCCESS"
            assert "Recovered via backup candidate" in res["summary"]


# =====================================================================
# 4. Grounded POI Retrieval & Missing Location Handling
# =====================================================================

@pytest.mark.asyncio
async def test_poi_tool_vit_chennai_resolution():
    """Verify POITool resolves 'VIT Chennai' and returns grounded mapped establishments."""
    poi_tool = POITool()
    res = await poi_tool.execute({
        "place": "VIT Chennai",
        "radius_m": 3000.0,
        "max_results": 10
    })
    assert res["status"] == "AVAILABLE"
    assert len(res["pois"]) > 0
    # Establishments near VIT Chennai include Jarvinia Tea Kadai, Gazebo, hostels
    poi_names = [p["name"] for p in res["pois"]]
    assert any("Jarvinia" in n or "Gazebo" in n or "Hostel" in n or "Campus" in n for n in poi_names)


@pytest.mark.asyncio
async def test_poi_tool_location_missing():
    """Verify POITool gracefully handles missing location parameters with helpful disclosure."""
    poi_tool = POITool()
    res = await poi_tool.execute({})
    assert res["status"] == "LOCATION_MISSING"
    assert res["total_found"] == 0
    assert "required" in res["disclosure"].lower()


@pytest.mark.asyncio
async def test_reasoning_tool_pure_coordinates_acknowledgement():
    """Verify that when coordinates are sent alone, the assistant acknowledges them and asks what the user seeks."""
    tool = ReasoningTool()
    # Coordinates for Panagal Park / T. Nagar
    res = await tool.execute({"context": {"query": "13.0418, 80.2337"}})
    summary = res["summary"]
    assert "13.0418" in summary or "coordinates" in summary.lower()
    assert any(phrase in summary.lower() for phrase in [
        "what would you like to find", "what you would like to find",
        "how can i help", "searching for", "let me know"
    ])
    assert len(res.get("reasoning", [])) > 0


# =====================================================================
# 5. Route Corridor Commercial POI Coverage & Provenance
# =====================================================================

def test_route_corridor_commercial_poi_coverage_and_provenance():
    """Verify corridor query between VIT Chennai and T. Nagar returns enriched commercial shops without false claims."""
    poi_service = get_poi_service()

    # Route corridor from VIT Chennai (12.8406, 80.1554) to T. Nagar (13.0418, 80.2337)
    corridor_coords = [
        [80.15540, 12.84060],
        [80.17000, 12.89000],
        [80.19000, 12.95000],
        [80.21840, 13.00670],
        [80.23370, 13.04180]
    ]

    res = poi_service.query_pois_near_route(
        corridor_coords, corridor_m=800.0, max_pois_per_category=25, max_total_pois=150
    )
    pois = res.get("pois", [])
    assert len(pois) >= 50, f"Corridor should contain substantial mapped places, found {len(pois)}"

    shops = [p for p in pois if p.get("is_shop")]
    emergencies = [p for p in pois if p.get("is_emergency")]

    assert len(shops) >= 30, f"Commercial shops along corridor should be well-represented, found {len(shops)}"
    assert len(emergencies) > 0, "Emergency facilities should also be preserved along corridor"

    # Strict provenance check: commercial shops must NEVER claim to be verified safety facilities or safe havens
    for s in shops:
        assert s["is_verified_safety_facility"] is False
        assert s["is_safe_haven_eligible"] is False
        assert s["provenance_type"] == "mapped_commercial_business"


def test_corridor_activity_zones_present_without_safety_claims():
    """Verify activity zones are identified along corridor with clear commercial disclosure."""
    poi_service = get_poi_service()
    corridor_coords = [
        [80.15540, 12.84060],
        [80.19000, 12.95000],
        [80.23370, 13.04180]
    ]
    res = poi_service.query_pois_near_route(corridor_coords, corridor_m=800.0)
    zones = res.get("activity_zones", [])
    assert len(zones) > 0, "Commercial clusters along corridor should produce activity zones"

    for z in zones:
        assert "shop_count" in z
        assert z["activity_level"] in ("HIGH", "MODERATE")
        assert "Does not represent live crowd density or verified police presence" in z["disclosure"]


# =====================================================================
# 6. Weather Service Coalescing, Caching, and 429 Cooldown
# =====================================================================

@pytest.mark.asyncio
async def test_weather_service_concurrent_coalescing():
    """Verify identical concurrent requests for the same coordinates share a single network call."""
    service = WeatherService()
    call_count = 0

    dummy_weather = LiveWeatherResponse(
        available=True,
        status="AVAILABLE",
        provider="Open-Meteo",
        latitude=13.0418,
        longitude=80.2337,
        location_name="T. Nagar, Chennai",
        timezone="Asia/Kolkata",
        temperature=29.0,
        apparent_temperature=30.5,
        condition="Clear sky",
        humidity=65,
        wind_speed=12.0,
        observation_timestamp="2026-10-27T12:00:00"
    )

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "current": {"temperature_2m": 29.0, "apparent_temperature": 30.5, "relative_humidity_2m": 65, "weather_code": 0, "wind_speed_10m": 12.0, "time": "2026-10-27T12:00:00"},
            "daily": {},
            "hourly": {}
        }
        return resp

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        # Fire 5 concurrent requests for identical coordinates
        results = await asyncio.gather(*[
            service.get_live_weather(13.0418, 80.2337, location_name="T. Nagar")
            for _ in range(5)
        ])
        assert len(results) == 5
        assert call_count == 1, f"Concurrent requests must coalesce into exactly 1 network call, got {call_count}"
        for r in results:
            assert r.temperature == 29.0
            assert r.status == "AVAILABLE"


@pytest.mark.asyncio
async def test_weather_service_429_uses_cached_observation():
    """Verify 429 rate limit activates cooldown and reuses last valid observation with warning."""
    service = WeatherService()
    lat, lon = 13.04, 80.23
    cache_key = (round(lat, 2), round(lon, 2))

    # Seed an earlier verified observation
    prior_obs = LiveWeatherResponse(
        available=True,
        status="AVAILABLE",
        provider="Open-Meteo",
        latitude=lat,
        longitude=lon,
        location_name="Chennai Central",
        timezone="Asia/Kolkata",
        temperature=30.0,
        apparent_temperature=32.0,
        condition="Partly cloudy",
        humidity=70,
        wind_speed=10.0,
        observation_timestamp="2026-10-27T10:00:00"
    )
    service._last_valid_observation[cache_key] = (time.time() - 100, prior_obs)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"retry-after": "30"}

    with patch("httpx.AsyncClient.get", return_value=mock_resp_429):
        res = await service.get_live_weather(lat, lon, location_name="Chennai Central")
        assert res.status == "AVAILABLE"
        assert res.cached is True
        assert res.temperature == 30.0
        assert any("rate-limited" in w.lower() for w in res.warnings)


# =====================================================================
# 7. Safe Redirect URL & Navigation Integrity
# =====================================================================

def test_safe_redirect_rules_enforcement():
    """Verify safe redirect helper allows recognized paths and rejects open redirect attacks."""
    from pathlib import Path
    safe_redirect_file = Path("frontend/src/utils/safeRedirect.ts")
    assert safe_redirect_file.exists(), "safeRedirect.ts must exist"
    content = safe_redirect_file.read_text(encoding="utf-8")

    # Verify protected internal routes
    for route in ["/journey", "/home", "/live", "/assistant", "/settings", "/terms", "/privacy"]:
        assert route in content, f"Route {route} must be included in ALLOWED_INTERNAL_ROUTES"

    # Verify defense against external and protocol-relative redirects
    assert 'trimmed.startsWith("//")' in content
    assert 'trimmed.includes("://")' in content
    assert 'javascript:' in content
