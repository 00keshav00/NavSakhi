from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.user_schemas import UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse
from app.models.user import EmergencyContact
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.api.dependencies import get_user_service, get_current_user_id

router = APIRouter()

def _to_user_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        preferences=user.preferences,
        emergency_contacts=user.emergency_contacts,
        full_name=getattr(user, "profile_settings", {}).get("full_name", user.username) if isinstance(getattr(user, "profile_settings", None), dict) else user.username,
        is_active=getattr(user, "is_active", True),
        role="user"
    )

@router.get("/me", response_model=StandardResponse[UserResponse])
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_user_profile(user_id)
    return StandardResponse(success=True, data=_to_user_response(user))

@router.post("/", response_model=StandardResponse[UserResponse], status_code=201)
async def register(
    data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.register_user(data)
    return StandardResponse(success=True, data=_to_user_response(user))

@router.post("/login", response_model=StandardResponse[TokenResponse])
async def login(
    data: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.authenticate_user(data.email, data.password)
    token = AuthService.create_access_token(user_id=str(user.id), email=user.email)
    return StandardResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            user=_to_user_response(user)
        )
    )

@router.patch("/me/preferences", response_model=StandardResponse[UserResponse])
async def update_preferences(
    data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.update_preferences(user_id, data)
    return StandardResponse(success=True, data=_to_user_response(user))

@router.post("/me/emergency-contacts", response_model=StandardResponse[UserResponse])
async def add_emergency_contact(
    data: EmergencyContact,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.add_emergency_contact(user_id, data)
    return StandardResponse(success=True, data=_to_user_response(user))
