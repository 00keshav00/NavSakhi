from fastapi import APIRouter, Depends
from typing import Any
import uuid
from app.schemas.responses import StandardResponse
from app.schemas.emergency_schemas import SOSTrigger, SOSResponse
from app.services.emergency_service import EmergencyService
from app.services.emergency_session_service import emergency_session_registry
from app.api.dependencies import get_emergency_service, get_current_user_id
from app.api.exceptions import ForbiddenException

router = APIRouter()

@router.post("/sos", response_model=StandardResponse[SOSResponse])
async def trigger_sos(
    data: SOSTrigger,
    user_id: str = Depends(get_current_user_id),
    emergency_service: EmergencyService = Depends(get_emergency_service)
):
    try:
        result = await emergency_service.trigger_sos(user_id, data)
        session_id = result.get("session_id") if isinstance(result, dict) else None
    except Exception:
        session_id = None

    if not session_id:
        session_id = "sos_" + str(uuid.uuid4())[:8]

    # Register session ownership for WebSocket and REST streaming security
    emergency_session_registry.register_session(
        session_id=session_id,
        user_id=user_id,
        journey_id=data.journey_id
    )

    resp = SOSResponse(session_id=session_id)
    return StandardResponse(success=True, data=resp)

@router.get("/{session_id}/status", response_model=StandardResponse[Any])
async def get_emergency_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    session = emergency_session_registry.get_session(session_id)
    if session and not emergency_session_registry.is_authorized(session_id, user_id):
        raise ForbiddenException("You do not have permission to access this emergency session.")

    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    response = await coordinator.build_emergency_status(session_id, user_id)
    return StandardResponse(success=True, data=response)
