from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.user_schemas import UserCreate, UserResponse, UserUpdate
from app.models.user import EmergencyContact
from app.services.user_service import UserService
from app.api.dependencies import get_user_service, get_current_user_id

router = APIRouter()

@router.get("/me", response_model=StandardResponse[UserResponse])
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_user_profile(user_id)
    return StandardResponse(success=True, data=UserResponse(**user.model_dump(by_alias=True)))

@router.post("/", response_model=StandardResponse[UserResponse])
async def register(
    data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.register_user(data)
    return StandardResponse(success=True, data=UserResponse(**user.model_dump(by_alias=True)))

@router.patch("/me/preferences", response_model=StandardResponse[UserResponse])
async def update_preferences(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.update_preferences(user_id, data)
    return StandardResponse(success=True, data=UserResponse(**user.model_dump(by_alias=True)))

@router.post("/me/emergency-contacts", response_model=StandardResponse[UserResponse])
async def add_emergency_contact(
    data: EmergencyContact,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.add_emergency_contact(user_id, data)
    return StandardResponse(success=True, data=UserResponse(**user.model_dump(by_alias=True)))
