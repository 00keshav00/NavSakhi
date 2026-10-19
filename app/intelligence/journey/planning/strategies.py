from typing import List, Optional
from abc import ABC, abstractmethod
from app.models.journey import TransportMode, CandidateRoute, JourneySegment
from app.intelligence.journey.models import JourneyContext
from app.intelligence.journey.planning.multimodal import MultiModalPlanner

class BaseJourneyStrategy(ABC):
    def __init__(self, routing_provider=None):
        self.routing_provider = routing_provider

    @abstractmethod
    def generate_candidates(self, context: JourneyContext) -> List[CandidateRoute]:
        pass

class CabStrategy(BaseJourneyStrategy):
    def generate_candidates(self, context: JourneyContext) -> List[CandidateRoute]:
        # Stub: Cab returns a single high-quality path directly
        route = CandidateRoute(
            route_identifier="cab_route_1",
            distance=10000.0,
            duration=1200.0,
            recommendation_status="CANDIDATE"
        )
        return [route]

class OwnVehicleStrategy(BaseJourneyStrategy):
    def generate_candidates(self, context: JourneyContext) -> List[CandidateRoute]:
        # Stub: Generate multiple candidate routes
        return [
            CandidateRoute(route_identifier="veh_1", distance=5000.0, duration=600.0, recommendation_status="CANDIDATE"),
            CandidateRoute(route_identifier="veh_2", distance=6000.0, duration=500.0, recommendation_status="CANDIDATE")
        ]

class WalkingStrategy(BaseJourneyStrategy):
    def __init__(self, routing_provider=None):
        super().__init__(routing_provider)
        self.multimodal = MultiModalPlanner()

    def generate_candidates(self, context: JourneyContext) -> List[CandidateRoute]:
        # Stub: Walking strategy can return a single candidate route which contains multi-modal segments
        # or it can return multiple walking paths.
        route = CandidateRoute(
            route_identifier="walk_1",
            distance=1000.0,
            duration=900.0,
            recommendation_status="CANDIDATE"
        )
        return [route]
