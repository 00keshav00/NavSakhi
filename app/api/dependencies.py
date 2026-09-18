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

# Currently mocked for simplicity, replace with real auth
async def get_current_user_id() -> str:
    return "650c1f1e1c9d440000000000" # Dummy ObjectId

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

def get_journey_coordinator() -> JourneyIntelligenceCoordinator:
    """Instantiate and return the Journey Intelligence Coordinator."""
    return JourneyIntelligenceCoordinator()

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
