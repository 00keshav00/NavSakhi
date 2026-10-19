import pytest
from unittest.mock import AsyncMock, MagicMock
from app.intelligence.response.builder import ResponseBuilder
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.schemas.assistant_schemas import AssistantResponse


@pytest.fixture
def response_builder():
    return ResponseBuilder()


@pytest.fixture
def coordinator():
    return JourneyIntelligenceCoordinator()


@pytest.mark.asyncio
async def test_assistant_query_missing_route_context(response_builder):
    """When no active journey is in progress, assistant must not report route score or fabricate telemetry."""
    final_context = {"LLM": {"summary": "System Ready"}}
    res: AssistantResponse = response_builder.build_assistant_chat(
        final_context=final_context,
        user_id="u_test",
        query="What is my safety score?",
        active_journey=None,
        journey_history=[]
    )

    assert res.context.active_journey is False
    assert res.context.safety_score is None
    assert res.reasoning.confidence is None
    assert "No active journey" in res.content
    assert "98" not in res.content
    assert "optimal lighting" not in res.content
    assert "crowd density" not in res.content
    assert "zero community incident" not in res.content


@pytest.mark.asyncio
async def test_assistant_query_route_score_unavailable(response_builder):
    """When active journey has no available score (insufficient coverage), assistant communicates limitation."""
    mock_active_journey = {
        "source": "13.0827, 80.2707",
        "destination": "13.0600, 80.2500",
        "plan": {
            "selected_route": {
                "route_identifier": "route_unscored",
                "safety_score": None,
                "score_status": "NO_SCOREABLE_SEGMENTS"
            }
        },
        "planned_routes": [
            {
                "id": "route_unscored",
                "safety_score": None,
                "score_status": "NO_SCOREABLE_SEGMENTS"
            }
        ]
    }
    final_context = {"LLM": {"summary": "Context active"}}
    res: AssistantResponse = response_builder.build_assistant_chat(
        final_context=final_context,
        user_id="u_test",
        query="What is my route safety score?",
        active_journey=mock_active_journey,
        journey_history=[]
    )

    assert res.context.active_journey is True
    assert res.context.safety_score is None
    assert res.reasoning.confidence is None
    assert "currently unavailable" in res.content
    assert "98" not in res.content
    assert "90" not in res.content
    assert "optimal lighting" not in res.content
    assert "zero community incident" not in res.content


@pytest.mark.asyncio
async def test_assistant_query_valid_supported_score_with_disclosure(response_builder):
    """When active journey has a valid score, assistant reports exact score and mandatory synthetic disclosure."""
    mock_active_journey = {
        "source": "13.0827, 80.2707",
        "destination": "13.0600, 80.2500",
        "plan": {
            "selected_route": {
                "route_identifier": "route_scored",
                "safety_score": 74.2,
                "score_status": "READY"
            }
        },
        "planned_routes": [
            {
                "id": "route_scored",
                "safety_score": 74.2,
                "score_status": "READY"
            }
        ]
    }
    final_context = {"LLM": {"summary": "Route scored"}}
    res: AssistantResponse = response_builder.build_assistant_chat(
        final_context=final_context,
        user_id="u_test",
        query="How safe is my path?",
        active_journey=mock_active_journey,
        journey_history=[]
    )

    assert res.context.active_journey is True
    assert res.context.safety_score == 74.2
    assert res.reasoning.confidence is None
    assert "74.2%" in res.content
    assert "synthetic environmental proxy" in res.content
    assert "not represent empirical crime occurrence" in res.content
    assert "98%" not in res.content
    assert "optimal lighting" not in res.content


@pytest.mark.asyncio
async def test_coordinator_execute_pipeline_non_road_workflow(coordinator):
    """Non-road workflows (assistant, profile, dashboard, emergency) do not fabricate ML predictions."""
    res_assistant = await coordinator.execute_pipeline("assistant", {"user_id": "u_test", "query": "init"})
    ml_pred = res_assistant.get("MLPrediction", {})
    assert ml_pred.get("safety_score") is None
    assert ml_pred.get("confidence") is None
    assert ml_pred.get("status") == "UNAVAILABLE"
    assert ml_pred.get("safety_score") != 90.0

    res_dash = await coordinator.execute_pipeline("dashboard", {"user_id": "u_test"})
    assert res_dash.get("MLPrediction", {}).get("safety_score") is None
    assert res_dash.get("MLPrediction", {}).get("confidence") is None


@pytest.mark.asyncio
async def test_coordinator_execute_pipeline_road_scoring_error_visible(coordinator, monkeypatch):
    """Genuine ML prediction errors on road scoring are not converted into fake success scores."""
    def broken_predict(*args, **kwargs):
        raise RuntimeError("LightGBM segment feature mismatch error")

    monkeypatch.setattr(coordinator.ml_predictor, "predict", broken_predict)

    res = await coordinator.execute_pipeline("journey_plan", {"source": "A", "destination": "B"})
    ml_pred = res.get("MLPrediction", {})
    assert ml_pred.get("status") == "INFERENCE_FAILED"
    assert ml_pred.get("safety_score") is None
    assert ml_pred.get("confidence") is None
    assert "LightGBM segment feature mismatch error" in ml_pred.get("error", "")


@pytest.mark.asyncio
async def test_reasoning_tool_absence_of_unsupported_assertions():
    """ReasoningTool fallback does not assert zero community hazard reports or optimal lighting."""
    tool = ReasoningTool()
    res = await tool.execute({"context": {"decision": {"recommended_route": "Route A"}}})
    summary = res.get("summary", "")
    reasoning = res.get("reasoning", [])

    assert "zero community hazard" not in summary.lower()
    assert "optimal lighting" not in summary.lower()
    for step in reasoning:
        assert "zero community hazard" not in step.lower()
        assert "low crowds" not in step.lower()
        assert "excellent lighting" not in step.lower()


@pytest.mark.asyncio
async def test_active_monitor_tick_no_fabricated_scores(coordinator):
    """Active monitor tick does not emit fabricated 92 score or lighting decrease claims."""
    tick_result = await coordinator.active_monitor_tick({}, tick_count=4)
    assert tick_result is not None
    assert "new_safety_score" not in tick_result
    assert "lighting" not in tick_result.get("message", "").lower()
    assert tick_result.get("status") == "MONITORING"
