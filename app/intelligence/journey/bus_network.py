import datetime
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel

# =========================================================
# MTC BUS DATA MODELS (Normalized for future GTFS / OpenData)
# =========================================================
class BusStop(BaseModel):
    stop_id: str
    canonical_name: str
    aliases: List[str] = []
    latitude: float
    longitude: float
    operational_status: str = "ACTIVE"
    source: str = "UNKNOWN"
    last_updated: str

class BusRoute(BaseModel):
    route_id: str
    service_number: str
    direction: str
    stop_sequence: List[str]
    geometry: Optional[Dict[str, Any]] = None
    source: str = "UNKNOWN"

class BusTrip(BaseModel):
    trip_id: str
    route_id: str
    calendar_id: str
    stop_times: List[Dict[str, Any]] # e.g., {"stop_id": "X", "arrival_time": "08:00"}

class BusCalendar(BaseModel):
    calendar_id: str
    service_days: List[str]
    start_date: str
    end_date: str
    exceptions: List[str] = []

# =========================================================
# BUS SERVICE VALIDATION
# =========================================================
class BusValidator:
    def __init__(self):
        # MTC GTFS Data is not yet publicly verifiable or ingested into SafeShe
        self.bus_data_available = False

    def validate_bus_segment(self, start_name: str, end_name: str, service: str, req_dt: datetime.datetime) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates if a specific bus service can take a user from A to B at the requested time.
        Currently safely blocks due to lack of verified MTC infrastructure.
        """
        if not self.bus_data_available:
            return False, "INSUFFICIENT_BUS_DATA", {
                "source": "Bus Validator",
                "status": "REJECTED",
                "reason": "Verified MTC GTFS or OpenData network geometry is not yet available."
            }

        # Future Logic (When GTFS is loaded):
        # 1. Resolve stop_ids from start_name and end_name
        # 2. Check if service exists
        # 3. Check if service stops at start and end sequentially
        # 4. Check if calendar covers req_dt
        # 5. Extract specific geometry
        # 6. Return True, "VALID", {...}
        
        return False, "NO_VERIFIED_BUS_SERVICE", {}

global_bus_validator = BusValidator()
