from typing import Dict, Any, Optional
from app.intelligence.journey.models import MonitoringResult, JourneyContext
from app.intelligence.journey.monitoring.strategies import (
    BaseMonitoringStrategy,
    CabMonitoringStrategy,
    VehicleMonitoringStrategy,
    WalkingMonitoringStrategy
)
from app.models.journey import JourneyStateEnum, TransportMode

class JourneyMonitor:
    """
    Coordinates transport-specific monitoring rules using the Strategy Pattern.
    Executes strictly within the Agentic Layer.
    """
    def __init__(self):
        self._strategies: Dict[TransportMode, BaseMonitoringStrategy] = {
            TransportMode.CAB: CabMonitoringStrategy(),
            TransportMode.OWN_VEHICLE: VehicleMonitoringStrategy(),
            TransportMode.WALK: WalkingMonitoringStrategy(),
            # Stub mappings for future modes
            TransportMode.BUS: CabMonitoringStrategy(), 
            TransportMode.METRO: CabMonitoringStrategy(),
            TransportMode.TRAIN: CabMonitoringStrategy(),
            TransportMode.BICYCLE: VehicleMonitoringStrategy(),
            TransportMode.RIDE_SHARE: CabMonitoringStrategy(),
        }

    def monitor(self, context: JourneyContext) -> MonitoringResult:
        # Validate Journey State
        if context.state in [JourneyStateEnum.COMPLETED, JourneyStateEnum.FAILED, JourneyStateEnum.CANCELLED]:
            return MonitoringResult(
                monitoring_status="monitoring_rejected",
                metadata={"reason": f"Journey is in terminal state: {context.state.value}"}
            )
            
        if context.state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING, JourneyStateEnum.REROUTING]:
            raise ValueError(f"Cannot monitor journey in state: {context.state.value}")

        # Select Strategy
        strategy = self._strategies.get(context.transport_mode)
        if not strategy:
            raise ValueError(f"No monitoring strategy found for mode: {context.transport_mode.value}")

        # Execute Monitoring
        return strategy.execute(context=context)
