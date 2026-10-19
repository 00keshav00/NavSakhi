from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.schemas.responses import StandardResponse
from app.schemas.user_schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.ticket_service import ticket_service
from app.api.dependencies import get_user_service, get_current_user_id

router = APIRouter()

@router.post("/register", response_model=StandardResponse[TokenResponse], status_code=201)
async def auth_register(
    data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.register_user(data)
    token = AuthService.create_access_token(user_id=str(user.id), email=user.email)
    user_data = UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        preferences=user.preferences,
        emergency_contacts=user.emergency_contacts,
        full_name=getattr(user, "profile_settings", {}).get("full_name", user.username) if isinstance(getattr(user, "profile_settings", None), dict) else user.username,
        is_active=getattr(user, "is_active", True),
        role="user"
    )
    return StandardResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user_data
        )
    )

@router.post("/login", response_model=StandardResponse[TokenResponse])
async def auth_login(
    data: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.authenticate_user(data.email, data.password)
    token = AuthService.create_access_token(user_id=str(user.id), email=user.email)
    user_data = UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        preferences=user.preferences,
        emergency_contacts=user.emergency_contacts,
        full_name=getattr(user, "profile_settings", {}).get("full_name", user.username) if isinstance(getattr(user, "profile_settings", None), dict) else user.username,
        is_active=getattr(user, "is_active", True),
        role="user"
    )
    return StandardResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user_data
        )
    )

@router.post("/ws-ticket", response_model=StandardResponse[Dict[str, Any]])
async def create_ws_ticket(user_id: str = Depends(get_current_user_id)):
    """Issue a short-lived, single-use ticket for WebSocket authentication."""
    ticket = ticket_service.issue_ticket(user_id)
    return StandardResponse(
        success=True,
        data={
            "ticket": ticket,
            "expires_in": ticket_service.ticket_ttl
        }
    )
