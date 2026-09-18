from typing import List
from app.models.journey import CandidateRoute, TransportMode
from app.intelligence.journey.models import JourneyContext
from app.intelligence.journey.planning.strategies import (
    BaseJourneyStrategy,
    CabStrategy,
    OwnVehicleStrategy,
    WalkingStrategy
)

class JourneyPlanner:
    """
    Coordinates the generation of CandidateRoutes dynamically mapping to TransportMode.
    Does NOT evaluate, rank, or recommend routes.
    """
    def __init__(self, routing_provider=None):
        self.routing_provider = routing_provider
        self._strategies = {
            TransportMode.CAB: CabStrategy(routing_provider=self.routing_provider),
            TransportMode.OWN_VEHICLE: OwnVehicleStrategy(routing_provider=self.routing_provider),
            TransportMode.WALK: WalkingStrategy(routing_provider=self.routing_provider),
            TransportMode.BUS: CabStrategy(routing_provider=self.routing_provider),
            TransportMode.METRO: CabStrategy(routing_provider=self.routing_provider),
            TransportMode.TRAIN: CabStrategy(routing_provider=self.routing_provider),
            TransportMode.BICYCLE: OwnVehicleStrategy(routing_provider=self.routing_provider),
            TransportMode.RIDE_SHARE: CabStrategy(routing_provider=self.routing_provider)
        }

    def generate_candidates(self, context: JourneyContext) -> List[CandidateRoute]:
        strategy: BaseJourneyStrategy = self._strategies.get(context.transport_mode)
        if not strategy:
            raise ValueError(f"No planning strategy found for mode: {context.transport_mode.value}")
            
        return strategy.generate_candidates(context)
