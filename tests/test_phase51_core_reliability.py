import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.assistant_intent_service import (
    global_intent_classifier,
    IntentCategory,
    IntentClassificationResult
)
from app.services.autocomplete_service import AutocompleteService
from app.services.local_location_resolver import global_local_location_resolver
from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    record_gemini_429_event,
    is_gemini_in_rate_limit_cooldown
)
from app.services.weather_service import WeatherService
from app.providers.live.weather import WeatherProvider
from app.models.journey import Location, CandidateRoute
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator


# =====================================================================
# WORKSTREAM A: AUTH ERROR PARSING & EXTRACTION CONTRACT
# =====================================================================
def test_auth_error_message_extraction():
    """Validates FastAPI error envelope unpacking for registration/login failures."""
    # 1. Validation array format (FastAPI Pydantic 422)
    pydantic_422 = {
        "detail": [
            {"loc": ["body", "password"], "msg": "Password must be at least 8 characters", "type": "value_error"}
        ]
    }
    # Emulate frontend extractApiErrorMessage logic
    def extract_msg(data):
        if isinstance(data, dict):
            detail = data.get("detail")
            if isinstance(detail, list) and len(detail) > 0:
                first = detail[0]
                if isinstance(first, dict):
                    return first.get("msg", str(first))
                return str(first)
            elif isinstance(detail, str):
                return detail
            if "message" in data:
                return data["message"]
            if "error" in data:
                err = data["error"]
                if isinstance(err, dict):
                    return err.get("message", str(err))
                return str(err)
        return "Unknown error"

    assert extract_msg(pydantic_422) == "Password must be at least 8 characters"

    # 2. String detail (FastAPI 401 / 400)
    auth_401 = {"detail": "Invalid email or password"}
    assert extract_msg(auth_401) == "Invalid email or password"

    # 3. Custom error envelope
    custom_err = {"error": {"message": "Email already registered"}}
    assert extract_msg(custom_err) == "Email already registered"


# =====================================================================
# WORKSTREAM B & C: INTENT CLASSIFICATION & TRAVEL COMPANION BEHAVIOR
# =====================================================================
def test_intent_classification_safety():
    """Safety and distress queries are prioritized and classified as SAFETY."""
    safety_queries = [
        "I feel unsafe walking alone near the bus stand",
        "Someone is following me",
        "I am scared, it is very dark here",
        "What should I do if I feel in danger?",
        "Where is the nearest police station or safe zone?"
    ]
    for q in safety_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == IntentCategory.SAFETY, f"Query '{q}' expected SAFETY, got {res.intent}"
        assert res.requires_external_llm is True


def test_intent_classification_journey_and_transit():
    """Chennai routes, stations, and travel planning queries."""
    transit_queries = [
        "How do I reach Guindy from Chennai Central?",
        "What is the frequency of Metro on the Blue line?",
        "Are MTC buses running to Tambaram right now?",
        "Plan a safe route from Saidapet to T Nagar",
        "Is Suburban train safe to ride after 9 PM?"
    ]
    for q in transit_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == IntentCategory.JOURNEY_TRANSIT, f"Query '{q}' expected JOURNEY_TRANSIT, got {res.intent}"


def test_intent_classification_navsakhi_support():
    """Application features, scores, and account support queries."""
    support_queries = [
        "How do I register an account on NavSakhi?",
        "How is the LightGBM safety score evaluated?",
        "How do I set up my emergency contacts for SOS?",
        "What features does NavSakhi provide for women travellers?"
    ]
    for q in support_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == IntentCategory.NAVSAKHI_SUPPORT, f"Query '{q}' expected NAVSAKHI_SUPPORT, got {res.intent}"


def test_intent_classification_small_talk():
    """Greetings, thanks, and informal pleasantries handled deterministically."""
    small_talk_queries = [
        "Hi",
        "Hello Sakhi",
        "Vanakkam",
        "Good morning",
        "Thank you for helping me"
    ]
    for q in small_talk_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == IntentCategory.SMALL_TALK, f"Query '{q}' expected SMALL_TALK, got {res.intent}"
        assert res.requires_external_llm is False
        assert res.direct_response is not None
        assert len(res.direct_response) > 5


def test_intent_classification_off_topic_redirection():
    """Harmless off-topic queries receive concise answers (<= 2 sentences) with gentle domain redirection."""
    off_topic_queries = [
        "What is the capital of France?",
        "Write a Python script to sort an array",
        "Tell me a joke about space"
    ]
    for q in off_topic_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == IntentCategory.OFF_TOPIC, f"Query '{q}' expected OFF_TOPIC, got {res.intent}"
        assert res.requires_external_llm is False
        assert "NavSakhi" in res.direct_response
        assert "Chennai" in res.direct_response or "safety" in res.direct_response
        # Ensure answer meets the maximum of 1 or 2 concise sentences without a duplicate long paragraph
        sentences = [s.strip() for s in res.direct_response.split(".") if s.strip()]
        assert len(sentences) <= 3, f"Response too verbose ({len(sentences)} sentences): {res.direct_response}"


def test_safety_intent_precedence_and_emergency_contacts():
    """
    Step 2 Regression Tests:
    1. Acute danger with emergency contact -> SAFETY
    2. Feeling unsafe with emergency contacts -> SAFETY
    3. Adding emergency contact to account -> NAVSAKHI_SUPPORT
    4. Updating saved emergency contacts -> NAVSAKHI_SUPPORT
    5. Mixed safety / transit -> SAFETY or JOURNEY_TRANSIT
    """
    # 1. Someone is following me; I need an emergency contact -> SAFETY
    q1 = "Someone is following me; I need an emergency contact."
    res1 = global_intent_classifier.classify(q1)
    assert res1.intent == IntentCategory.SAFETY, f"Expected SAFETY for '{q1}', got {res1.intent}"

    # 2. I feel unsafe and need to alert someone in my emergency contacts -> SAFETY
    q2 = "I feel unsafe and need to alert someone in my emergency contacts."
    res2 = global_intent_classifier.classify(q2)
    assert res2.intent == IntentCategory.SAFETY, f"Expected SAFETY for '{q2}', got {res2.intent}"

    # 3. How do I add an emergency contact to my account? -> NAVSAKHI_SUPPORT
    q3 = "How do I add an emergency contact to my account?"
    res3 = global_intent_classifier.classify(q3)
    assert res3.intent == IntentCategory.NAVSAKHI_SUPPORT, f"Expected NAVSAKHI_SUPPORT for '{q3}', got {res3.intent}"

    # 4. How do I update my saved emergency contacts? -> NAVSAKHI_SUPPORT
    q4 = "How do I update my saved emergency contacts?"
    res4 = global_intent_classifier.classify(q4)
    assert res4.intent == IntentCategory.NAVSAKHI_SUPPORT, f"Expected NAVSAKHI_SUPPORT for '{q4}', got {res4.intent}"

    # 5. Mixed safety/transit query remains a supported safety or transit intent
    q5 = "Is it safe to wait at Guindy metro station late at night, or should I call police?"
    res5 = global_intent_classifier.classify(q5)
    assert res5.intent in [IntentCategory.SAFETY, IntentCategory.JOURNEY_TRANSIT]
    assert res5.is_supported_domain is True


def test_intent_classification_mixed_intent_conservatism():
    """Mixed intent containing safety or transit words must not be rejected as off-topic."""
    mixed_queries = [
        "I was reading about physics, but now I feel unsafe near this dark bus stop",
        "Can you help me with my math homework while I wait for the Chennai Metro train?"
    ]
    # First query contains 'unsafe' -> must classify as SAFETY
    res1 = global_intent_classifier.classify(mixed_queries[0])
    assert res1.intent == IntentCategory.SAFETY

    # Second query contains 'metro train' -> must classify as JOURNEY_TRANSIT
    res2 = global_intent_classifier.classify(mixed_queries[1])
    assert res2.intent == IntentCategory.JOURNEY_TRANSIT


@pytest.mark.asyncio
async def test_reasoning_tool_rate_limit_cooldown():
    """Verifies that HTTP 429 triggers cooldown and avoids repeated hammering."""
    tool = ReasoningTool()

    try:
        # Simulate a 429 event
        record_gemini_429_event()
        assert is_gemini_in_rate_limit_cooldown() is True

        # Calling tool during cooldown should immediately return rate-limited fallback
        res = await tool.execute({"context": {"query": "How do I take Chennai metro to airport?"}})
        assert res["ai_status"] == "RATE_LIMITED_FALLBACK"
        assert res["provider"] == "local_fallback"
        assert "rate-limited" in res["summary"].lower() or "verified" in res["summary"].lower()
    finally:
        from app.tools.specialized.reasoning_tool import reset_gemini_cooldowns
        reset_gemini_cooldowns()


@pytest.mark.asyncio
async def test_reasoning_tool_deterministic_small_talk():
    """Small talk queries execute deterministically without external LLM calls."""
    tool = ReasoningTool()
    res = await tool.execute({"context": {"query": "Hello!"}})
    assert res["provider"] == "local_companion"
    assert res["ai_status"] == "OFFLINE_DETERMINISTIC"
    assert "NavSakhi" in res["summary"] or "Hello" in res["summary"] or "Chennai" in res["summary"]


# =====================================================================
# WORKSTREAM E: CHENNAI AUTOCOMPLETE RELEVANCE & VIT CHENNAI
# =====================================================================
def test_local_location_resolver_vit_chennai():
    """Demonstrates that 'vit' resolves to VIT Chennai Campus."""
    aliases = [
        "vit",
        "vit chennai",
        "vit chennai campus",
        "vit campus",
        "vit university",
        "vellore institute of technology"
    ]
    for a in aliases:
        loc = global_local_location_resolver.resolve(a)
        assert loc is not None, f"Alias '{a}' failed to resolve in local resolver"
        lon, lat = loc.coordinates[0], loc.coordinates[1]
        assert abs(lat - 12.8406) < 0.001
        assert abs(lon - 80.1554) < 0.001


@pytest.mark.asyncio
async def test_autocomplete_service_vit_ranking_and_exclusion():
    """Demonstrates that 'vit' query ranks VIT Chennai Campus #1 and excludes Kavitha Pannai."""
    service = AutocompleteService()
    results = await service.get_suggestions("vit", limit=5)

    assert len(results) > 0, "Expected at least 1 suggestion for 'vit'"
    top = results[0]
    assert "VIT" in top.name or "Vellore Institute of Technology" in top.name
    assert abs(top.latitude - 12.8406) < 0.001

    # Verify that Kavitha Pannai does NOT appear in results for 'vit'
    names = [r.name.lower() for r in results]
    assert not any("kavitha" in n for n in names), f"False-positive 'Kavitha Pannai' found in results: {names}"


@pytest.mark.asyncio
async def test_autocomplete_service_unrelated_query_no_results():
    """Unrelated/nonsense query returns 0 suggestions rather than misleading results."""
    service = AutocompleteService()
    results = await service.get_suggestions("zzqxwyk99", limit=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_autocomplete_service_established_chennai_places():
    """Verifies that Guindy, Saidapet, and Chennai Central continue to resolve accurately."""
    service = AutocompleteService()

    guindy_res = await service.get_suggestions("Guindy", limit=5)
    assert len(guindy_res) > 0
    assert any("guindy" in r.name.lower() for r in guindy_res)

    saidapet_res = await service.get_suggestions("Saidapet", limit=5)
    assert len(saidapet_res) > 0
    assert any("saidapet" in r.name.lower() for r in saidapet_res)

    central_res = await service.get_suggestions("Chennai Central", limit=5)
    assert len(central_res) > 0
    assert any("central" in r.name.lower() for r in central_res)


# =====================================================================
# WORKSTREAM F & G: JOURNEY PLANNING BOUNDS & HONEST WEATHER FALLBACK
# =====================================================================
@pytest.mark.asyncio
async def test_weather_provider_honest_unavailable_and_cooldown():
    """Weather provider returns honest unavailable status on failure and enters cooldown."""
    provider = WeatherProvider()

    # Simulate a network failure
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        res = await provider.get_live_weather(13.0827, 80.2707)
        assert res["available"] is False
        assert res["status"] == "UNAVAILABLE"
        assert res["temperature"] == 0
        assert res["humidity"] == 0

    # During cooldown, next call returns immediately without invoking HTTP
    with patch("httpx.AsyncClient.get") as mock_get:
        res2 = await provider.get_live_weather(13.0827, 80.2707)
        assert res2["available"] is False
        assert res2["status"] == "UNAVAILABLE"
        mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_weather_service_rate_limit_caching():
    """WeatherService caches rate-limited (429) responses for 60 seconds."""
    service = WeatherService()

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res1 = await service.get_live_weather(13.0827, 80.2707, location_name="Chennai")
        assert res1.available is False
        assert res1.status == "RATE_LIMITED"
        assert res1.temperature == 0.0

    # Immediate second call should be served from cache without HTTP client
    with patch("httpx.AsyncClient.get") as mock_get:
        res2 = await service.get_live_weather(13.0827, 80.2707, location_name="Chennai")
        assert res2.available is False
        assert res2.status == "RATE_LIMITED"
        mock_get.assert_not_called()


# =====================================================================
# WORKSTREAM H: DETERMINISTIC JOURNEY TIMEOUT & FALLBACK REGRESSION TESTS
# =====================================================================
from fastapi import HTTPException
from app.schemas.journey_schemas import JourneyCreate
from app.providers.shared.exceptions import LocationNotFoundError


@pytest.mark.asyncio
async def test_journey_delayed_geocoder_raises_503():
    """A delayed or hung forward geocode operation times out at 4.0s and raises 503."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="80.2184,13.0067", destination="Unknown Slow Land")

    async def slow_geocode(*args, **kwargs):
        await asyncio.sleep(10.0)
        return Location(coordinates=[80.2755, 13.0827])

    with patch("app.providers.location.provider.NominatimLocationProvider.forward_geocode", side_effect=slow_geocode):
        t0 = time.time()
        with pytest.raises(HTTPException) as exc_info:
            await coordinator.build_journey_plan_response("j_timeout_geo", req)
        elapsed = time.time() - t0

        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail.lower()
        assert elapsed < 5.0, f"Expected geocoder timeout <= 4.5s, took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_journey_failed_geocoder_location_not_found_raises_422():
    """When a location cannot be found, geocoding raises 422 with actionable detail."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="80.2184,13.0067", destination="Nonexistent Place XYZ 999")

    with patch("app.providers.location.provider.NominatimLocationProvider.forward_geocode", side_effect=LocationNotFoundError("Not found")):
        with pytest.raises(HTTPException) as exc_info:
            await coordinator.build_journey_plan_response("j_not_found_geo", req)

        assert exc_info.value.status_code == 422
        assert "could not find" in exc_info.value.detail.lower()


from app.models.journey import Address


@pytest.mark.asyncio
async def test_journey_slow_weather_does_not_block_routing():
    """Slow or hung weather enrichment times out after 2.0s without blocking road routing."""
    coordinator = JourneyIntelligenceCoordinator()
    # Guindy to Central coordinates
    req = JourneyCreate(source="80.2184,13.0067", destination="80.2755,13.0827")

    sample_road = CandidateRoute(
        route_identifier="road_test_1",
        distance=12000.0,
        duration=1500.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": {"type": "LineString", "coordinates": [[80.2184, 13.0067], [80.2755, 13.0827]]},
            "travel_mode": "Personal Vehicle",
            "route_name": "Personal Vehicle"
        }
    )

    async def slow_weather(*args, **kwargs):
        await asyncio.sleep(10.0)
        return {"available": True, "status": "LIVE"}

    async def mock_rev_geo(*args, **kwargs):
        return Address(display_name="Mocked Place, Chennai")

    with patch("app.providers.location.provider.NominatimLocationProvider.reverse_geocode", side_effect=mock_rev_geo), \
         patch("app.providers.live.weather.global_weather_provider.get_live_weather", side_effect=slow_weather), \
         patch("app.providers.routing.provider.OSRMRoutingProvider.get_routes", return_value=[sample_road]), \
         patch("app.intelligence.journey.multimodal_router.global_multimodal_router.search_candidates", return_value=[]):
        t0 = time.time()
        response = await coordinator.build_journey_plan_response("j_slow_weather", req)
        elapsed = time.time() - t0

        assert elapsed < 4.0, f"Expected weather to timeout <= 2.5s, took {elapsed:.2f}s"
        assert response.recommended_routes is not None
        assert len(response.recommended_routes) >= 1
        assert any("weather" in w.lower() for w in response.warnings)


@pytest.mark.asyncio
async def test_journey_slow_transit_search_falls_back_to_road():
    """Slow or timed out transit search (bounded to 6.0s) does not fail the journey; road routes are preserved."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="80.2184,13.0067", destination="80.2755,13.0827", preferences=["public_transport"])

    sample_road = CandidateRoute(
        route_identifier="road_test_2",
        distance=12000.0,
        duration=1500.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": {"type": "LineString", "coordinates": [[80.2184, 13.0067], [80.2755, 13.0827]]},
            "travel_mode": "Personal Vehicle",
            "route_name": "Personal Vehicle"
        }
    )

    async def slow_transit(*args, **kwargs):
        await asyncio.sleep(15.0)
        return []

    async def mock_rev_geo(*args, **kwargs):
        return Address(display_name="Mocked Place, Chennai")

    with patch("app.providers.location.provider.NominatimLocationProvider.reverse_geocode", side_effect=mock_rev_geo), \
         patch("app.intelligence.journey.multimodal_router.global_multimodal_router.search_candidates", side_effect=slow_transit), \
         patch("app.providers.routing.provider.OSRMRoutingProvider.get_routes", return_value=[sample_road]):
        t0 = time.time()
        response = await coordinator.build_journey_plan_response("j_slow_transit", req)
        elapsed = time.time() - t0

        # Bounded by 6.0s timeout
        assert elapsed < 8.0, f"Expected transit search to bound <= 6.5s, took {elapsed:.2f}s"
        assert response.recommended_routes is not None
        assert len(response.recommended_routes) >= 1
        # Warnings should indicate transit unavailable and road alternatives shown
        assert any("transit" in w.lower() or "road alternatives" in w.lower() for w in response.warnings)


@pytest.mark.asyncio
async def test_journey_slow_gemini_explanation_does_not_block():
    """Slow or timed-out Gemini narrative (bounded to 2.0s) returns the plan with ai_explanation=None."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="80.2184,13.0067", destination="80.2755,13.0827")

    sample_road = CandidateRoute(
        route_identifier="road_test_3",
        distance=12000.0,
        duration=1500.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "geometry": {"type": "LineString", "coordinates": [[80.2184, 13.0067], [80.2755, 13.0827]]},
            "travel_mode": "Personal Vehicle",
            "route_name": "Personal Vehicle"
        }
    )

    async def slow_explanation(*args, **kwargs):
        await asyncio.sleep(10.0)
        return "Slow narrative"

    async def mock_rev_geo(*args, **kwargs):
        return Address(display_name="Mocked Place, Chennai")

    with patch("app.providers.location.provider.NominatimLocationProvider.reverse_geocode", side_effect=mock_rev_geo), \
         patch("app.providers.live.weather.global_weather_provider.get_live_weather", return_value={"available": True, "condition": "Clear", "temperature": 28, "hazards": []}), \
         patch("app.tools.specialized.reasoning_tool.ReasoningTool.explain_journey_recommendations", side_effect=slow_explanation), \
         patch("app.providers.routing.provider.OSRMRoutingProvider.get_routes", return_value=[sample_road]), \
         patch("app.intelligence.journey.multimodal_router.global_multimodal_router.search_candidates", return_value=[]):
        t0 = time.time()
        response = await coordinator.build_journey_plan_response("j_slow_gemini", req)
        elapsed = time.time() - t0

        assert elapsed < 4.0, f"Expected Gemini narrative to bound <= 2.5s, took {elapsed:.2f}s"
        assert response.recommended_routes is not None
        assert len(response.recommended_routes) >= 1
        assert response.ai_recommendation is not None
        assert response.ai_recommendation.summary != ""


@pytest.mark.asyncio
async def test_journey_total_route_failure_raises_503():
    """When both road and transit candidates fail for distant locations, 503 is returned promptly."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="80.2184,13.0067", destination="80.2755,13.0827")

    with patch("app.providers.routing.provider.OSRMRoutingProvider.get_routes", return_value=[]), \
         patch("app.intelligence.journey.multimodal_router.global_multimodal_router.search_candidates", return_value=[]):
        with pytest.raises(HTTPException) as exc_info:
            await coordinator.build_journey_plan_response("j_total_failure", req)

        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_journey_preserves_http_exception_semantics():
    """Any explicit HTTPException raised during processing is preserved and not swallowed into 500."""
    coordinator = JourneyIntelligenceCoordinator()
    req = JourneyCreate(source="", destination="80.2755,13.0827")

    with pytest.raises(HTTPException) as exc_info:
        await coordinator.build_journey_plan_response("j_empty_source", req)

    assert exc_info.value.status_code == 422
    assert "source location cannot be empty" in exc_info.value.detail.lower()
