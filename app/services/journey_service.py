from app.repositories.journey_repository import JourneyRepository
from app.models.journey import Journey, JourneyStateEnum, JourneyPlan, JourneyProgress, TransportMode, Location
from app.schemas.journey_schemas import JourneyCreate
from app.api.exceptions import ResourceNotFoundException, InvalidStateTransitionError

from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.intelligence.journey.models import JourneyContext
from datetime import datetime
from typing import Any, Optional

class JourneyService:
    def __init__(self, journey_repo: JourneyRepository, coordinator: JourneyIntelligenceCoordinator = None):
        self.journey_repo = journey_repo
        self._coordinator = coordinator

    @property
    def coordinator(self) -> JourneyIntelligenceCoordinator:
        if self._coordinator is None:
            self._coordinator = JourneyIntelligenceCoordinator()
        return self._coordinator

    async def get_journey_details(self, journey_id: str) -> Journey:
        journey = await self.journey_repo.get_by_id(journey_id)
        if not journey:
            raise ResourceNotFoundException("Journey")
        return journey

    async def get_active_journey(self, user_id: str) -> Optional[Journey]:
        return await self.journey_repo.get_active_journey(user_id)

    async def create_journey(self, user_id: str, data: JourneyCreate, cancel_check: Optional[Any] = None) -> Any:
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
        
        plan_response = await self.coordinator.build_journey_plan_response(str(created_journey.id), data, cancel_check=cancel_check)
        
        # Persist calculated route geometry onto the journey document for authentic progress tracking
        if plan_response and hasattr(plan_response, 'recommended_routes') and plan_response.recommended_routes:
            planned_routes_dump = [
                r.model_dump() if hasattr(r, 'model_dump') else r
                for r in plan_response.recommended_routes
            ]
            selected_id = planned_routes_dump[0].get("id") or planned_routes_dump[0].get("route_id") or "route_0"
            journey_doc = await self.get_journey_details(str(created_journey.id))
            journey_doc.planned_routes = planned_routes_dump
            journey_doc.selected_route_id = selected_id
            if not journey_doc.progress:
                journey_doc.progress = JourneyProgress(status="unavailable")
            await self.journey_repo.update(str(created_journey.id), journey_doc.model_dump())
            
        return plan_response

    async def plan_guest_journey(self, data: JourneyCreate, cancel_check: Optional[Any] = None) -> Any:
        """
        Narrowly scoped read-only route planning for unauthenticated guests.
        Does not persist journey to database, create user records, or modify private state.
        Executes full multimodal routing graph and LightGBM spatial scoring on eligible road segments.
        """
        if not data.source or not data.destination:
            from app.api.exceptions import ValidationException
            raise ValidationException("Source and destination are required.")
        return await self.coordinator.build_journey_plan_response("guest-exploration", data, cancel_check=cancel_check)

    async def initialize_journey(self, journey_id: str) -> Journey:
        """Journey Initialization: Delegates to agent to plan the journey"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state != JourneyStateEnum.CREATED:
            raise InvalidStateTransitionError("Journey must be in CREATED state to initialize.")
            
        journey.state.current_state = JourneyStateEnum.PLANNING
        await self.journey_repo.update(journey_id, journey.model_dump())
        
        # Coordinator execution is handled by build_journey_plan_response in create_journey.
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

    async def start_journey(self, journey_id: str, selected_route_id: str = None) -> Journey:
        """Journey Start"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.PLANNED, JourneyStateEnum.PAUSED]:
            raise InvalidStateTransitionError("Journey must be PLANNED or PAUSED to start.")
            
        if selected_route_id:
            journey.selected_route_id = selected_route_id
            
        if not journey.started_timestamp:
            journey.started_timestamp = datetime.utcnow()
            
        journey.state.current_state = JourneyStateEnum.ACTIVE
        await self.journey_repo.update(journey_id, journey.model_dump())
        
        journey.state.current_state = JourneyStateEnum.MONITORING
        if not journey.progress:
            journey.progress = JourneyProgress(status="unavailable")
        elif journey.progress.status == "paused":
            journey.progress.status = "on_route"

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
        if journey.progress:
            journey.progress.status = "paused"
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
        if journey.progress:
            journey.progress.status = "cancelled"
        return await self.journey_repo.update(journey_id, journey.model_dump())

    async def complete_journey(self, journey_id: str) -> Journey:
        """Journey Completion"""
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            raise InvalidStateTransitionError("Journey must be ACTIVE or MONITORING to complete.")
            
        journey.state.current_state = JourneyStateEnum.COMPLETED
        journey.completed_timestamp = datetime.utcnow()
        if journey.progress:
            journey.progress.status = "completed"
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

    async def record_telemetry(self, journey_id: str, persistence_data: dict) -> Journey:
        """
        Persists the latest valid telemetry snapshot into journey.progress.
        Only stores the latest snapshot; does NOT store continuous GPS history.
        Enforces that telemetry is only recorded for active or monitoring journeys.
        """
        journey = await self.get_journey_details(journey_id)
        if journey.state.current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            return journey

        calc = persistence_data.get("calc_result", {})
        if not journey.progress:
            journey.progress = JourneyProgress()

        total_len = calc.get("total_route_length_m", 0.0)
        dist_remaining = calc.get("distance_remaining_m", 0.0)
        dist_covered = max(0.0, total_len - dist_remaining)

        # Estimate remaining duration at standard pedestrian/transit pace (~1.3 m/s)
        updated_eta = round(dist_remaining / 1.3, 0) if dist_remaining > 0 else 0.0

        journey.progress.distance_covered = round(dist_covered, 1)
        journey.progress.distance_remaining = round(dist_remaining, 1)
        journey.progress.eta_remaining = updated_eta
        journey.progress.updated_eta = updated_eta
        journey.progress.progress_percentage = calc.get("progress_percentage", 0.0)
        journey.progress.distance_from_route = calc.get("distance_from_route_m")
        journey.progress.is_on_route = calc.get("is_on_route", True)
        journey.progress.status = calc.get("status", "on_route")
        journey.progress.accuracy = persistence_data.get("accuracy")

        lat = persistence_data.get("lat")
        lng = persistence_data.get("lng")
        if lat is not None and lng is not None:
            journey.progress.current_location = Location(type="Point", coordinates=[lng, lat])

        ts = persistence_data.get("timestamp")
        if ts:
            journey.progress.last_updated = datetime.fromtimestamp(ts)
            journey.last_telemetry_timestamp = float(ts)

        return await self.journey_repo.update(journey_id, journey.model_dump())
