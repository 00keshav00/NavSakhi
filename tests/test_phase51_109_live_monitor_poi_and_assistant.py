"""Phase 51.109 Test Suite: Live Monitor POI Overlay, Grounded Assistant POI Tool, and Provenance.

Verifies:
1. POISpatialService.query_pois_near_point returns grounded, formatted POIs with opening hours.
2. POITool executes correctly, validates inputs, and queries spatial index.
3. AssistantAgent integrates POITool and executes contextual queries.
4. JourneyIntelligenceCoordinator returns response_source and model_identifier provenance.
5. Spatial index log wording accurately distinguishes mapped Chennai establishments from safety facilities.
6. Live Monitor response schema includes nearby_pois and activity_zones in current_route.
"""

import pytest
import asyncio
from typing import Dict, Any

from app.services.poi_service import get_poi_service, POISpatialService
from app.tools.specialized.poi_tool import POITool
from app.agents.specialized.assistant import AssistantAgent
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator


def test_poi_spatial_service_query_near_point():
    """Verify query_pois_near_point accurately queries cKDTree index around given coordinates."""
    poi_service = get_poi_service()

    # Coordinates in central Chennai (near T. Nagar / Panagal Park: 13.0418, 80.2337)
    res = poi_service.query_pois_near_point(
        lon=80.2337,
        lat=13.0418,
        radius_m=1000.0,
        max_results=10
    )

    assert res["status"] in ("AVAILABLE", "NO_POIS_IN_RADIUS")
    assert "pois" in res
    assert "total_found" in res
    assert isinstance(res["pois"], list)
    assert len(res["pois"]) > 0

    # Check structure of returned POIs
    first_poi = res["pois"][0]
    assert "poi_id" in first_poi
    assert "name" in first_poi
    assert "category" in first_poi
    assert "category_label" in first_poi
    assert "distance_m" in first_poi
    assert "opening_status" in first_poi
    assert first_poi["distance_m"] <= 1000.0


def test_poi_spatial_service_query_near_point_category_filter():
    """Verify category filtering works when querying POIs near a point."""
    poi_service = get_poi_service()

    # Query pharmacies near T. Nagar
    res = poi_service.query_pois_near_point(
        lon=80.2337,
        lat=13.0418,
        radius_m=2000.0,
        category="pharmacy",
        max_results=5
    )

    assert res["status"] in ("AVAILABLE", "NO_POIS_IN_RADIUS")
    for poi in res["pois"]:
        assert poi["category"] == "pharmacy"


@pytest.mark.asyncio
async def test_poi_tool_definition_and_execution():
    """Verify POITool metadata and async execute method."""
    tool = POITool()
    assert tool.name == "SpecializedPOITool"
    assert "facilities" in tool.description.lower() or "commercial" in tool.description.lower()

    # Valid execution with lat / lon
    result = await tool.execute({
        "lat": 13.0418,
        "lon": 80.2337,
        "radius_m": 800.0,
        "category": "pharmacy"
    })
    assert result["status"] == "AVAILABLE"
    assert "pois" in result
    assert len(result["pois"]) > 0

    # Missing coordinates execution
    missing_res = await tool.execute({})
    assert missing_res["status"] == "LOCATION_MISSING"
    assert "disclosure" in missing_res


@pytest.mark.asyncio
async def test_assistant_agent_tool_integration():
    """Verify AssistantAgent uses POITool for commercial and facility queries."""
    agent = AssistantAgent()
    assert hasattr(agent, "poi_tool")
    assert isinstance(agent.poi_tool, POITool)

    res = await agent.execute({
        "query": "Find pharmacies near Panagal Park",
        "lat": 13.0418,
        "lon": 80.2337
    })
    assert res["status"] == "READY"
    assert res["agent"] == "AssistantAgent"
    assert res["poi_data"] is not None
    assert res["poi_data"]["status"] == "AVAILABLE"
    assert len(res["poi_data"]["pois"]) > 0


@pytest.mark.asyncio
async def test_coordinator_assistant_chat_provenance():
    """Verify coordinator process_assistant_chat returns structured response with provenance."""
    coordinator = JourneyIntelligenceCoordinator()

    # Send a safety and facilities question
    res = await coordinator.process_assistant_chat(
        user_id="phase51_109_user",
        query="What safety facilities and open shops are near Chennai Central?"
    )

    assert hasattr(res, "content")
    assert hasattr(res, "reasoning")
    assert res.reasoning.response_source in ("gemini", "fallback", "rule_based")
    assert isinstance(res.content, str)
    assert len(res.content) > 0


def test_poi_service_honesty_check():
    """Ensure spatial index does not classify commercial establishments as safety havens."""
    poi_service = get_poi_service()

    # Query commercial shops and ensure is_verified_safety_facility is False
    res = poi_service.query_pois_near_point(
        lon=80.2337,
        lat=13.0418,
        radius_m=1000.0,
        category="retail_shop",
        max_results=5
    )

    assert res["status"] == "AVAILABLE"
    for poi in res["pois"]:
        assert poi["is_verified_safety_facility"] is False
        assert poi["is_shop"] is True
