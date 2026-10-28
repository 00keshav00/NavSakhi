from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.connection import get_database

from app.repositories.user_repository import UserRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.community_repository import CommunityRepository
from app.repositories.chat_repository import ChatRepository

from app.services.user_service import UserService
from app.services.journey_service import JourneyService
from app.services.community_service import CommunityService
from app.services.emergency_service import EmergencyService
from app.services.chat_service import ChatService

from typing import Optional
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService
from app.api.exceptions import UnauthorizedException
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authentication token is missing.")
    payload = AuthService.decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload: missing user identity.")
    return str(user_id)


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[str]:
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = AuthService.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        return str(user_id) if user_id else None
    except Exception:
        return None


def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> UserRepository:
    return UserRepository(db)

def get_journey_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> JourneyRepository:
    return JourneyRepository(db)

def get_community_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> CommunityRepository:
    return CommunityRepository(db)

def get_chat_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> ChatRepository:
    return ChatRepository(db)

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
) -> User:
    return await user_service.get_user_profile(user_id)

def get_community_service(repo: CommunityRepository = Depends(get_community_repository)) -> CommunityService:
    return CommunityService(repo)


def get_chat_service(repo: ChatRepository = Depends(get_chat_repository)) -> ChatService:
    return ChatService(repo)

# Providers

from app.providers.routing.provider import OSRMRoutingProvider
from app.intelligence.journey.providers import RoutingProvider, LocationProvider, WeatherProvider, TransitProvider, ReportsProvider
from app.providers.location.provider import NominatimLocationProvider
from app.providers.weather.provider import OpenWeatherProvider
from app.providers.transit.provider import PlaceholderTransitProvider
from app.providers.reports.provider import MongoReportsProvider

def get_routing_provider() -> RoutingProvider:
    """Instantiate and return the Routing Provider."""
    return OSRMRoutingProvider()

def get_location_provider() -> LocationProvider:
    """Instantiate and return the Location Provider."""
    return NominatimLocationProvider()

def get_weather_provider() -> WeatherProvider:
    """Instantiate and return the Weather Provider."""
    return OpenWeatherProvider()

def get_transit_provider() -> TransitProvider:
    """Instantiate and return the Transit Provider."""
    return PlaceholderTransitProvider()

def get_reports_provider(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReportsProvider:
    """Instantiate and return the Reports Provider."""
    return MongoReportsProvider(db)

from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator

_global_journey_coordinator: Optional[JourneyIntelligenceCoordinator] = None

def get_journey_coordinator() -> JourneyIntelligenceCoordinator:
    """Return the shared Journey Intelligence Coordinator singleton."""
    global _global_journey_coordinator
    if _global_journey_coordinator is None:
        _global_journey_coordinator = JourneyIntelligenceCoordinator()
    return _global_journey_coordinator

def get_journey_service(
    repo: JourneyRepository = Depends(get_journey_repository),
    coordinator: JourneyIntelligenceCoordinator = Depends(get_journey_coordinator)
) -> JourneyService:
    return JourneyService(repo, coordinator)

from app.intelligence.emergency.coordinator import EmergencyIntelligenceCoordinator

def get_emergency_coordinator() -> EmergencyIntelligenceCoordinator:
    return EmergencyIntelligenceCoordinator()

def get_emergency_service(
    user_repo: UserRepository = Depends(get_user_repository),
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    coordinator: EmergencyIntelligenceCoordinator = Depends(get_emergency_coordinator)
) -> EmergencyService:
    return EmergencyService(user_repo, journey_repo, coordinator)
