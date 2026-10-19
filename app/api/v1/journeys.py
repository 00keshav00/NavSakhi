from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from app.schemas.responses import StandardResponse
from app.schemas.journey_schemas import JourneyCreate, JourneyResponse, JourneyPlanResponse
from app.models.journey import JourneyStateEnum
from app.services.journey_service import JourneyService
from app.services.autocomplete_service import global_autocomplete_service, LocationSuggestion
from app.api.dependencies import get_journey_service, get_current_user_id, get_optional_user_id
from app.api.exceptions import ForbiddenException

def _verify_journey_ownership(journey, user_id: str) -> None:
    if str(journey.user_id) != str(user_id):
        raise ForbiddenException("You do not have permission to access or modify this journey.")

router = APIRouter()

@router.post("/", response_model=StandardResponse[JourneyPlanResponse])
async def create_journey(
    data: JourneyCreate,
    user_id: Optional[str] = Depends(get_optional_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    if user_id:
        plan_response = await journey_service.create_journey(user_id, data)
    else:
        plan_response = await journey_service.plan_guest_journey(data)
    return StandardResponse(success=True, data=plan_response)

@router.post("/guest/plan", response_model=StandardResponse[JourneyPlanResponse])
async def plan_guest_journey(
    data: JourneyCreate,
    journey_service: JourneyService = Depends(get_journey_service)
):
    """
    Public read-only guest route planning endpoint.
    Permits unauthenticated multimodal exploration across the supported transit and road network.
    Does not persist user journey documents or require session state.
    """
    plan_response = await journey_service.plan_guest_journey(data)
    return StandardResponse(success=True, data=plan_response)
 
@router.get("/active", response_model=StandardResponse[Optional[JourneyResponse]])
async def get_active_journey(
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_active_journey(user_id)
    if not journey:
        return StandardResponse(success=True, data=None)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/autocomplete", response_model=StandardResponse[List[LocationSuggestion]])
async def autocomplete_locations(
    q: str = Query(..., min_length=1, description="Location search query or coordinates"),
    limit: int = Query(8, ge=1, le=20, description="Maximum suggestions to return"),
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Search for places, transit stations, POIs, or parse coordinates
    with verified local data priority and OSM Nominatim coverage.
    """
    results = await global_autocomplete_service.get_suggestions(query=q, limit=limit)
    return StandardResponse(success=True, data=results)

@router.get("/{journey_id}", response_model=StandardResponse[JourneyResponse])
async def get_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

class StartJourneyRequest(BaseModel):
    selected_route_id: Optional[str] = None

@router.post("/{journey_id}/start", response_model=StandardResponse[JourneyResponse])
async def start_journey(
    journey_id: str,
    payload: Optional[StartJourneyRequest] = None,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    selected_id = payload.selected_route_id if payload else None
    journey = await journey_service.start_journey(journey_id, selected_route_id=selected_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/pause", response_model=StandardResponse[JourneyResponse])
async def pause_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    journey = await journey_service.pause_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/resume", response_model=StandardResponse[JourneyResponse])
async def resume_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    journey = await journey_service.resume_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/cancel", response_model=StandardResponse[JourneyResponse])
async def cancel_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    journey = await journey_service.cancel_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/complete", response_model=StandardResponse[JourneyResponse])
async def complete_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    journey = await journey_service.complete_journey(journey_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.post("/{journey_id}/reroute", response_model=StandardResponse[JourneyResponse])
async def reroute_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/progress", response_model=StandardResponse[JourneyResponse])
async def get_journey_progress(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/alerts", response_model=StandardResponse[JourneyResponse])
async def get_journey_alerts(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

@router.get("/{journey_id}/segment", response_model=StandardResponse[JourneyResponse])
async def get_journey_segment(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)
    return StandardResponse(success=True, data=JourneyResponse.model_validate(journey.model_dump(by_alias=True)))

from typing import Any
import time

@router.get("/{journey_id}/monitor", response_model=StandardResponse[Any])
async def monitor_journey(
    journey_id: str,
    user_id: str = Depends(get_current_user_id),
    journey_service: JourneyService = Depends(get_journey_service)
):
    journey = await journey_service.get_journey_details(journey_id)
    _verify_journey_ownership(journey, user_id)

    is_active = journey.state.current_state in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]

    # 1. Resolve selected route from planned routes
    target_route = None
    if journey.planned_routes:
        if journey.selected_route_id:
            for r in journey.planned_routes:
                if r.get("id") == journey.selected_route_id or r.get("route_id") == journey.selected_route_id:
                    target_route = r
                    break
        if not target_route:
            target_route = journey.planned_routes[0]

    # 2. Extract metrics and authentic geometry
    route_dist = 0.0
    route_dur = 0.0
    route_score = None
    route_geom = {"type": "FeatureCollection", "features": []}

    if target_route:
        raw_dist = target_route.get("distance", 0.0)
        try:
            if isinstance(raw_dist, str):
                if "km" in raw_dist:
                    route_dist = float(raw_dist.replace("km", "").strip()) * 1000.0
                elif "m" in raw_dist:
                    route_dist = float(raw_dist.replace("m", "").strip())
                else:
                    route_dist = float(raw_dist)
            else:
                route_dist = float(raw_dist)
        except Exception:
            route_dist = 0.0

        raw_dur = target_route.get("estimated_duration") or target_route.get("duration") or 0.0
        try:
            if isinstance(raw_dur, str):
                if "min" in raw_dur:
                    route_dur = float(raw_dur.replace("mins", "").replace("min", "").strip()) * 60.0
                else:
                    route_dur = float(raw_dur)
            else:
                route_dur = float(raw_dur)
        except Exception:
            route_dur = 0.0

        route_score = target_route.get("safety_score")

        features = []
        for seg in target_route.get("segments", []):
            poly = seg.get("polyline")
            if poly and isinstance(poly, dict):
                features.append(poly)
        if features:
            route_geom = {"type": "FeatureCollection", "features": features}

    # 3. Determine telemetry and progress state
    prog = journey.progress
    has_telemetry = (
        prog is not None
        and prog.current_location is not None
        and prog.current_location.coordinates is not None
        and len(prog.current_location.coordinates) >= 2
    )

    now = time.time()
    is_stale = False
    if has_telemetry and journey.last_telemetry_timestamp is not None:
        if (now - journey.last_telemetry_timestamp > 120.0) and is_active:
            is_stale = True

    if has_telemetry:
        status_label = "stale" if is_stale else prog.status
        current_loc = {
            "lat": prog.current_location.coordinates[1],
            "lng": prog.current_location.coordinates[0],
            "accuracy": prog.accuracy
        }
        dist_remaining = prog.distance_remaining
        eta = prog.eta_remaining or prog.updated_eta
        progress_pct = prog.progress_percentage
    else:
        status_label = journey.state.current_state.value.lower()
        if status_label in ["planned", "created"]:
            status_label = "waiting_for_gps"
        elif status_label in ["active", "monitoring"]:
            status_label = "unavailable"
        current_loc = None
        dist_remaining = route_dist
        eta = route_dur
        progress_pct = 0.0

    monitor_response = {
        "journey_id": journey_id,
        "is_active": is_active,
        "status_summary": {
            "distance_remaining": dist_remaining,
            "eta": eta,
            "transport_mode": (
                journey.plan.transport_mode.value
                if journey.plan and hasattr(journey.plan.transport_mode, 'value')
                else "walking"
            ),
            "progress_percentage": progress_pct,
            "current_segment": prog.current_segment if prog and prog.current_segment else ("En Route" if is_active else "Journey Planned"),
            "status": status_label,
            "is_on_route": prog.is_on_route if prog else True,
            "distance_from_route": prog.distance_from_route if prog else None,
            "last_updated": prog.last_updated.isoformat() if prog and prog.last_updated else None
        },
        "safety_score": {
            "current": route_score,
            "trend": "stable",
            "confidence": None,
            "risk_level": "Low" if (route_score and route_score >= 80) else "Moderate"
        },
        "ai_recommendation": {
            "recommendation": "Maintain awareness along your planned route.",
            "reason": "Route monitoring is active. Deviation or delays will be reflected immediately.",
            "confidence": None,
            "warnings": [],
            "suggested_action": "Keep device accessible and follow navigation."
        },
        "environment_summary": {
            "weather_condition": "Clear",
            "visibility": "Normal",
            "lighting": "Optimal",
            "crowd_density": "Moderate",
            "police_presence": "Not verified in real time",
            "road_condition": "Dry"
        },
        "realtime_alerts": [
            {
                "id": a.alert_identifier,
                "severity": a.severity.lower(),
                "time": a.created_timestamp.isoformat(),
                "description": a.message
            }
            for a in journey.alerts
        ],
        "agent_timeline": [
            {
                "id": f"t_{i}",
                "action": f"State: {t.to_state.value}",
                "time": t.timestamp.isoformat(),
                "icon": "check"
            }
            for i, t in enumerate(journey.state.state_history)
        ] if journey.state.state_history else [
            {
                "id": "t_init",
                "action": f"Journey status: {journey.state.current_state.value}",
                "time": journey.created_timestamp.isoformat(),
                "icon": "play"
            }
        ],
        "current_route": {
            "distance": route_dist,
            "duration": route_dur,
            "safety_score": route_score,
            "weather_impact": "Neutral",
            "community_impact": "Neutral",
            "risk_factors": [],
            "geometry": route_geom
        },
        "current_location": current_loc
    }

    return StandardResponse(success=True, data=monitor_response)
