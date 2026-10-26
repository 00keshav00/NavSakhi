from typing import List
from fastapi import APIRouter, Depends
from app.schemas.responses import StandardResponse
from app.schemas.user_schemas import (
    UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse,
    ProfileUpdate, EmergencyContactCreate, EmergencyContactUpdate
)
from app.models.user import EmergencyContact
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.api.dependencies import get_user_service, get_current_user_id

router = APIRouter()

def _to_user_response(user) -> UserResponse:
    profile_settings = getattr(user, "profile_settings", {}) or {}
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        preferences=user.preferences,
        emergency_contacts=user.emergency_contacts,
        full_name=profile_settings.get("full_name", user.username),
        phone_number=profile_settings.get("phone_number"),
        age=profile_settings.get("age"),
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

@router.patch("/me", response_model=StandardResponse[UserResponse])
@router.put("/me", response_model=StandardResponse[UserResponse])
async def update_profile_details(
    data: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.update_profile(user_id, data)
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

@router.get("/me/emergency-contacts", response_model=StandardResponse[List[EmergencyContact]])
async def get_emergency_contacts(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    contacts = await user_service.get_emergency_contacts(user_id)
    return StandardResponse(success=True, data=contacts)

@router.post("/me/emergency-contacts", response_model=StandardResponse[UserResponse])
async def add_emergency_contact(
    data: EmergencyContactCreate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    contact = EmergencyContact(
        name=data.name,
        phone_number=data.phone_number,
        relationship=data.relationship or "Family",
        email=data.email,
        is_primary=data.is_primary
    )
    user = await user_service.add_emergency_contact(user_id, contact)
    return StandardResponse(success=True, data=_to_user_response(user))

@router.put("/me/emergency-contacts/{contact_id}", response_model=StandardResponse[UserResponse])
async def update_emergency_contact(
    contact_id: str,
    data: EmergencyContactUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    existing_contacts = await user_service.get_emergency_contacts(user_id)
    target = next((c for c in existing_contacts if c.id == contact_id), None)
    if not target:
        from app.api.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("Emergency contact")

    updated = EmergencyContact(
        id=contact_id,
        name=data.name if data.name is not None else target.name,
        phone_number=data.phone_number if data.phone_number is not None else target.phone_number,
        relationship=data.relationship if data.relationship is not None else target.relationship,
        email=data.email if data.email is not None else target.email,
        is_primary=data.is_primary if data.is_primary is not None else target.is_primary
    )
    user = await user_service.update_emergency_contact(user_id, contact_id, updated)
    return StandardResponse(success=True, data=_to_user_response(user))

@router.delete("/me/emergency-contacts/{contact_id}", response_model=StandardResponse[UserResponse])
async def delete_emergency_contact(
    contact_id: str,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.delete_emergency_contact(user_id, contact_id)
    return StandardResponse(success=True, data=_to_user_response(user))

