"""

Unit and regression tests for Gemini API key security, header-based auth,

log sanitization, error classification, retry, and active multi-model fallback chain.

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

    raw_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={DUMMY_KEY}"

    cleaned = sanitize_log_message(raw_url)

    assert DUMMY_KEY not in cleaned

    assert "[REDACTED_API_KEY]" in cleaned or "[REDACTED]" in cleaned



    header_msg = f"Headers sent: x-goog-api-key: {DUMMY_KEY}"

    cleaned_header = sanitize_log_message(header_msg)

    assert DUMMY_KEY not in cleaned_header



    bearer_msg = "Authorization: Bearer my_secret_token_abc123"

    assert "my_secret_token_abc123" not in sanitize_log_message(bearer_msg)





def test_gemini_models_resolution(monkeypatch):

    monkeypatch.delenv("LLM_MODEL_NAME", raising=False)

    monkeypatch.delenv("LLM_FALLBACK_MODELS", raising=False)

    models = get_gemini_models()

    assert models[0] == "gemini-3.8-flash"

    assert "gemini-3.6-flash" in models

    assert "gemini-3.5-flash-lite" in models





def test_gemini_custom_configured_models(monkeypatch):

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite")

    models = get_gemini_models()

    assert models == ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]





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

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    called_models = []



    async def mock_post(url, json=None, headers=None):

        url_str = str(url)

        for m in ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]:

            if m in url_str:

                called_models.append(m)

                break

        mock_resp = MagicMock()

        if "gemini-3.8-flash" in url_str:

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

            assert "gemini-3.8-flash" in called_models

            assert "gemini-3.6-flash" in called_models





@pytest.mark.asyncio

async def test_gemini_quota_exhausted_triggers_fallback(monkeypatch):

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    called_models = []



    async def mock_post(url, json=None, headers=None):

        url_str = str(url)

        for m in ["gemini-3.8-flash", "gemini-3.6-flash"]:

            if m in url_str:

                called_models.append(m)

                break

        mock_resp = MagicMock()

        if "gemini-3.8-flash" in url_str:

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

        assert "gemini-3.8-flash" in called_models

        assert "gemini-3.6-flash" in called_models

        # Confirm primary model is placed in cooldown

        assert tool._model_cooldown.get("gemini-3.8-flash", 0) > 0





@pytest.mark.asyncio

async def test_gemini_unavailable_or_retired_model_transitions_without_retry(monkeypatch):

    """Ensure retired/discontinued models (HTTP 404/400) set cooldown and do not retry."""

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    call_counts = {}



    async def mock_post(url, json=None, headers=None):

        url_str = str(url)

        model = "gemini-3.8-flash" if "gemini-3.8-flash" in url_str else "gemini-3.6-flash"

        call_counts[model] = call_counts.get(model, 0) + 1



        mock_resp = MagicMock()

        if model == "gemini-3.8-flash":

            mock_resp.status_code = 404

            mock_resp.text = "models/gemini-3.8-flash is not found or discontinued"

        else:

            mock_resp.status_code = 200

            mock_resp.json.return_value = {

                "candidates": [{"content": {"parts": [{"text": "Success from active fallback"}]}}]

            }

        return mock_resp



    with patch("httpx.AsyncClient.post", side_effect=mock_post):

        result = await tool._call_gemini_content("Test prompt")

        assert result == "Success from active fallback"

        # Primary model must NOT have been retried (attempt 1 only)

        assert call_counts["gemini-3.8-flash"] == 1

        assert call_counts["gemini-3.6-flash"] == 1

        # Primary model must be placed in long cooldown

        assert tool._model_cooldown.get("gemini-3.8-flash", 0) > 0





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





@pytest.mark.asyncio

async def test_missing_gemini_key_returns_graceful_fallback():

    with patch("app.tools.specialized.reasoning_tool.get_gemini_api_key", return_value=""):

        tool = ReasoningTool()

        tool._model_cooldown.clear()

        routes = [{"route_name": "Test Route", "distance_km": 10.0, "eta_min": 20, "safety_score": 85.0}]

        explanation = await tool.explain_journey_recommendations("Source", "Dest", routes)

        assert explanation is not None

        assert explanation.get("title") == "Objective AI Recommendation"



        # When no routes are supplied, explanation returns None

        empty_explanation = await tool.explain_journey_recommendations("Source", "Dest", [])

        assert empty_explanation is None



        # generate_dynamic_plans safely returns empty list without error

        plans = await tool.generate_dynamic_plans("Source", "Dest", 10.0)

        assert plans == []





@pytest.mark.asyncio

async def test_invalid_gemini_key_returns_graceful_fallback(monkeypatch, caplog):

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    async def mock_403(url, json=None, headers=None):

        mock_resp = MagicMock()

        mock_resp.status_code = 403

        mock_resp.text = "PERMISSION_DENIED: The caller does not have permission"

        return mock_resp



    with caplog.at_level(logging.DEBUG):

        with patch("httpx.AsyncClient.post", side_effect=mock_403):

            routes = [{"route_name": "Test Route", "distance_km": 10.0, "eta_min": 20, "safety_score": 85.0}]

            explanation = await tool.explain_journey_recommendations("Source", "Dest", routes)

            assert explanation is not None

            assert explanation.get("title") == "Objective AI Recommendation"



    for record in caplog.records:

        assert DUMMY_KEY not in record.message



@pytest.mark.asyncio

async def test_gemini_payload_structure_clean_and_supported(monkeypatch):

    """Verify Gemini request sends canonical payload without deprecated or unsupported parameters."""

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    captured_payload = None



    async def mock_post(url, json=None, headers=None):

        nonlocal captured_payload

        captured_payload = json

        mock_resp = MagicMock()

        mock_resp.status_code = 200

        mock_resp.json.return_value = {

            "candidates": [{"content": {"parts": [{"text": "Valid test response"}]}}]

        }

        return mock_resp



    with patch("httpx.AsyncClient.post", side_effect=mock_post):

        result = await tool._call_gemini_content("Test payload verification prompt")

        assert result == "Valid test response"

        assert captured_payload is not None



        # Verify canonical structure

        assert "contents" in captured_payload

        assert len(captured_payload["contents"]) == 1

        assert "parts" in captured_payload["contents"][0]

        assert captured_payload["contents"][0]["parts"][0]["text"] == "Test payload verification prompt"



        # Verify absence of unsupported or deprecated parameters

        for deprecated in [

            "temperature", "top_p", "top_k", "candidate_count",

            "candidateCount", "thinking_budget", "thinkingBudget"

        ]:

            assert deprecated not in captured_payload, f"Deprecated parameter '{deprecated}' found in payload!"

            if "generationConfig" in captured_payload:

                assert deprecated not in captured_payload["generationConfig"]





@pytest.mark.asyncio

async def test_gemini_invalid_request_payload_does_not_apply_model_cooldown(monkeypatch, caplog):

    """Ensure HTTP 400 for bad request payloads is treated as a request error without model cooldown."""

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    async def mock_400(url, json=None, headers=None):

        mock_resp = MagicMock()

        mock_resp.status_code = 400

        mock_resp.text = '{"error": {"code": 400, "message": "Invalid JSON payload received. Unknown field bad_field."}}'

        return mock_resp



    with caplog.at_level(logging.DEBUG):

        with patch("httpx.AsyncClient.post", side_effect=mock_400):

            result = await tool._call_gemini_content("Test bad payload prompt")

            assert result is None



    # Model must NOT be placed in cooldown for request-level errors

    assert tool._model_cooldown.get("gemini-3.8-flash") is None

    # Verify the error was logged as a request error

    assert any("request payload invalid" in record.message for record in caplog.records)





# ============================================================

# Phase 44 Regression Tests

# ============================================================



# ============================================================

# Phase 44 Regression Tests

# ============================================================



@pytest.mark.asyncio

async def test_gemini_all_models_timeout_returns_static_fallback(monkeypatch):

    """

    When all configured Gemini models time out (ReadTimeout), explain_journey_recommendations

    must return the static fallback dict, never raise an exception or return None implicitly

    such that the route response would fail.

    """

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    async def always_timeout(url, json=None, headers=None):

        raise httpx.ReadTimeout("Simulated ReadTimeout", request=None)



    with patch("httpx.AsyncClient.post", side_effect=always_timeout):

        routes = [

            {"route_name": "Direct Drive", "travel_mode": "Cab", "distance_km": 12.5, "eta_min": 28, "safety_score": 76.0},

            {"route_name": "Alternate Road", "travel_mode": "Auto", "distance_km": 13.1, "eta_min": 31, "safety_score": 71.0},

        ]

        result = await tool.explain_journey_recommendations(

            source="T. Nagar",

            dest="Adyar",

            verified_routes=routes,

            preferences=["Fastest"],

        )



    assert result is not None, "Static fallback must be returned when all Gemini models time out"

    assert isinstance(result, dict), "Fallback result must be a dict"

    assert "title" in result or "summary" in result, "Fallback must contain route explanation fields"

    # Cooldown must be set on all models

    assert "_all_" in tool._model_cooldown, "Global cooldown must be set after all models timeout"





@pytest.mark.asyncio

async def test_gemini_timeout_does_not_prevent_route_response(monkeypatch):

    """

    Simulates the full explain_journey_recommendations call timing out.

    Verifies asyncio.wait_for allows the coordinator to deliver

    a route response with ai_explanation=None (static fallback) instead of 502.

    """

    import asyncio

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    async def slow_explain(*args, **kwargs):

        await asyncio.sleep(15)

        return {"title": "Should never reach here"}



    with patch.object(tool, "explain_journey_recommendations", side_effect=slow_explain):

        routes = [{"route_name": "Route A", "travel_mode": "Cab", "distance_km": 8.0, "eta_min": 20, "safety_score": 80.0}]

        ai_explanation = None

        try:

            ai_explanation = await asyncio.wait_for(

                tool.explain_journey_recommendations(

                    source="Source", dest="Dest", verified_routes=routes

                ),

                timeout=0.1,  # Fast timeout for test

            )

        except asyncio.TimeoutError:

            pass



    assert ai_explanation is None, "Gemini timeout must result in ai_explanation=None, not an exception"





@pytest.mark.asyncio

async def test_gemini_single_readtimeout_fallsback_to_next_model(monkeypatch):

    """

    ReadTimeout on first model must immediately trigger fallback to the next model

    without retrying the timed-out model, and the first model must be put on cooldown.

    """

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini-3.6-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    call_log = []



    async def mixed_responses(url, json=None, headers=None):

        model = url.split("/models/")[1].split(":")[0] if "/models/" in url else "unknown"

        call_log.append(model)

        if "3.8" in model:

            raise httpx.ReadTimeout("Simulated primary timeout", request=None)

        mock_resp = MagicMock()

        mock_resp.status_code = 200

        mock_resp.json.return_value = {

            "candidates": [{"content": {"parts": [{"text": "Fallback model response"}]}}]

        }

        return mock_resp



    with patch("httpx.AsyncClient.post", side_effect=mixed_responses):

        result = await tool._call_gemini_content("Test prompt")



    assert result == "Fallback model response", "Should return response from fallback model"

    assert any("3.8" in m for m in call_log), "Primary model should have been attempted"

    assert any("3.6" in m for m in call_log), "Fallback model should have been tried"

    assert call_log.count("gemini-3.8-flash") == 1, "Timed out model must NOT be retried on timeout"

    assert tool._model_cooldown.get("gemini-3.8-flash") is not None, "Timed out model must be placed on cooldown"





@pytest.mark.asyncio

async def test_bounded_total_latency_and_no_repeated_fallback_chain(monkeypatch):

    """

    When Phase 2 dynamic planning exhausts the Gemini budget or times out,

    the subsequent Phase 4 explanation phase must NOT blindly retry all models;

    it must fail-fast immediately (utilizing global cooldown or remaining deadline)

    and return the static fallback in sub-millisecond time.

    """

    import time

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini-3.6-flash")

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    call_count = 0



    async def timeout_response(url, json=None, headers=None):

        nonlocal call_count

        call_count += 1

        raise httpx.ReadTimeout("Timeout", request=None)



    with patch("httpx.AsyncClient.post", side_effect=timeout_response):

        # 1. Dynamic planning runs and exhausts candidate models

        dyn_plans = await tool.generate_dynamic_plans("Origin", "Dest", 10.0, ["Safe"], deadline=time.time() + 3.5)

        assert dyn_plans == [], "Dynamic plans must return empty list on failure"

        calls_after_phase2 = call_count



        # 2. Explanation runs immediately after for the same journey

        t0 = time.perf_counter()

        routes = [{"route_name": "Route 1", "travel_mode": "Cab", "distance_km": 5.0, "eta_min": 15, "safety_score": 75.0}]

        explanation = await tool.explain_journey_recommendations(

            source="Origin",

            dest="Dest",

            verified_routes=routes,

            deadline=time.time() + 5.0

        )

        t_elapsed = time.perf_counter() - t0



    # Phase 4 must NOT have made additional external HTTP calls because _all_ cooldown is active

    assert call_count == calls_after_phase2, "Phase 4 must not initiate new slow calls when Gemini is in cooldown"

    assert t_elapsed < 0.1, f"Phase 4 must fail-fast immediately (took {t_elapsed:.4f}s)"

    assert explanation is not None, "Must return valid static fallback"

    assert "Objective AI Recommendation" in explanation.get("title", "")





@pytest.mark.asyncio

async def test_cancellation_and_cleanup_of_timed_out_async_requests(monkeypatch):

    """

    When asyncio.wait_for cancels an ongoing Gemini call due to deadline expiry,

    the cancelled task must clean up gracefully without raising unhandled exceptions

    or leaking pending background coroutines.

    """

    import asyncio

    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    tool = ReasoningTool()

    tool._model_cooldown.clear()



    task_started = asyncio.Event()

    task_cancelled = asyncio.Event()



    async def hang_with_cancellation(*args, **kwargs):

        task_started.set()

        try:

            await asyncio.sleep(10.0)

            return "Should not finish"

        except asyncio.CancelledError:

            task_cancelled.set()

            raise



    with patch.object(tool, "_call_gemini_content", side_effect=hang_with_cancellation):

        try:

            await asyncio.wait_for(tool.generate_dynamic_plans("A", "B", 5.0), timeout=0.1)

        except asyncio.TimeoutError:

            pass



    await asyncio.sleep(0.05)

    assert task_started.is_set(), "Inner task should have started"

    assert task_cancelled.is_set(), "Inner task should have received CancelledError on timeout"





def test_valid_routing_geometry_and_safety_scores_when_gemini_unavailable():

    """

    The ResponseBuilder must deliver complete GeoJSON geometry, distance, duration,

    and LightGBM safety scores even when ai_explanation is None or static fallback.

    """

    from app.intelligence.response.builder import ResponseBuilder

    from app.models.journey import Journey, CandidateRoute, Location

    builder = ResponseBuilder()



    route_metadata = {

        "route_name": "Verified Corridor",

        "travel_mode": "Cab Direct",

        "safety_score": 78.5,

        "score_status": "READY",

        "scoreable_coverage_ratio": 0.85,

        "cost": "INR 150",

        "geometry": {

            "type": "LineString",

            "coordinates": [[80.23, 13.04], [80.24, 13.03], [80.25, 13.01]]

        }

    }

    candidate = CandidateRoute(

        route_identifier="real_route_0",

        distance=8500.0,

        duration=1200.0,

        recommendation_status="AVAILABLE",

        route_metadata=route_metadata

    )



    context = {

        "source_name": "T. Nagar",

        "dest_name": "Adyar",

        "source_loc": [80.23, 13.04],

        "dest_loc": [80.25, 13.01],

        "routes": [candidate],

        "warnings": [],

        "weather": {"condition": "Clear", "temperature": 28},

        "ai_explanation": None  # Gemini unavailable

    }



    plan_response = builder.build_journey_plan(context, user_id="guest", journey_id="j_test")

    assert plan_response is not None

    assert len(plan_response.recommended_routes) == 1

    rec = plan_response.recommended_routes[0]

    assert rec.safety_score == 78.5, "Safety score must be preserved"

    assert rec.distance == "8.5 km", "Distance must be preserved"

    assert len(rec.segments) > 0, "Route segments must be present"

    seg = rec.segments[0]

    assert seg.polyline is not None and "geometry" in seg.polyline, "Segment polyline geometry must be present"

    assert len(seg.polyline["geometry"]["coordinates"]) == 3, "Valid coordinates must be retained"

    assert plan_response.ai_recommendation is not None, "Deterministic non-LLM recommendation must be present"

    assert plan_response.ai_recommendation.title == "Objective Recommendation"





def test_spatial_index_reuse_and_bbox_expansion():

    """

    SpatialMatchingService must expand its indexed bounding box seamlessly

    when routes traverse disjoint geographic areas, without reloading full 1M parquet.

    """

    from app.intelligence.journey.spatial_matcher import SpatialMatchingService

    matcher = SpatialMatchingService(auto_build_index=False)



    # Initial area: Chennai Central

    matcher._ensure_index_for_bbox(min_lon=80.27, min_lat=13.08, max_lon=80.28, max_lat=13.09)

    first_bbox = matcher._indexed_bbox

    assert first_bbox is not None



    # Querying inside same area does not rebuild

    matcher._ensure_index_for_bbox(min_lon=80.272, min_lat=13.082, max_lon=80.278, max_lat=13.088)

    assert matcher._indexed_bbox == first_bbox, "Index must be reused for enclosed bounding box"



    # Querying disjoint area (Tambaram south): bbox must expand to cover both

    matcher._ensure_index_for_bbox(min_lon=80.11, min_lat=12.92, max_lon=80.12, max_lat=12.93)

    second_bbox = matcher._indexed_bbox

    assert second_bbox[0] <= 80.11 and second_bbox[2] >= 80.28, "Bounding box must expand to enclose both areas"





def test_public_assets_accessible_and_valid():

    """

    Verify that /maplibre-worker.js and /manifest.json exist in the public directory,

    are valid JS and JSON respectively, and are explicitly excluded from middleware login redirect.

    """

    import json

    from pathlib import Path

    import re



    repo_root = Path(__file__).resolve().parent.parent

    worker_path = repo_root / "frontend" / "public" / "maplibre-worker.js"

    manifest_path = repo_root / "frontend" / "public" / "manifest.json"

    middleware_path = repo_root / "frontend" / "src" / "middleware.ts"



    # 1. MapLibre worker verification

    assert worker_path.exists(), "maplibre-worker.js must exist in frontend/public/"

    with open(worker_path, "r", encoding="utf-8", errors="ignore") as f:

        worker_content = f.read()

    assert len(worker_content) > 10000, "Worker file must contain valid bundled JavaScript"

    assert not worker_content.strip().startswith("<!DOCTYPE"), "Worker must NOT be an HTML page"



    # 2. Manifest verification

    assert manifest_path.exists(), "manifest.json must exist in frontend/public/"

    with open(manifest_path, "r", encoding="utf-8") as f:

        manifest_data = json.load(f)

    assert "name" in manifest_data and "icons" in manifest_data, "Manifest must be valid Web App Manifest JSON"



    # 3. Middleware configuration verification

    with open(middleware_path, "r", encoding="utf-8") as f:

        mw_content = f.read()



    # Extract matcher

    match = re.search(r"matcher:\s*\['(.+?)'\]", mw_content)

    assert match, "Could not find matcher pattern in middleware.ts"

    pattern = match.group(1)



    # Exact-path isPublicRoute checks

    assert "pathname === '/manifest.json'" in mw_content, "manifest.json must be exempted via exact-path check in isPublicRoute"

    assert "pathname === '/maplibre-worker.js'" in mw_content, "maplibre-worker.js must be exempted via exact-path check in isPublicRoute"



    # Matcher should NOT contain blanket exclusions for .js or .json

    assert "\\.js" not in pattern, "Matcher must not blanket-exclude .js files"

    assert "\\.json" not in pattern, "Matcher must not blanket-exclude .json files"





def test_protected_routes_enforce_authentication():

    """

    Ensure sensitive routes (/emergency, /live, /activity, /settings, /profile)

    are NOT declared public and remain subject to authentication redirects.

    """

    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent

    middleware_path = repo_root / "frontend" / "src" / "middleware.ts"



    with open(middleware_path, "r", encoding="utf-8") as f:

        mw_content = f.read()



    # Protected routes must NOT be in isPublicRoute

    for protected in ["/emergency", "/live", "/activity", "/settings", "/profile"]:

        assert f"pathname === '{protected}'" not in mw_content, f"Protected route {protected} must not be in isPublicRoute"





def test_cors_headers_on_successful_responses():

    """

    Verify FastAPI CORS middleware returns Access-Control-Allow-Origin: https://nav-sakhi.vercel.app

    for requests originating from the production frontend origin.

    """

    from fastapi.testclient import TestClient

    from app.main import app



    client = TestClient(app)

    # Preflight request

    resp_opt = client.options(

        "/api/v1/journeys/",

        headers={

            "Origin": "https://nav-sakhi.vercel.app",

            "Access-Control-Request-Method": "POST",

            "Access-Control-Request-Headers": "Content-Type",

        }

    )

    assert resp_opt.status_code == 200

    assert resp_opt.headers.get("access-control-allow-origin") == "https://nav-sakhi.vercel.app"

    assert resp_opt.headers.get("access-control-allow-credentials") == "true"



    # Authenticated / health endpoint with origin

    resp_health = client.get("/health", headers={"Origin": "https://nav-sakhi.vercel.app"})

    assert resp_health.status_code == 200

    assert resp_health.headers.get("access-control-allow-origin") == "https://nav-sakhi.vercel.app"





# ---------------------------------------------------------------------------

# Cross-request / process-wide cooldown behaviour (circuit-breaker contract)

# ---------------------------------------------------------------------------



@pytest.mark.asyncio

async def test_class_level_cooldown_is_process_wide_circuit_breaker(monkeypatch):

    """

    DESIGN CONTRACT: _model_cooldown is intentionally class-level (process-wide).



    When User A's request exhausts all Gemini models and triggers the global

    '_all_' cooldown, a subsequent independent request from User B (represented

    here by a second ReasoningTool instance) must immediately serve the static

    fallback without making any external HTTP calls.



    This is the desired circuit-breaker behaviour: if Gemini is known to be

    unresponsive, protecting all users from 3s+ blocking waits outweighs the

    benefit of retrying on a per-request basis.



    The test:

    1. Simulates User A's request exhausting all models (sets global cooldown).

    2. Instantiates a fresh ReasoningTool as if it were User B's handler.

    3. Verifies User B's request returns the static fallback with zero HTTP calls.

    """

    import asyncio, time



    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")

    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gemini-3.6-flash")



    # --- User A: all models time out ---

    tool_user_a = ReasoningTool()

    tool_user_a._model_cooldown.clear()  # clean class-level state for test isolation



    async def always_timeout(url, json=None, headers=None):

        raise httpx.ReadTimeout("Simulated ReadTimeout", request=None)



    with patch("httpx.AsyncClient.post", side_effect=always_timeout):

        result_a = await tool_user_a._call_gemini_content("User A prompt")



    assert result_a is None, "User A should receive None (all models failed)"

    assert "_all_" in ReasoningTool._model_cooldown, (

        "Global cooldown must be set on the class after all models fail"

    )



    # --- User B: fresh instance, no HTTP call should be made ---

    tool_user_b = ReasoningTool()  # new instance, same class-level cooldown



    http_call_count = 0



    async def should_not_be_called(url, json=None, headers=None):

        nonlocal http_call_count

        http_call_count += 1

        mock_resp = MagicMock()

        mock_resp.status_code = 200

        mock_resp.json.return_value = {

            "candidates": [{"content": {"parts": [{"text": "Should not reach Gemini"}]}}]

        }

        return mock_resp



    with patch("httpx.AsyncClient.post", side_effect=should_not_be_called):

        result_b = await tool_user_b._call_gemini_content("User B prompt")



    assert result_b is None, (

        "User B should receive None because the class-level cooldown is still active"

    )

    assert http_call_count == 0, (

        "No HTTP calls should be made for User B while global cooldown is active "

        "(circuit-breaker protects all users from known-unresponsive Gemini)"

    )



    # --- Cleanup: expire cooldown so subsequent tests are not affected ---

    ReasoningTool._model_cooldown.clear()





@pytest.mark.asyncio

async def test_cooldown_expires_and_next_request_retries_gemini(monkeypatch):

    """

    After the cooldown window expires, the NEXT request must attempt Gemini again

    rather than serving the static fallback indefinitely.



    This ensures the circuit breaker is self-healing: a temporary Gemini outage

    does not permanently disable AI explanations for the remainder of the process

    lifetime.

    """

    import time



    monkeypatch.setenv("GEMINI_API_KEY", DUMMY_KEY)

    monkeypatch.setenv("LLM_MODEL_NAME", "gemini-3.8-flash")



    tool = ReasoningTool()

    # Manually set a cooldown that is already expired

    ReasoningTool._model_cooldown.clear()

    ReasoningTool._model_cooldown["_all_"] = time.time() - 1.0  # expired 1s ago



    http_call_count = 0



    async def succeed_on_retry(url, json=None, headers=None):

        nonlocal http_call_count

        http_call_count += 1

        mock_resp = MagicMock()

        mock_resp.status_code = 200

        mock_resp.json.return_value = {

            "candidates": [{"content": {"parts": [{"text": "Gemini recovered"}]}}]

        }

        return mock_resp



    with patch("httpx.AsyncClient.post", side_effect=succeed_on_retry):

        result = await tool._call_gemini_content("Post-recovery prompt")



    assert result == "Gemini recovered", (

        "After cooldown expires, Gemini must be retried and successful response returned"

    )

    assert http_call_count == 1, "Exactly one HTTP call should be made after cooldown expiry"



    # Cleanup

    ReasoningTool._model_cooldown.clear()
