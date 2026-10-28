import pytest
import asyncio
import httpx
import json
import time
from unittest.mock import patch, AsyncMock, MagicMock

from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    classify_gemini_error,
    get_configured_gemini_models,
    reset_gemini_cooldowns
)
from app.services.assistant_intent_service import (
    global_intent_classifier,
    AssistantIntent
)
from app.intelligence.response.builder import ResponseBuilder


@pytest.fixture(autouse=True)
def clean_cooldowns():
    reset_gemini_cooldowns()
    yield
    reset_gemini_cooldowns()


@pytest.fixture
def reasoning_tool():
    return ReasoningTool()


# =========================================================================
# 1. CANDIDATE LADDER & 2-MODEL MAXIMUM
# =========================================================================

def test_candidate_models_capped_at_two():
    """Verify that candidate models are strictly capped at 2 candidates."""
    models = get_configured_gemini_models()
    assert len(models) <= 2
    assert models[0] in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]


# =========================================================================
# 2. ERROR CLASSIFICATION BOUNDARIES
# =========================================================================

def test_classify_api_key_invalid():
    """HTTP 400 with API_KEY_INVALID in details must be classified as credential failure with NO failover."""
    payload = json.dumps({
        "error": {
            "code": 400,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "INVALID_ARGUMENT",
            "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": "API_KEY_INVALID"}]
        }
    })
    res = classify_gemini_error(400, payload, "gemini-3.5-flash-lite")
    assert res["category"] == "AUTH_RESTRICTION"
    assert res["is_credential_failure"] is True
    assert res["can_failover"] is False


def test_classify_http_402_billing():
    """HTTP 402 or billing depletion must NOT failover to alternate candidate."""
    payload = json.dumps({
        "error": {
            "code": 402,
            "message": "Project billing quota exhausted.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    res = classify_gemini_error(402, payload, "gemini-3.5-flash-lite")
    assert res["category"] == "BILLING_DEPLETED"
    assert res["can_failover"] is False


def test_classify_shared_quota_429():
    """HTTP 429 for shared project quota must NOT rotate models blindly."""
    payload = json.dumps({
        "error": {
            "code": 429,
            "message": "Shared project quota exhausted for today.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [{"reason": "PROJECT_QUOTA_EXHAUSTED"}]
        }
    })
    res = classify_gemini_error(429, payload, "gemini-3.5-flash-lite")
    assert res["category"] == "RATE_LIMIT"
    assert res["can_failover"] is False


def test_classify_model_specific_429():
    """HTTP 429 for model-specific rate limit is eligible for failover if deadline allows."""
    payload = json.dumps({
        "error": {
            "code": 429,
            "message": "Rate limit exceeded for model gemini-3.5-flash-lite.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    res = classify_gemini_error(429, payload, "gemini-3.5-flash-lite")
    assert res["category"] == "RATE_LIMIT"
    assert res["can_failover"] is True


def test_classify_404_model_not_found_vs_endpoint():
    """HTTP 404 with model in message rotates, whereas generic endpoint 404 does not."""
    model_404 = json.dumps({"error": {"code": 404, "message": "models/gemini-old is not found for API version v1beta"}})
    res1 = classify_gemini_error(404, model_404, "gemini-old")
    assert res1["category"] == "MODEL_NOT_FOUND"
    assert res1["can_failover"] is True

    generic_404 = json.dumps({"error": {"code": 404, "message": "Not Found"}})
    res2 = classify_gemini_error(404, generic_404, "gemini-3.5-flash-lite")
    assert res2["category"] == "ENDPOINT_NOT_FOUND"
    assert res2["can_failover"] is False


# =========================================================================
# 3. SAFETY REFUSAL: NEVER ROTATE TO ALTERNATE MODEL
# =========================================================================

@pytest.mark.asyncio
async def test_safety_refusal_stops_rotation(reasoning_tool):
    """When Gemini returns 200 with SAFETY finishReason, do NOT rotate to alternate model."""
    mock_post_calls = []

    async def mock_post(url, json=None, headers=None):
        mock_post_calls.append(url)
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = {
            "candidates": [
                {
                    "finishReason": "SAFETY",
                    "content": {"parts": []}
                }
            ]
        }
        return mock_r

    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="dummy_key"):

        result = await reasoning_tool.execute({"context": {"query": "how to travel to central safely"}})

        # Must attempt ONLY 1 candidate, never rotate after safety block!
        assert len(mock_post_calls) == 1
        assert result["response_source"] == "fallback"
        assert result["decision_source"] == "safety_rules"
        assert result["model_identifier"] is None  # Truthful provenance!
        assert result["safety_blocked_candidate"] is not None


# =========================================================================
# 4. TRUTHFUL PROVENANCE & ATTRIBUTION
# =========================================================================

@pytest.mark.asyncio
async def test_fallback_provenance_truthful(reasoning_tool):
    """Fallback response MUST have model_identifier=None and proper decision_source."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Network unreachable")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="dummy_key"):

        result = await reasoning_tool.execute({"context": {"query": "Hello, how are you?"}})

        assert result["response_source"] == "fallback"
        assert result["model_identifier"] is None
        assert result["decision_source"] in ["small_talk_fallback", "contextual_fallback"]
        assert len(result["failed_model_candidates"]) > 0
        assert result["last_failed_model"] is not None


def test_builder_truthful_attribution():
    """ResponseBuilder must not attribute fallback to Gemini and must remove hardcoded Journey Engine State."""
    builder = ResponseBuilder()
    final_context = {
        "LLM": {
            "summary": "Local fallback guidance for travel.",
            "response_source": "fallback",
            "decision_source": "contextual_fallback",
            "model_identifier": None,
            "last_failed_model": "gemini-3.5-flash-lite",
            "failed_model_candidates": ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
        }
    }
    resp = builder.build_assistant_chat(final_context, user_id="u1", query="help me travel")

    assert resp.response_source == "fallback"
    assert resp.reasoning.response_source == "fallback"
    assert resp.reasoning.decision_source == "contextual_fallback"
    assert resp.reasoning.model_identifier is None
    assert resp.reasoning.last_failed_model == "gemini-3.5-flash-lite"
    assert len(resp.reasoning.failed_model_candidates) == 2


# =========================================================================
# 5. CONVERSATIONAL BEHAVIOR & INTENT MAPPINGS
# =========================================================================

def test_intent_site_explanation():
    """Queries asking about site or app functionality produce NavSakhi support explanation."""
    r1 = global_intent_classifier.classify("Tell me about this site")
    assert r1.intent == AssistantIntent.NAVSAKHI_SUPPORT
    assert r1.direct_response is not None
    assert "NavSakhi" in r1.direct_response

    r2 = global_intent_classifier.classify("What does this app do?")
    assert r2.intent == AssistantIntent.NAVSAKHI_SUPPORT
    assert r2.direct_response is not None
    assert "NavSakhi" in r2.direct_response


def test_intent_casual_companion_phrasing():
    """Casual companion phrasing 'Will you with me in journey' is recognized as companion empathy."""
    res = global_intent_classifier.classify("Will you with me in journey")
    assert res.intent == AssistantIntent.COMPANION_EMPATHY


def test_intent_prior_companion_continuity():
    """Follow-up turns retain companion context when prior turn was companion empathy."""
    history = [
        {"role": "user", "content": "Can you be my companion?"},
        {"role": "assistant", "content": "Of course, I will be your digital travel partner."}
    ]
    res = global_intent_classifier.classify("Are you still there?", history=history)
    assert res.intent == AssistantIntent.COMPANION_EMPATHY


def test_intent_acute_medical_fast_path():
    """Acute medical distress (chest pain, breathing trouble) triggers deterministic fast guidance."""
    res = global_intent_classifier.classify("I am having severe chest pain and cannot breathe")
    assert res.intent == AssistantIntent.SAFETY
    assert res.requires_external_llm is False
    assert "112" in res.direct_response
    assert "108" in res.direct_response


# =========================================================================
# 6. CANCELLATION PROPAGATION
# =========================================================================

@pytest.mark.asyncio
async def test_cancellation_propagates(reasoning_tool):
    """asyncio.CancelledError must propagate cleanly without being swallowed by fallback generation."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = asyncio.CancelledError()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value="dummy_key"):

        with pytest.raises(asyncio.CancelledError):
            await reasoning_tool.execute({"context": {"query": "Hello"}})
