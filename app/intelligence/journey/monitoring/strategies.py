from typing import Dict, Any
from abc import ABC, abstractmethod
from app.intelligence.journey.models import MonitoringResult, JourneyContext

class BaseMonitoringStrategy(ABC):
    @abstractmethod
    def execute(self, context: JourneyContext) -> MonitoringResult:
        pass

class CabMonitoringStrategy(BaseMonitoringStrategy):
    def execute(self, context: JourneyContext) -> MonitoringResult:
        # Stub: Implement Safety Monitoring, Unsafe Area, Weather Alert, Emergency
        # Cab NEVER requests rerouting
        return MonitoringResult(
            reroute_required=False,
            monitoring_status="cab_monitoring_executed"
        )

class VehicleMonitoringStrategy(BaseMonitoringStrategy):
    def execute(self, context: JourneyContext) -> MonitoringResult:
        # Stub: Implement Safety Monitoring, Route Hazards, Traffic, Unsafe Route
        # Vehicle CAN request rerouting
        return MonitoringResult(
            reroute_required=False, # Mock logic
            monitoring_status="vehicle_monitoring_executed"
        )

class WalkingMonitoringStrategy(BaseMonitoringStrategy):
    def execute(self, context: JourneyContext) -> MonitoringResult:
        # Stub: Implement Walking Safety, Segment Progress, Segment Transitions
        return MonitoringResult(
            reroute_required=False,
            monitoring_status="walking_monitoring_executed"
        )
