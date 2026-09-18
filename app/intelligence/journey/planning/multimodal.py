from typing import List
from app.models.journey import JourneySegment, TransportMode, Location

class MultiModalPlanner:
    """
    Sub-component of Journey Planning responsible for generating JourneySegment arrays.
    """
    def plan_segments(self, source: Location, destination: Location) -> List[JourneySegment]:
        # Stub: Return a list of segments using the expanded model
        seg1 = JourneySegment(
            segment_identifier="seg_walk_1",
            transport_mode=TransportMode.WALK,
            start_location=source,
            end_location=Location(coordinates=[0.5, 0.5]),
            distance=500.0,
            duration=300.0,
            progress=0.0,
            status="PENDING",
            safety_information={"risk_level": "LOW"}
        )
        
        seg2 = JourneySegment(
            segment_identifier="seg_bus_1",
            transport_mode=TransportMode.BUS,
            start_location=Location(coordinates=[0.5, 0.5]),
            end_location=destination,
            distance=5000.0,
            duration=600.0,
            progress=0.0,
            status="PENDING",
            safety_information={"risk_level": "LOW"}
        )
        
        return [seg1, seg2]
