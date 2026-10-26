"""
NavSakhi Phase 51.106 — Assistant Timeout Exception & Runtime Crash Regression Suite

Validates remediation of the P0 defect discovered in Phase 51.105:
  NameError: name 'asyncio' is not defined
  in app/tools/specialized/reasoning_tool.py at line 628

Verifies:
1. Module namespace explicitly includes 'asyncio'.
2. Simulated asyncio.TimeoutError during model call triggers failover without NameError.
3. When all candidate models time out, system returns honest fallback contract:
   - provider="local_fallback"
   - ai_status="UNAVAILABLE_FALLBACK"
   - response_source="fallback" (never "gemini")
   - outcome_category="timeout"
4. Simulated httpx.TimeoutException (ReadTimeout, ConnectTimeout) is cleanly handled as a timeout.
5. Coordinator process_assistant_chat returns structured AssistantResponse during timeout.
6. FastAPI route POST /api/v1/assistant/chat returns HTTP 200 OK with fallback payload instead of crashing with HTTP 500.
7. Telemetry honors strict provider disclosure: response_source="gemini" only on true live provider success.
"""

import asyncio
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

import app.tools.specialized.reasoning_tool as rt
from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    reset_gemini_cooldowns,
    _model_cooldowns,
    _model_ineligible
)
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.main import app


@pytest.fixture(autouse=True)
def clean_cooldowns():
    reset_gemini_cooldowns()
    yield
    reset_gemini_cooldowns()


def test_asyncio_present_in_module_namespace():
    """Confirms asyncio is imported at the module level in reasoning_tool.py."""
    assert "asyncio" in rt.__dict__, "asyncio must be present in reasoning_tool module namespace"
    assert rt.asyncio is asyncio


@pytest.mark.asyncio
async def test_gemini_timeout_failover_without_name_error():
    """
    Simulates asyncio.TimeoutError on the primary candidate model.
    Verifies that the exception handler executes without NameError and cleanly
    fails over to the second candidate model which succeeds.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()
    _model_ineligible.clear()

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "NavSakhi guidance: safe corridor verified."}]}}]
    }

    call_count = 0
    async def mock_post(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First candidate times out via asyncio.TimeoutError
            raise asyncio.TimeoutError("Simulated provider network timeout")
        return mock_resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            params = {"context": {"query": "is the metro running?"}}
            result = await tool.execute(params)

            assert result["ai_status"] == "LIVE_SUCCESS"
            assert result["provider"] == "gemini"
            assert result["model"] == "gemini-3.1-flash-lite"
            assert result["attempt_count"] == 2
            assert "safe corridor verified" in result["summary"]


@pytest.mark.asyncio
async def test_gemini_all_timeouts_returns_honest_fallback():
    """
    Simulates asyncio.TimeoutError across all candidate models.
    Verifies that:
    1. No NameError or unhandled exception is raised.
    2. System returns honest local fallback.
    3. response_source is strictly 'fallback', never 'gemini'.
    4. outcome_category is 'timeout'.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()
    _model_ineligible.clear()

    async def mock_timeout(url, *args, **kwargs):
        raise asyncio.TimeoutError("Connection timed out")

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_timeout):
            params = {"context": {"query": "i need assistance reaching central"}}
            result = await tool.execute(params)

            assert result["provider"] == "local_fallback"
            assert result["response_source"] == "fallback"
            assert result["ai_status"] == "UNAVAILABLE_FALLBACK"
            assert result["outcome_category"] == "timeout"
            assert result["gemini_attempted"] is True
            assert result["attempt_count"] > 0
            assert "112" in result["summary"] or "NavSakhi" in result["summary"] or len(result["summary"]) > 0


@pytest.mark.asyncio
async def test_gemini_httpx_read_timeout_handled_cleanly():
    """
    Simulates httpx.ReadTimeout on all candidate models.
    Verifies that httpx.TimeoutException is caught by the timeout handler and
    transitions gracefully to honest fallback without crashing.
    """
    tool = ReasoningTool()
    _model_cooldowns.clear()
    _model_ineligible.clear()

    async def mock_read_timeout(url, *args, **kwargs):
        raise httpx.ReadTimeout("Read timed out from server", request=MagicMock())

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_read_timeout):
            params = {"context": {"query": "safety advice please"}}
            result = await tool.execute(params)

            assert result["provider"] == "local_fallback"
            assert result["response_source"] == "fallback"
            assert result["outcome_category"] == "timeout"


@pytest.mark.asyncio
async def test_coordinator_process_assistant_chat_timeout_fallback():
    """
    Verifies that JourneyIntelligenceCoordinator.process_assistant_chat survives
    a Gemini timeout and returns a properly structured chat response.
    """
    coordinator = JourneyIntelligenceCoordinator()

    async def mock_timeout(url, *args, **kwargs):
        raise asyncio.TimeoutError("Upstream timeout")

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_timeout):
            chat_resp = await coordinator.process_assistant_chat(
                user_id="guest_test",
                query="Hello, what safety features are available?"
            )

            assert chat_resp is not None
            assert hasattr(chat_resp, "content")
            assert hasattr(chat_resp, "response_source")
            assert chat_resp.response_source == "fallback"
            assert chat_resp.reasoning.response_source == "fallback"
            assert chat_resp.reasoning.outcome_category == "timeout"
            assert len(chat_resp.content) > 0


def test_assistant_chat_http_endpoint_timeout_returns_200_fallback():
    """
    Full HTTP integration test reproducing the exact Phase 51.105 incident:
    POST /api/v1/assistant/chat previously returned HTTP 500 with NameError: name 'asyncio' is not defined.
    Verifies that with the patch, the route returns HTTP 200 OK with honest fallback data.
    """
    client = TestClient(app)

    async def mock_timeout(url, *args, **kwargs):
        raise asyncio.TimeoutError("Gateway timeout to Gemini")

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_timeout):
            response = client.post(
                "/api/v1/assistant/chat",
                json={"query": "Hello, what safety features are available?"}
            )

            # Must NOT return HTTP 500
            assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["success"] is True
            resp_data = data["data"]
            assert resp_data["response_source"] == "fallback"
            assert resp_data["reasoning"]["response_source"] == "fallback"
            assert resp_data["reasoning"]["outcome_category"] == "timeout"
            assert len(resp_data["content"]) > 0


def test_assistant_chat_http_endpoint_live_success_telemetry():
    """
    Full HTTP integration test verifying that when Gemini succeeds,
    the endpoint returns HTTP 200 OK with response_source="gemini".
    """
    client = TestClient(app)

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "NavSakhi live intelligence: all safety features active."}]}}]
    }

    async def mock_success(url, *args, **kwargs):
        return mock_resp_200

    with patch("os.getenv", return_value="AIzaSy_mock_test_key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_success):
            response = client.post(
                "/api/v1/assistant/chat",
                json={"query": "Hello, what safety features are available?"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            resp_data = data["data"]
            assert resp_data["response_source"] == "gemini"
            assert resp_data["reasoning"]["response_source"] == "gemini"
            assert "NavSakhi live intelligence" in resp_data["content"]
