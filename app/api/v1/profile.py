from fastapi import APIRouter, Depends
from typing import Any
from app.schemas.responses import StandardResponse
from app.schemas.profile_schemas import ProfileResponse
from app.schemas.user_schemas import UserUpdate
from app.api.dependencies import get_current_user_id, get_user_service

router = APIRouter()

@router.get("/", response_model=StandardResponse[ProfileResponse])
async def get_profile(user_id: str = Depends(get_current_user_id)):
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    profile = await coordinator.build_profile_response(user_id)
    return StandardResponse(success=True, data=profile)

@router.put("/", response_model=StandardResponse[ProfileResponse])
async def update_profile(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: Any = Depends(get_user_service)
):
    await user_service.update_preferences(user_id, data)
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    profile = await coordinator.build_profile_response(user_id)
    return StandardResponse(success=True, data=profile)
