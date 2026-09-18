from app.repositories.journey_repository import JourneyRepository
from app.models.journey import Journey, JourneyStateEnum, JourneyPlan, JourneyProgress, TransportMode, Location
from app.schemas.journey_schemas import JourneyCreate
from app.api.exceptions import ResourceNotFoundException, InvalidStateTransitionError

from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.intelligence.journey.models import JourneyContext
from datetime import datetime
from typing import Any

class JourneyService:
    def __init__(self, journey_repo: JourneyRepository, coordinator: JourneyIntelligenceCoordinator = None):
        self.journey_repo = journey_repo
        if coordinator is None:
            self.coordinator = JourneyIntelligenceCoordinator()
        else:
            self.coordinator = coordinator

    async def get_journey_details(self, journey_id: str) -> Journey:
        journey = await self.journey_repo.get_by_id(journey_id)
        if not journey:
            raise ResourceNotFoundException("Journey")
        return journey

    async def create_journey(self, user_id: str, data: JourneyCreate) -> Any:
        """Journey Creation"""
        journey = Journey(
            user_id=user_id,
            source=Location(type="Point", coordinates=[77.5946, 12.9716]),
            destination=Location(type="Point", coordinates=[77.5946, 12.9716])
        )
        journey.state.current_state = JourneyStateEnum.CREATED
        journey.plan = JourneyPlan(transport_mode="WALK")
        
        created_journey = await self.journey_repo.create(journey)
        await self.initialize_journey(str(created_journey.id))
        
        return await self.coordinator.build_journey_plan_response(str(created_journey.id), data)

    async def initialize_journey(self, journey_id: str) -> Journey:
        """Journey Initialization: Delegates to agent to plan the journey"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state != JourneyStateEnum.CREATED:
            raise InvalidStateTransitionError("Journey must be in CREATED state to initialize.")
            
        journey.state.current_state = JourneyStateEnum.PLANNING
        await self.journey_repo.update(journey_id, journey.model_dump())
        
        # Stale methods removed during architecture repair.
        # Coordinator execution is handled by build_journey_plan_response in create_journey.
        
        # Mocking the successful planning outcome for now
        journey.state.current_state = JourneyStateEnum.PLANNED
        return await self.journey_repo.update(journey_id, journey.model_dump())

    async def _active_monitor_loop(self, journey_id: str, context: JourneyContext):
        from app.api.websockets.journey_ws import journey_manager
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        tick_count = 0
        while True:
            # Check current state
            journey = await self.get_journey_details(journey_id)
            if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
                logger.info(f"Monitor loop terminating for {journey_id} - state is {journey.state.current_state.value}")
                break
                
            tick_count += 1
            if self.coordinator:
                alert = await self.coordinator.active_monitor_tick(context, tick_count)
                if alert:
                    logger.info(f"Agent generated alert for {journey_id}: {alert}")
                    await journey_manager.send_personal_message(alert, journey_id)
            
            await asyncio.sleep(5) # Poll every 5 seconds for simulation

    async def start_journey(self, journey_id: str) -> Journey:
        """Journey Start"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.PLANNED, JourneyStateEnum.PAUSED]:
            raise InvalidStateTransitionError("Journey must be PLANNED or PAUSED to start.")
            
        journey.state.current_state = JourneyStateEnum.ACTIVE
        await self.journey_repo.update(journey_id, journey.model_dump())
        
        journey.state.current_state = JourneyStateEnum.MONITORING
        updated_journey = await self.journey_repo.update(journey_id, journey.model_dump())
        
        # Spawn the autonomous background loop
        import asyncio
        context = JourneyContext(
            journey_id=journey_id,
            user_id=str(journey.user_id),
            source=journey.source,
            destination=journey.destination,
            transport_mode=journey.plan.transport_mode if journey.plan else TransportMode.WALK,
            timestamp=datetime.utcnow().isoformat()
        )
        asyncio.create_task(self._active_monitor_loop(journey_id, context))
        
        return updated_journey

    async def pause_journey(self, journey_id: str) -> Journey:
        """Journey Pause"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            raise InvalidStateTransitionError("Journey must be ACTIVE or MONITORING to pause.")
            
        journey.state.current_state = JourneyStateEnum.PAUSED
        return await self.journey_repo.update(journey_id, journey.model_dump())

    async def resume_journey(self, journey_id: str) -> Journey:
        """Journey Resume"""
        return await self.start_journey(journey_id)

    async def cancel_journey(self, journey_id: str) -> Journey:
        """Journey Cancellation"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state in [JourneyStateEnum.COMPLETED, JourneyStateEnum.FAILED, JourneyStateEnum.CANCELLED]:
            raise InvalidStateTransitionError("Cannot cancel a completed, failed, or already cancelled journey.")
            
        journey.state.current_state = JourneyStateEnum.CANCELLED
        return await self.journey_repo.update(journey_id, journey.model_dump())

    async def complete_journey(self, journey_id: str) -> Journey:
        """Journey Completion"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            raise InvalidStateTransitionError("Journey must be ACTIVE or MONITORING to complete.")
            
        journey.state.current_state = JourneyStateEnum.COMPLETED
        return await self.journey_repo.update(journey_id, journey.model_dump())

    async def update_progress(self, journey_id: str, distance_covered: float, updated_eta: float) -> Journey:
        """Journey Progress Management"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            raise InvalidStateTransitionError("Cannot update progress unless journey is active or monitoring.")
            
        if not journey.progress:
            journey.progress = JourneyProgress()
            
        journey.progress.distance_covered = distance_covered
        journey.progress.updated_eta = updated_eta
        return await self.journey_repo.update(journey_id, journey.model_dump())
