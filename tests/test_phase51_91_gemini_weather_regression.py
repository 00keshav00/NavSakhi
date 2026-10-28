"""
NavSakhi Phase 51.91 — Gemini Verification & Weather Concurrency Regression Suite

Validates:
1. Safety awareness queries ("tell me what to be aware of", "safety tips", "precautions")
   are classified as AssistantIntent.SAFETY with requires_external_llm=True.
2. Concrete fallback guidance is returned when Gemini is unavailable, rather than generic introductory text.
3. Multi-turn conversation history is preserved and forwarded in coordinator execute_pipeline.
4. Weather single-flight coalescing prevents concurrent duplicate outbound HTTP requests to Open-Meteo.
5. Concurrent requests during Open-Meteo HTTP 429 share the single response and activate provider cooldown.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.assistant_intent_service import (
    global_intent_classifier,
    AssistantIntent
)
from app.services.weather_service import WeatherService
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator


# =====================================================================
# 1. ASSISTANT INTENT & SAFETY AWARENESS VERIFICATION
# =====================================================================
def test_safety_awareness_intent_classification():
    """Validates that general safety awareness queries are categorized as SAFETY and require LLM."""
    test_queries = [
        "tell me what to be aware of",
        "what should I be aware of when traveling?",
        "what to look out for",
        "any safety tips for traveling alone in Chennai?",
        "what precautions should I take?",
        "tips for staying safe at night"
    ]
    for q in test_queries:
        res = global_intent_classifier.classify(q)
        assert res.intent == AssistantIntent.SAFETY, f"Query '{q}' should be classified as SAFETY, got {res.intent}"
        assert res.requires_external_llm is True, f"Query '{q}' must require external LLM"
        assert res.direct_response is not None
        assert "112" in res.direct_response
        assert "1091" in res.direct_response
        assert "Corridors" in res.direct_response or "transit" in res.direct_response.lower()


@pytest.mark.asyncio
async def test_assistant_awareness_fallback_when_gemini_offline():
    """Validates that when Gemini is offline, the assistant returns concrete safety guidance, not generic greeting."""
    tool = ReasoningTool()
    # Mock no Gemini API key to trigger fallback
    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value=""):
        res = await tool.execute({
            "context": {
                "query": "tell me what to be aware of"
            }
        })
        summary = res.get("summary", "")
        assert "Hello! I am your NavSakhi Intelligence Coordinator" not in summary
        assert "112" in summary
        assert "1091" in summary
        assert "Corridors" in summary or "Metro" in summary


@pytest.mark.asyncio
async def test_coordinator_preserves_conversation_history():
    """Validates that coordinator execute_pipeline forwards history to ReasoningTool."""
    coordinator = JourneyIntelligenceCoordinator()
    captured_context = {}

    async def mock_execute(params):
        captured_context.update(params.get("context", {}))
        return {"summary": "Verified response", "reasoning": ["Mocked"]}

    with patch.object(coordinator.reasoning_tool, "execute", side_effect=mock_execute):
        history = [
            {"role": "user", "content": "I am taking the Chennai Metro from Guindy."},
            {"role": "assistant", "content": "The Metro Blue Line is well-lit and active."}
        ]
        context = {
            "user_id": "test_user",
            "query": "tell me what to be aware of",
            "history": history,
            "active_journey": None,
            "journey_history": []
        }
        await coordinator.execute_pipeline("assistant", context)
        assert "history" in captured_context
        assert captured_context["history"] == history


# =====================================================================
# 2. WEATHER SINGLE-FLIGHT COALESCING & 429 RATE-LIMIT VERIFICATION
# =====================================================================
@pytest.mark.asyncio
async def test_weather_single_flight_coalescing_concurrent_requests():
    """
    Validates that concurrent callers for identical coordinates share a single
    in-flight outbound HTTP request rather than firing duplicate network calls.
    """
    service = WeatherService()
    call_count = 0

    mock_open_meteo_payload = {
        "current": {
            "temperature_2m": 28.5,
            "apparent_temperature": 31.0,
            "relative_humidity_2m": 70,
            "wind_speed_10m": 12.0,
            "wind_direction_10m": 180,
            "precipitation": 0.0,
            "rain": 0.0,
            "weather_code": 1,
            "cloud_cover": 20,
            "uv_index": 5.0,
            "time": "2026-10-25T12:00:00"
        },
        "daily": {
            "time": ["2026-10-25"],
            "weather_code": [1],
            "temperature_2m_max": [32.0],
            "temperature_2m_min": [26.0],
            "sunrise": ["2026-10-25T06:00"],
            "sunset": ["2026-10-25T18:00"],
            "uv_index_max": [8.0]
        },
        "hourly": {
            "time": ["2026-10-25T12:00"],
            "temperature_2m": [28.5],
            "precipitation_probability": [0],
            "weather_code": [1]
        },
        "timezone": "Asia/Kolkata"
    }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate network latency
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = lambda: mock_open_meteo_payload
            return mock_resp

    with patch("httpx.AsyncClient", MockAsyncClient):
        # Fire 5 concurrent requests for identical coordinates
        lat, lon = 13.0827, 80.2707
        results = await asyncio.gather(
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
        )

        assert call_count == 1, f"Expected exactly 1 outbound call to Open-Meteo, got {call_count}"
        for res in results:
            assert res.available is True
            assert res.status == "AVAILABLE"
            assert res.temperature == 28.5


@pytest.mark.asyncio
async def test_weather_single_flight_coalescing_on_429():
    """
    Validates that when Open-Meteo returns HTTP 429:
    1. Concurrent callers share the single 429 response without redundant outbound calls.
    2. The 30s rate-limit cooldown is activated.
    3. Subsequent requests for different coordinates immediately hit the cooldown without network calls.
    """
    current_time = 1000.0
    service = WeatherService(time_func=lambda: current_time)
    call_count = 0

    class MockAsyncClient429:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.text = "Too Many Requests"
            return mock_resp

    with patch("httpx.AsyncClient", MockAsyncClient429):
        lat, lon = 13.0827, 80.2707
        # Fire 4 concurrent requests for Chennai Central
        results = await asyncio.gather(
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
            service.get_live_weather(lat, lon, "Chennai Central"),
        )

        assert call_count == 1, f"Expected exactly 1 outbound call during 429, got {call_count}"
        for res in results:
            assert res.available is False
            assert res.status == "RATE_LIMITED"
            assert res.cache_expires_in_seconds <= 30

        # Now test a request for completely DIFFERENT coordinates during the active cooldown
        current_time += 5.0  # 5 seconds later
        res_diff = await service.get_live_weather(12.9249, 80.1000, "Tambaram")
        assert call_count == 1, "Provider cooldown should suppress outbound calls for all coordinates"
        assert res_diff.status == "RATE_LIMITED"
        assert res_diff.cached is True
        assert res_diff.cache_expires_in_seconds == 25
