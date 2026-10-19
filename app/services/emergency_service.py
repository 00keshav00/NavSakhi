from app.repositories.user_repository import UserRepository
from app.repositories.journey_repository import JourneyRepository
from app.schemas.emergency_schemas import SOSTrigger
from app.intelligence.emergency.coordinator import EmergencyIntelligenceCoordinator

class EmergencyService:
    def __init__(self, user_repo: UserRepository, journey_repo: JourneyRepository, coordinator: EmergencyIntelligenceCoordinator = None):
        self.user_repo = user_repo
        self.journey_repo = journey_repo
        self.coordinator = coordinator or EmergencyIntelligenceCoordinator()

    async def trigger_sos(self, user_id: str, data: SOSTrigger) -> dict:
        """
        Delegates the SOS trigger entirely to the Emergency Agent.
        """
        context = {
            "current_location": data.current_location,
            "journey_id": data.journey_id
        }
        # The agent returns the session dictionary containing session_id
        return await self.coordinator.handle_sos_trigger(user_id, context)
