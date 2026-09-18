from fastapi import APIRouter

from app.api.v1.users import router as users_router
from app.api.v1.journeys import router as journeys_router
from app.api.v1.community import router as community_router
from app.api.v1.emergency import router as emergency_router
from app.api.v1.chat import router as chat_router
from app.api.v1.debug import router as debug_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.profile import router as profile_router
from app.api.v1.settings import router as settings_router

api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(journeys_router, prefix="/journeys", tags=["Journeys"])

api_router.include_router(community_router, prefix="/community", tags=["Community"])
api_router.include_router(emergency_router, prefix="/emergency", tags=["Emergency"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(debug_router, prefix="/debug", tags=["Debug"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(assistant_router, prefix="/assistant", tags=["Assistant"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
