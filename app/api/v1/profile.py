from fastapi import APIRouter, Depends
from typing import Any
from app.schemas.responses import StandardResponse
from app.schemas.profile_schemas import ProfileResponse
from app.schemas.user_schemas import UserUpdate, ProfileUpdate
from app.repositories.journey_repository import JourneyRepository
from app.repositories.community_repository import CommunityRepository
from app.api.dependencies import (
    get_current_user_id, get_user_service, 
    get_journey_repository, get_community_repository
)

router = APIRouter()

@router.get("/", response_model=StandardResponse[ProfileResponse])
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    user_service: Any = Depends(get_user_service),
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    community_repo: CommunityRepository = Depends(get_community_repository)
):
    user = await user_service.get_user_profile(user_id)
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    profile = await coordinator.build_profile_response(
        user_id,
        user=user,
        journey_repo=journey_repo,
        community_repo=community_repo
    )
    return StandardResponse(success=True, data=profile)

@router.put("/", response_model=StandardResponse[ProfileResponse])
async def update_profile(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: Any = Depends(get_user_service),
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    community_repo: CommunityRepository = Depends(get_community_repository)
):
    if data.preferences:
        await user_service.update_preferences(user_id, data)
        
    profile_dict = {}
    if data.full_name is not None:
        profile_dict["full_name"] = data.full_name
    phone = data.phone_number or getattr(data, "phone", None)
    if phone is not None:
        profile_dict["phone_number"] = phone
    city = getattr(data, "current_city", None)
    if city is not None:
        profile_dict["current_city"] = city
    if data.age is not None:
        profile_dict["age"] = data.age
        
    if profile_dict and hasattr(user_service, "update_profile"):
        await user_service.update_profile(user_id, ProfileUpdate(**profile_dict))

    user = await user_service.get_user_profile(user_id)
    from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
    coordinator = JourneyIntelligenceCoordinator()
    profile = await coordinator.build_profile_response(
        user_id,
        user=user,
        journey_repo=journey_repo,
        community_repo=community_repo
    )
    return StandardResponse(success=True, data=profile)

