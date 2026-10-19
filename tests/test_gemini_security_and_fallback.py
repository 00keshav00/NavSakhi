"""
Unit and regression tests for Gemini API key security, header-based auth,
log sanitization, error classification, retry, and multi-model fallback.
"""

import os
import json
import logging
import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.tools.specialized.reasoning_tool import (
    ReasoningTool,
    get_gemini_api_key,
    get_gemini_model,
    get_gemini_models,
    sanitize_log_message,
)

DUMMY_KEY = "AIzaSyTEST_KEY_NOT_REAL_FOR_TESTING_123"


def test_sanitize_log_message_redacts_credentials():
    raw_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={DUMMY_KEY}"
    cleaned = sanitize_log_message(raw_url)
    assert DUMMY_KEY not in cleaned
    assert "[REDACTED_API_KEY]" in cleaned or "[REDACTED]" in cleaned

    header_msg = f"Headers sent: x-goog-api-key: {DUMMY_KEY}"
    cleaned_header = sanitize_log_message(header_msg)
    assert DUMMY_KEY not in cleaned_header

    bearer_msg = "Authorization: Bearer my_secret_token_abc123"
    assert "my_secret_token_abc123" not in sanitize_log_message(bearer_msg)


def test_gemini_models_resolution(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    monkeypatch.delenv("LLM_FALLBACK_MODELS", raising=False)
    models = get_gemini_models()
    assert models[0] == "gemini-2.5-flash"
    assert "gemini-2.0-flash" in models
    assert "gemini-1.5-flash" in models


@pytest.mark.asyncio
async def test_gemini_request_uses_header_not_query_param(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)
    tool = ReasoningTool()
    tool._model_cooldown.clear()

    captured_url = None
    captured_headers = None

    async def mock_post(url, json=None, headers=None):
        nonlocal captured_url, captured_headers
        captured_url = str(url)
        captured_headers = headers
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Objective AI reasoning test response"}]}}]
        }
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await tool._call_gemini_content("Test prompt")
        assert result == "Objective AI reasoning test response"
        assert captured_url is not None
        assert "?key=" not in captured_url
        assert DUMMY_KEY not in captured_url
        assert captured_headers.get("x-goog-api-key") == DUMMY_KEY


@pytest.mark.asyncio
async def test_gemini_dummy_key_never_logged_on_errors(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)
    tool = ReasoningTool()
    tool._model_cooldown.clear()

    async def mock_503(url, json=None, headers=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.headers = {"Retry-After": "0"}
        mock_resp.text = "Service Unavailable"
        return mock_resp

    with caplog.at_level(logging.DEBUG):
        with patch("httpx.AsyncClient.post", side_effect=mock_503):
            with patch("asyncio.sleep", return_value=None):
                result = await tool._call_gemini_content("Test prompt")
                assert result is None

    # Verify dummy key never leaked into any captured log entry
    for record in caplog.records:
        assert DUMMY_KEY not in record.message
        assert DUMMY_KEY not in str(record)
    assert any("transient HTTP 503" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_gemini_model_fallback_on_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)
    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    tool = ReasoningTool()
    tool._model_cooldown.clear()

    called_models = []

    async def mock_post(url, json=None, headers=None):
        url_str = str(url)
        for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            if m in url_str:
                called_models.append(m)
                break
        mock_resp = MagicMock()
        if "gemini-2.5-flash" in url_str:
            mock_resp.status_code = 503
            mock_resp.headers = {}
            mock_resp.text = "Service Unavailable"
        else:
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": '{"title": "Fallback Success", "summary": "Used fallback model", "reasoning": "Valid", "tradeoffs": []}'}]}}]
            }
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        with patch("asyncio.sleep", return_value=None):
            routes = [{"route_name": "Test Route", "distance_km": 10.0, "eta_min": 20, "safety_score": 85.0}]
            explanation = await tool.explain_journey_recommendations("Source", "Dest", routes)
            assert explanation is not None
            assert explanation.get("summary") == "Used fallback model"
            assert "gemini-2.5-flash" in called_models
            assert "gemini-2.0-flash" in called_models


@pytest.mark.asyncio
async def test_gemini_quota_exhausted_triggers_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)
    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-2.5-flash")
    tool = ReasoningTool()
    tool._model_cooldown.clear()

    called_models = []

    async def mock_post(url, json=None, headers=None):
        url_str = str(url)
        for m in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            if m in url_str:
                called_models.append(m)
                break
        mock_resp = MagicMock()
        if "gemini-2.5-flash" in url_str:
            mock_resp.status_code = 429
            mock_resp.text = "RESOURCE_EXHAUSTED: Daily quota exceeded."
            mock_resp.headers = {}
        else:
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": '[{"strategy_name": "Metro Transit", "strategy_id": "s1", "steps": []}]'}]}}]
            }
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        plans = await tool.generate_dynamic_plans("Source Station", "Dest Station", 15.0)
        assert len(plans) == 1
        assert plans[0]["strategy_name"] == "Metro Transit"
        assert "gemini-2.5-flash" in called_models
        assert "gemini-2.0-flash" in called_models
        # Confirm primary model is placed in cooldown
        assert tool._model_cooldown.get("gemini-2.5-flash", 0) > 0


@pytest.mark.asyncio
async def test_gemini_auth_failure_fails_fast_without_retrying_all_models(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)
    tool = ReasoningTool()
    tool._model_cooldown.clear()

    call_count = 0

    async def mock_401(url, json=None, headers=None):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "API_KEY_INVALID"
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_401):
        result = await tool._call_gemini_content("Test prompt")
        assert result is None
        # Must fail fast (only 1 attempt) and not retry or iterate through all models
        assert call_count == 1
        assert tool._model_cooldown.get("_all_", 0) > 0
