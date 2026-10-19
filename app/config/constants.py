from enum import Enum

class JourneyStatus(str, Enum):
    SAFE = "SAFE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ReportType(str, Enum):
    POOR_LIGHTING = "Poor Lighting"
    HARASSMENT = "Harassment"
    ROAD_BLOCK = "Road Block"
    ACCIDENT = "Accident"
    FLOOD = "Flood"
    CONSTRUCTION = "Construction"

class SafetyLevel(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HIGH_RISK = "HIGH_RISK"

class SystemConstants:
    DEFAULT_SEARCH_RADIUS_KM = 5.0
    NEARBY_DISTANCE_METERS = 500
    MAX_REPORTS_RETURNED = 50
    JOURNEY_UPDATE_INTERVAL_SEC = 30
