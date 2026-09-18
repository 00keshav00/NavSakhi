from fastapi import APIRouter, Depends
from typing import Any
from app.schemas.responses import StandardResponse
from app.schemas.emergency_schemas import SOSTrigger, SOSResponse
from app.services.emergency_service import EmergencyService
from app.api.dependencies import get_emergency_service, get_current_user_id

router = APIRouter()

@router.post("/sos", response_model=StandardResponse[SOSResponse])
async def trigger_sos(
    data: SOSTrigger,
    user_id: str = Depends(get_current_user_id),
    emergency_service: EmergencyService = Depends(get_emergency_service)
):
    import uuid
    session_id = "sos_" + str(uuid.uuid4())[:8]
    resp = SOSResponse(session_id=session_id)
    return StandardResponse(success=True, data=resp)

@router.get("/{session_id}/status", response_model=StandardResponse[Any])
async def get_emergency_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    response = await coordinator.build_emergency_status(session_id, user_id)
    return StandardResponse(success=True, data=response)
