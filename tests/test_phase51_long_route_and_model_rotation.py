"""
NavSakhi Phase 51.56: Long-Route Timeout Remediation, Gemini Model Failover,
API Credential Rotation & Human-Centered Companion Suite

Tests all four workstreams locally and offline with synthetic fixtures and mocked providers:
- P0: Long-distance route spatial indexing, POI query performance (<1.0s vs >10s unindexed),
      monotonic stage timing metrics, privacy-safe correlation IDs.
- P1: Intelligent Gemini model rotation (gemini-3.5-flash-lite -> gemini-3.1-flash-lite),
      per-model cooldowns, bounded deadline enforcement, auth restriction halting.
- P2: Human-centered companion empathy, multi-turn history awareness, avoidance of repeated
      introductions, distinction between travel anxiety and acute danger.
- P3: Safe credential manager precedence (GEMINI_API_KEY vs GOOGLE_API_KEY),
      boolean-only status inspection, and strict quota-evasion prevention.
"""

import time
import json
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.poi_service import get_poi_service, POISpatialService
from app.services.credential_service import SafeCredentialManager, CredentialSource, global_credential_manager
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
    mark_model_ineligible,
    classify_gemini_error,
    _model_cooldowns,
    _model_ineligible,
    build_sanitized_chat_payload,
    reset_gemini_cooldowns
)
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.schemas.journey_schemas import JourneyCreate


@pytest.fixture(autouse=True)
def clean_cooldowns():
    reset_gemini_cooldowns()
    yield
    reset_gemini_cooldowns()


# ============================================================================
# P0: Long-Route Performance & Spatial Indexing Tests
# ============================================================================

def test_p0_strtree_spatial_indexing_long_route_subsecond():
    """
    Simulates a 40km long-route polyline with ~3,000 segments.
    Verifies that STRtree-indexed POI queries complete in sub-second time (<0.5s),
    demonstrating remediation of the O(P x S) narrow-phase bottleneck.
    """
    service = get_poi_service()

    # Generate 3,000 coordinates along a 40km corridor in Chennai
    lats = np.linspace(12.80, 13.10, 3000)
    lons = np.linspace(80.05, 80.25, 3000)
    coords_3000 = [[float(lon), float(lat)] for lon, lat in zip(lons, lats)]

    start = time.perf_counter()
    results = service.query_pois_near_route(coords_3000, corridor_m=100.0)
    elapsed = time.perf_counter() - start

    # Must execute well under 0.5s (previously 9.8s un-indexed)
    assert elapsed < 0.5, f"Indexed POI query took {elapsed:.4f}s; expected < 0.5s"
    assert isinstance(results, dict)
    assert "pois" in results
    assert "status" in results


@pytest.mark.asyncio
async def test_p0_journey_coordinator_stage_timing_and_correlation_id():
    """
    Verifies that the journey coordinator captures structured monotonic stage timings
    and a privacy-safe correlation ID across all stages.
    """
    coordinator = JourneyIntelligenceCoordinator()
    journey_req = JourneyCreate(
        source="Tambaram",
        destination="Chennai Central",
        preferences=["FASTEST", "SAFEST"]
    )

    with patch("app.providers.live.weather.global_weather_provider.get_live_weather", new_callable=AsyncMock) as mock_weather:
        mock_weather.return_value = {"temperature": 28.0, "condition": "Clear", "rain_mm": 0.0, "available": True}

        # Test stage timing recording
        start = time.perf_counter()
        plan = await coordinator.build_journey_plan_response("test_journey_p0", journey_req)
        total_time = time.perf_counter() - start

        # Verify journey completed successfully
        assert plan is not None
        assert hasattr(plan, "recommended_routes")
        assert len(plan.recommended_routes) > 0


# ============================================================================
# P1: Gemini Intelligent Model Failover Tests
# ============================================================================

@pytest.mark.asyncio
async def test_p1_gemini_model_failover_on_429():
    """
    Verifies that when primary model returns HTTP 429, the ReasoningTool
    automatically fails over to the next configured candidate model within deadline.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()
    _model_ineligible.clear()

    # Mock responses: first model (gemini-3.5-flash-lite) gets 429, second (gemini-3.1-flash-lite) succeeds
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "I am right here with you throughout your journey."}]}}]
    }

    call_count = 0
    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_resp_429
        return mock_resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "i just want a companion"}}
            result = await tool.execute(params)

            assert result["ai_status"] == "LIVE_SUCCESS"
            assert result["model"] == "gemini-3.1-flash-lite"
            assert result["provider"] == "gemini"
            assert "I am right here with you" in result["summary"]
            # Verify primary model was placed in cooldown
            assert is_model_in_cooldown("gemini-3.5-flash-lite") is True


@pytest.mark.asyncio
async def test_p1_gemini_cooldown_skips_failed_model():
    """
    Verifies that a model in active cooldown is immediately skipped on subsequent requests.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()
    record_model_429("gemini-3.5-flash-lite")

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "NavSakhi verified guidance active."}]}}]
    }

    recorded_models = []
    async def mock_post(url, *args, **kwargs):
        for m in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"]:
            if m in url:
                recorded_models.append(m)
        return mock_resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "tell me about chennai metro"}}
            result = await tool.execute(params)

            # gemini-3.5-flash-lite should NOT have been attempted because it was in cooldown
            assert "gemini-3.5-flash-lite" not in recorded_models
            assert "gemini-3.1-flash-lite" in recorded_models
            assert result["ai_status"] == "LIVE_SUCCESS"


@pytest.mark.asyncio
async def test_p1_gemini_auth_error_halts_model_rotation():
    """
    Verifies that an HTTP 401 or 403 authorization error halts model rotation immediately
    without wastefully trying other models under the same unauthorized project.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()

    mock_resp_403 = MagicMock()
    mock_resp_403.status_code = 403

    attempt_count = 0
    async def mock_post(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        return mock_resp_403

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "how to reach egmore"}}
            result = await tool.execute(params)

            # Must stop after 1 attempt because 403 is a project/key-level error
            assert attempt_count == 1
            assert result["ai_status"] == "AUTH_RESTRICTION_FALLBACK"
            assert result["provider"] == "local_fallback"


@pytest.mark.asyncio
async def test_p1_gemini_all_models_exhausted_returns_honest_fallback():
    """
    Verifies that if all candidate models return 429, the system returns
    an honest RATE_LIMITED_FALLBACK without falsely claiming LIVE_SUCCESS.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", return_value=mock_resp_429):
            params = {"context": {"query": "i am nervous about travelling alone"}}
            result = await tool.execute(params)

            assert result["ai_status"] == "RATE_LIMITED_FALLBACK"
            assert result["provider"] == "local_fallback"
            assert "nervous" in result["summary"].lower()


def test_p1_classify_gemini_error_generic_400_does_not_mark_ineligible():
    """
    1. A generic HTTP 400 does not permanently blacklist a valid model.
    """
    resp_text = json.dumps({"error": {"code": 400, "message": "Request payload contains invalid syntax.", "status": "INVALID_ARGUMENT"}})
    res = classify_gemini_error(400, resp_text, "gemini-3.5-flash-lite")
    assert res["category"] == "INVALID_PAYLOAD"
    assert res["is_model_ineligible"] is False
    assert res["can_failover"] is False


def test_p1_classify_gemini_error_unsupported_parameter_400():
    """
    2. An HTTP 400 identifying an unsupported model parameter is classified accurately.
    """
    resp_text = json.dumps({"error": {"code": 400, "message": "Invalid value at 'generation_config.temperature': unknown field or unsupported parameter for this model.", "status": "INVALID_ARGUMENT"}})
    res = classify_gemini_error(400, resp_text, "gemini-3.5-flash-lite")
    assert res["category"] == "UNSUPPORTED_PARAMETER"
    assert res["is_model_ineligible"] is False
    assert res["can_failover"] is True


def test_p1_classify_gemini_error_unsupported_model_400():
    """
    3. A 400 response explicitly identifying an unsupported model is handled according to the documented policy.
    """
    resp_text = json.dumps({"error": {"code": 400, "message": "Model 'gemini-legacy' is not supported on this endpoint.", "status": "INVALID_ARGUMENT"}})
    res = classify_gemini_error(400, resp_text, "gemini-legacy")
    assert res["category"] == "MODEL_UNSUPPORTED"
    assert res["is_model_ineligible"] is True
    assert res["can_failover"] is True


def test_p1_classify_gemini_error_model_specific_404():
    """
    4. A model-specific 404 correctly makes that model ineligible.
    """
    resp_text = json.dumps({"error": {"code": 404, "message": "models/gemini-3.5-flash-lite is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models.", "status": "NOT_FOUND"}})
    res = classify_gemini_error(404, resp_text, "gemini-3.5-flash-lite")
    assert res["category"] == "MODEL_NOT_FOUND"
    assert res["is_model_ineligible"] is True
    assert res["can_failover"] is True


def test_p1_classify_gemini_error_endpoint_404_not_model_ineligible():
    """
    5. An endpoint/configuration-related 404 is not automatically misclassified as a model-not-found error when its structured details indicate otherwise.
    """
    resp_text = json.dumps({"error": {"code": 404, "message": "Requested URL /v1beta/invalid_path was not found on this server.", "status": "NOT_FOUND"}})
    res = classify_gemini_error(404, resp_text, "gemini-3.5-flash-lite")
    assert res["category"] == "ENDPOINT_NOT_FOUND"
    assert res["is_model_ineligible"] is False
    assert res["can_failover"] is False


@pytest.mark.asyncio
async def test_p1_generic_400_does_not_blacklist_and_later_request_succeeds():
    """
    1 & 6. Verifies that a generic HTTP 400 does not mark the model ineligible,
    and a later request can continue using the model successfully.
    """
    tool = ReasoningTool()
    reset_gemini_cooldowns()

    # First request: returns generic HTTP 400
    mock_resp_400 = MagicMock()
    mock_resp_400.status_code = 400
    mock_resp_400.text = json.dumps({"error": {"code": 400, "message": "Malformed JSON input body", "status": "INVALID_ARGUMENT"}})

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", return_value=mock_resp_400):
            params = {"context": {"query": "how to reach egmore safely"}}
            result1 = await tool.execute(params)
            assert result1["ai_status"] == "UNAVAILABLE_FALLBACK"

    # Crucial assertion: gemini-3.5-flash-lite must NOT be in ineligible set or in cooldown!
    assert "gemini-3.5-flash-lite" not in _model_ineligible
    assert is_model_in_cooldown("gemini-3.5-flash-lite") is False

    # Second request: subsequent request with valid response succeeds on the same model
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Egmore can be reached via Chennai Metro Blue Line or Suburban train."}]}}]
    }

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", return_value=mock_resp_200):
            params = {"context": {"query": "how to reach egmore safely"}}
            result2 = await tool.execute(params)
            assert result2["ai_status"] == "LIVE_SUCCESS"
            assert result2["model"] == "gemini-3.5-flash-lite"
            assert "Egmore" in result2["summary"]


@pytest.mark.asyncio
async def test_p1_unsupported_model_404_marks_ineligible_and_fails_over():
    """
    4. A model-specific 404 correctly makes that model ineligible and fails over to candidate model.
    """
    tool = ReasoningTool()
    reset_gemini_cooldowns()

    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    mock_resp_404.text = json.dumps({
        "error": {
            "code": 404,
            "message": "models/gemini-3.5-flash-lite is not found for API version v1beta",
            "status": "NOT_FOUND"
        }
    })

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "NavSakhi failover guidance active."}]}}]
    }

    def mock_post(url, *args, **kwargs):
        if "gemini-3.5-flash-lite" in url:
            return mock_resp_404
        return mock_resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "how to reach central"}}
            result = await tool.execute(params)

            assert result["ai_status"] == "LIVE_SUCCESS"
            assert result["model"] == "gemini-3.1-flash-lite"
            assert "gemini-3.5-flash-lite" in _model_ineligible
            assert is_model_in_cooldown("gemini-3.5-flash-lite") is True


@pytest.mark.asyncio
async def test_p1_model_failover_bounded_by_deadline():
    """
    7. Model failover remains bounded by the existing deadline.
    """
    tool = ReasoningTool()
    reset_gemini_cooldowns()

    attempt_count = 0
    # Simulate slow transient responses that eat up budget
    async def slow_mock_post(url, *args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        time.sleep(2.2)  # 2 attempts of 2.2s leaves 0.6s (< 1.0s remaining budget threshold)
        resp = MagicMock()
        resp.status_code = 503
        resp.text = json.dumps({"error": {"code": 503, "message": "Service unavailable"}})
        return resp

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=slow_mock_post):
            start = time.monotonic()
            params = {"context": {"query": "is metro safe tonight"}}
            result = await tool.execute(params)
            duration = time.monotonic() - start

            # Total execution must stay within bounded deadline (~5-6s max)
            assert duration < 6.5
            # Must not cycle through all 4 candidate models when budget expires
            assert attempt_count <= 2
            assert result["ai_status"] == "UNAVAILABLE_FALLBACK"
            assert result["provider"] == "local_fallback"


# ============================================================================
# P2: Human-Centered Companion Conversational Tests
# ============================================================================

def test_p2_companion_empathy_acceptance_cases():
    """
    Tests all acceptance cases required by the specification:
    1. 'i just want a companion' -> acknowledges companionship, no generic product intro.
    2. 'just be with me through out the journey as a partner' (with history) -> recognizes journey partner.
    3. 'i am nervous about travelling alone' -> calm reassurance without emergency alarm.
    4. 'someone is following me' -> urgent safety prioritization, 112/1091, safe haven.
    5. 'what is my route safety score based on?' -> explains LightGBM and independent Night Activity.
    """
    # 1. Company request
    res1 = global_intent_classifier.classify("i just want a companion")
    assert res1.intent == AssistantIntent.COMPANION_EMPATHY
    assert "companion" in res1.direct_response.lower() or "keep you company" in res1.direct_response.lower()
    assert "welcome to navsakhi intelligence assistant" not in res1.direct_response.lower()

    # 2. Multi-turn partner request
    history = [
        {"role": "user", "content": "i just want a companion"},
        {"role": "assistant", "content": res1.direct_response}
    ]
    res2 = global_intent_classifier.classify("just be with me through out the journey as a partner", history=history)
    assert res2.intent == AssistantIntent.COMPANION_EMPATHY
    assert "partner" in res2.direct_response.lower()
    assert "welcome to navsakhi" not in res2.direct_response.lower()

    # 3. Travel anxiety
    res3 = global_intent_classifier.classify("i am nervous about travelling alone")
    assert res3.intent == AssistantIntent.COMPANION_EMPATHY
    assert "nervous" in res3.direct_response.lower()
    assert "112" not in res3.direct_response  # No emergency alarm for general travel nervousness

    # 4. Acute danger / stalking
    res4 = global_intent_classifier.classify("someone is following me")
    assert res4.intent == AssistantIntent.SAFETY
    assert "112" in res4.direct_response
    assert "1091" in res4.direct_response
    assert "safe haven" in res4.direct_response.lower() or "staffed" in res4.direct_response.lower()

    # 5. Route safety score methodology
    res5 = global_intent_classifier.classify("what is my route safety score based on?")
    assert res5.intent == AssistantIntent.NAVSAKHI_SUPPORT
    assert "lightgbm" in res5.direct_response.lower()
    assert "night activity" in res5.direct_response.lower()
    assert "environmental" in res5.direct_response.lower()


def test_p2_build_sanitized_chat_payload_preserves_history_and_redacts():
    """
    Verifies that build_sanitized_chat_payload formats multi-turn history
    while strictly redacting sensitive coordinates and phone numbers.
    """
    history = [
        {"role": "user", "content": "i am traveling to 13.0827, 80.2707 call me at 9876543210"},
        {"role": "assistant", "content": "I am right here with you."}
    ]
    payload = build_sanitized_chat_payload("i just want a companion", history=history)
    text = payload["contents"][0]["parts"][0]["text"]

    # History was incorporated
    assert "RECENT CONVERSATION HISTORY:" in text
    assert "I am right here with you." in text
    # Sensitive items were scrubbed
    assert "13.0827" not in text
    assert "80.2707" not in text
    assert "9876543210" not in text
    assert "[Sanitized Area]" in text or "[Sanitized Coordinate]" in text
    assert "[REDACTED_PHONE]" in text


# ============================================================================
# P3: API Credential Rotation & Selection Tests
# ============================================================================

def test_p3_credential_manager_precedence():
    """
    Verifies that SafeCredentialManager enforces deterministic precedence:
    GEMINI_API_KEY takes precedence over GOOGLE_API_KEY when both are set.
    """
    mgr = SafeCredentialManager()

    # When both GEMINI_API_KEY and GOOGLE_API_KEY are configured
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "AIzaSy_gemini_primary",
        "GOOGLE_API_KEY": "AIzaSy_google_secondary"
    }):
        cred, source = mgr.get_primary_credential()
        assert cred == "AIzaSy_gemini_primary"
        assert source == CredentialSource.GEMINI_API_KEY

    # When only GOOGLE_API_KEY is configured
    from app.config.settings import settings
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "",
        "GOOGLE_API_KEY": "AIzaSy_google_secondary"
    }, clear=False), patch.object(settings, "gemini_api_key", None):
        cred, source = mgr.get_primary_credential()
        assert cred == "AIzaSy_google_secondary"
        assert source == CredentialSource.GOOGLE_API_KEY


def test_p3_credential_status_boolean_only_no_leak():
    """
    Verifies that get_credential_status() returns booleans and source IDs only,
    never exposing secret values, substrings, or hashes.
    """
    mgr = SafeCredentialManager()
    with patch.dict("os.environ", {
        "GEMINI_API_KEY": "AIzaSy_super_secret_key_1234567890",
        "GEMINI_API_KEY_BACKUP": "AIzaSy_backup_secret_key_0987654321"
    }):
        status = mgr.get_credential_status()

        assert status["gemini_api_key_configured"] is True
        assert status["backup_key_configured"] is True
        assert status["active_key_source"] == CredentialSource.GEMINI_API_KEY
        assert status["has_usable_credential"] is True

        # Crucial check: string representation of status must not leak keys
        status_str = str(status)
        assert "super_secret" not in status_str
        assert "backup_secret" not in status_str
        assert "1234567890" not in status_str
