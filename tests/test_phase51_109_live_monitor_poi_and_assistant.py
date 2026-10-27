import pytest
import asyncio
from app.services.poi_service import get_poi_service
from app.tools.specialized.poi_tool import POITool
from app.tools.specialized.reasoning_tool import ReasoningTool, build_sanitized_chat_payload

@pytest.mark.asyncio
async def test_poi_service_query_near_point():
    """Verify that POISpatialService.query_pois_near_point retrieves real mapped Chennai POIs."""
    service = get_poi_service()
    # T. Nagar coordinates (lon, lat)
    lon, lat = 80.2337, 13.0418
    res = service.query_pois_near_point(lon, lat, radius_m=1200.0, max_results=10)

    assert res["status"] == "AVAILABLE"
    assert res["total_found"] > 0
    assert len(res["pois"]) > 0
    assert "OpenStreetMap" in res["disclosure"]

    first_poi = res["pois"][0]
    assert "poi_id" in first_poi
    assert "name" in first_poi
    assert "category" in first_poi
    assert "longitude" in first_poi
    assert "latitude" in first_poi
    assert "is_shop" in first_poi

@pytest.mark.asyncio
async def test_poi_tool_resolution():
    """Verify POITool resolves named Chennai hubs and queries establishments."""
    poi_tool = POITool()

    # Query with known Chennai hub
    res = await poi_tool.execute({
        "place": "T. Nagar",
        "radius_m": 1200.0,
        "max_results": 5
    })
    assert res["status"] == "AVAILABLE"
    assert len(res["pois"]) > 0

    # Query with missing location
    missing_res = await poi_tool.execute({})
    assert missing_res["status"] == "LOCATION_MISSING"
    assert missing_res["total_found"] == 0

@pytest.mark.asyncio
async def test_reasoning_tool_grounded_poi_query():
    """Verify ReasoningTool handles shop queries by grounding in POI records."""
    reasoning_tool = ReasoningTool()

    # 1. Query with location
    context_with_loc = {
        "query": "Are there any shops or pharmacies near T. Nagar?",
        "history": []
    }
    res_with_loc = await reasoning_tool.execute({"context": context_with_loc})
    assert res_with_loc["response_source"] in ["gemini", "fallback"]
    summary_text = res_with_loc["summary"].lower()
    # If fallback or gemini, should mention either specific shops or OpenStreetMap/Chennai context
    assert ("shop" in summary_text or "pharmacy" in summary_text or "t. nagar" in summary_text or "nagar" in summary_text)

    # 2. Query seeking nearby shops without location and without active journey
    context_no_loc = {
        "query": "Can you show me nearby grocery shops?",
        "history": []
    }
    res_no_loc = await reasoning_tool.execute({"context": context_no_loc})
    assert res_no_loc["response_source"] in ["gemini", "fallback"]
    summary_no_loc = res_no_loc["summary"].lower()
    # Must ask for location or specify route/corridor limitation
    assert any(term in summary_no_loc for term in ["which area", "which location", "landmark", "where", "corridor", "route", "chennai"])

def test_build_sanitized_chat_payload_poi_guidance():
    """Verify build_sanitized_chat_payload includes grounded POI guidelines."""
    dummy_pois = [
        {
            "name": "Apollo Pharmacy",
            "category": "pharmacy",
            "category_label": "Pharmacy",
            "distance_m": 150,
            "opening_hours": "24/7",
            "opening_status": "OPEN",
            "is_emergency": True,
            "is_safe_haven_eligible": True
        },
        {
            "name": "Saravana Stores",
            "category": "retail_shop",
            "category_label": "Retail Store",
            "distance_m": 300,
            "opening_hours": "09:00-21:00",
            "opening_status": "OPEN",
            "is_emergency": False,
            "is_safe_haven_eligible": False
        }
    ]
    payload = build_sanitized_chat_payload(
        query="What shops are near T. Nagar?",
        grounded_pois=dummy_pois,
        poi_location_name="T. Nagar"
    )

    prompt = payload["contents"][0]["parts"][0]["text"]
    assert "GROUNDED MAPPED ESTABLISHMENTS IN CHENNAI NEAR T. NAGAR:" in prompt
    assert "Apollo Pharmacy" in prompt
    assert "Saravana Stores" in prompt
    assert "commercial shops are mapped openstreetmap records, not emergency safe havens" in prompt.lower()
    assert "distinguish commercial businesses from emergency facilities" in prompt.lower()

def test_route_corridor_poi_query_and_monitor_contract():
    """Verify that route corridor queries extract shops, facilities, and activity zones for the monitor."""
    service = get_poi_service()
    # Route through T. Nagar / Guindy corridor
    sample_route_coords = [
        [80.2337, 13.0418],
        [80.2260, 13.0240],
        [80.2184, 13.0067]
    ]
    res = service.query_pois_near_route(sample_route_coords, corridor_m=800.0)
    assert "pois" in res
    assert "activity_zones" in res
    assert res["status"] in ["AVAILABLE", "EMPTY"]

    if res["pois"]:
        poi = res["pois"][0]
        # Verify required monitor fields
        assert "poi_id" in poi or "name" in poi
        assert "latitude" in poi
        assert "longitude" in poi
        assert "is_shop" in poi
