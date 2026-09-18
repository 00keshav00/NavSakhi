from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.journey_schemas import JourneyCreate, JourneyResponse, JourneyPlanResponse
from app.services.journey_service import JourneyService
from app.api.dependencies import get_journey_service, get_current_user_id

router = APIRouter()

@router.post("/", response_model=StandardResponse[JourneyPlanResponse])
async def create_journey(
    data: JourneyCreate,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    plan_response = await journey_service.create_journey(user_id, data)
    
    # API Verification Log
    if plan_response.recommended_routes:
        for route in plan_response.recommended_routes:
            for seg in route.segments:
                if hasattr(seg, 'polyline') and seg.polyline:
                    geo = seg.polyline.get("geometry", {})
                    print("\n=== STAGE 2: API RESPONSE ===")
                    import json
                    print(json.dumps(geo, indent=2))
                    break # Just print one for verification
            break
            
    return StandardResponse(success=True, data=plan_response)

@router.get("/{journey_id}", response_model=StandardResponse[JourneyResponse])
async def get_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/start", response_model=StandardResponse[JourneyResponse])
async def start_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.start_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/pause", response_model=StandardResponse[JourneyResponse])
async def pause_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.pause_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/resume", response_model=StandardResponse[JourneyResponse])
async def resume_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.resume_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/cancel", response_model=StandardResponse[JourneyResponse])
async def cancel_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.cancel_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/complete", response_model=StandardResponse[JourneyResponse])
async def complete_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.complete_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/reroute", response_model=StandardResponse[JourneyResponse])
async def reroute_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    # Stub: Delegate to service when implemented. Just returning the journey for now.
    journey = await journey_service.get_journey_details(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/progress", response_model=StandardResponse[JourneyResponse])
async def get_journey_progress(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    # Returning standard response structure. Progress is embedded in JourneyResponse.
    journey = await journey_service.get_journey_details(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/alerts", response_model=StandardResponse[JourneyResponse])
async def get_journey_alerts(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    # Returning standard response structure. Alerts are embedded in JourneyResponse.
    journey = await journey_service.get_journey_details(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/segment", response_model=StandardResponse[JourneyResponse])
async def get_journey_segment(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    # Returning standard response structure. Segments are embedded in JourneyPlan.
    journey = await journey_service.get_journey_details(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

from typing import Any
@router.get("/{journey_id}/monitor", response_model=StandardResponse[Any])
async def monitor_journey(
    journey_id: str,
    journey_service: JourneyService = Depends(get_journey_service)
):
    """
    Fallback polling endpoint for live monitoring, returning the exact schema
    expected by the frontend's LiveMonitorResponse.
    """
    fake_geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.5946, 12.9716],
                [77.5980, 12.9750],
                [77.6020, 12.9780]
            ]
        }
    }
    
    mock_response = {
        "journey_id": journey_id,
        "is_active": True,
        "status_summary": {
            "distance_remaining": 2100,
            "eta": 1440,
            "transport_mode": "walking",
            "progress_percentage": 5,
            "current_segment": "Approaching 4th Ave Intersection"
        },
        "safety_score": {
            "current": 98,
            "trend": "improving",
            "confidence": None, # Removed hardcoded
            "risk_level": "Low"
        },
        "ai_recommendation": {
            "recommendation": "Continue on the recommended route.",
            "reason": "Conditions remain optimal. Crowd density is stable and lighting is sufficient.",
            "confidence": None, # Removed hardcoded
            "warnings": ["Stay alert near the upcoming intersection."],
            "suggested_action": "Keep device accessible."
        },
        "environment_summary": {
            "weather_condition": "Clear",
            "visibility": "High (10km)",
            "lighting": "Optimal (Streetlights active)",
            "crowd_density": "Low",
            "police_presence": "Patrol within 1km",
            "road_condition": "Dry"
        },
        "realtime_alerts": [
            {"id": "a1", "severity": "info", "time": "5m ago", "description": "Traffic easing up ahead."}
        ],
        "agent_timeline": [
            {"id": "t1", "action": "Journey Started & Route Verified", "time": "10m ago", "icon": "play"},
            {"id": "t2", "action": "Weather context initialized: Clear skies", "time": "9m ago", "icon": "cloud"}
        ],
        "current_route": {
            "distance": 2100,
            "duration": 1440,
            "safety_score": 98,
            "weather_impact": "Positive",
            "community_impact": "Neutral",
            "risk_factors": ["Intersection crossing"],
            "geometry": fake_geojson
        },
        "current_location": {"lat": 12.9716, "lng": 77.5946}
    }
    
    return StandardResponse(success=True, data=mock_response)
