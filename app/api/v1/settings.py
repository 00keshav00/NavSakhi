from fastapi import APIRouter, Depends
from typing import Any
from app.schemas.responses import StandardResponse
from app.schemas.settings_schemas import SettingsResponse
from app.api.dependencies import get_current_user_id

router = APIRouter()

@router.get("/", response_model=StandardResponse[SettingsResponse])
async def get_settings(user_id: str = Depends(get_current_user_id)):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    settings = await coordinator.build_settings_response(user_id)
    return StandardResponse(success=True, data=settings)

@router.patch("/", response_model=StandardResponse[Any])
async def update_settings(data: SettingsResponse, user_id: str = Depends(get_current_user_id)):
    return StandardResponse(success=True, data={"message": "Settings updated"})
