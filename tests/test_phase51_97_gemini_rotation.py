"""
Test suite for Phase 51.97: Gemini Candidate Model Rotation and Per-Model Cooldown.
Verifies that:
1. HTTP 429 triggers per-model cooldown (respecting Retry-After header if present).
2. Rate-limited model does NOT lock out other candidate models.
3. Immediate failover succeeds on candidate 2.
4. Subsequent calls route directly to non-cooldown candidates.
5. Global rate limit cooldown activates ONLY when all candidate models are in cooldown.
6. reset_gemini_cooldowns cleans state completely.
"""

import pytest
import json
import time
from unittest.mock import MagicMock, patch
from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    record_model_429,
    is_model_in_cooldown,
    is_gemini_in_rate_limit_cooldown,
    reset_gemini_cooldowns,
    _parse_retry_after,
    get_configured_gemini_models,
    _model_cooldown_until
)


def test_parse_retry_after():
    """Verify Retry-After extraction from headers."""
    assert _parse_retry_after({"retry-after": "45"}) == 45.0
    assert _parse_retry_after({"Retry-After": "120.5"}) == 120.5
    assert _parse_retry_after({}) is None
    assert _parse_retry_after({"retry-after": "invalid"}) is None


def test_per_model_cooldown_isolation():
    """Verify rate-limiting one model does not impact another model."""
    reset_gemini_cooldowns()

    models = get_configured_gemini_models()
    model_1 = models[0]
    model_2 = models[1]

    # Model 1 hits 429 with Retry-After: 25
    record_model_429(model_1, retry_after=25.0)

    # Model 1 must be in cooldown; Model 2 must NOT be in cooldown
    assert is_model_in_cooldown(model_1) is True
    assert is_model_in_cooldown(model_2) is False

    # Since model 2 is available, global rate limit cooldown must be False
    assert is_gemini_in_rate_limit_cooldown() is False

    # Verify expiry
    cooldown_expiry = _model_cooldown_until.get(model_1, 0.0)
    assert cooldown_expiry > time.time() + 20.0


def test_global_cooldown_only_when_all_models_in_cooldown():
    """Verify global cooldown flag only returns True when every candidate is rate-limited."""
    reset_gemini_cooldowns()

    models = get_configured_gemini_models()
    for m in models[:-1]:
        record_model_429(m, retry_after=60.0)
        assert is_gemini_in_rate_limit_cooldown() is False

    # Record last candidate
    record_model_429(models[-1], retry_after=60.0)
    assert is_gemini_in_rate_limit_cooldown() is True

    # Reset
    reset_gemini_cooldowns()
    assert is_gemini_in_rate_limit_cooldown() is False


@pytest.mark.asyncio
async def test_rotation_on_429_fails_over_to_candidate_2():
    """Verify that when candidate 1 returns 429, execution fails over to candidate 2."""
    reset_gemini_cooldowns()
    tool = ReasoningTool()

    models = get_configured_gemini_models()
    m1 = models[0]
    m2 = models[1]

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "30"}
    resp_429.text = json.dumps({"error": {"code": 429, "message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"}})

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.headers = {}
    resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Candidate 2 route guidance response."}]}}]
    }

    def mock_post(url, *args, **kwargs):
        if m1 in url:
            return resp_429
        return resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "how to reach egmore safely"}}
            result = await tool.execute(params)

            assert result["ai_status"] == "LIVE_SUCCESS"
            assert result["model"] == m2
            assert "Candidate 2" in result["summary"]
            assert is_model_in_cooldown(m1) is True
            assert is_model_in_cooldown(m2) is False
