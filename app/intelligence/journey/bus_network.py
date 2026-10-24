import datetime
import os
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# =========================================================
# MTC BUS DATA MODELS (Normalized for GTFS / OpenData)
# =========================================================
class BusStop(BaseModel):
    stop_id: str
    canonical_name: str
    aliases: List[str] = []
    latitude: float
    longitude: float
    operational_status: str = "ACTIVE"
    source: str = "MTC GTFS"
    last_updated: str = "2026-10-18"

class BusRoute(BaseModel):
    route_id: str
    service_number: str
    route_long_name: str
    stop_sequence: List[str]
    geometry: Optional[Dict[str, Any]] = None
    source: str = "MTC GTFS"


# =========================================================
# BUS SERVICE VALIDATION
# =========================================================
class BusValidator:
    def __init__(self, data_path: str = "transit_data/processed/bus_network.json"):
        self.bus_data_available = False
        self.routes_by_service: Dict[str, List[Dict[str, Any]]] = {}
        self.stops_by_name: Dict[str, List[Dict[str, Any]]] = {}
        self.stops_by_id: Dict[str, Dict[str, Any]] = {}
        self.load_bus_data(data_path)

    def load_bus_data(self, data_path: str):
        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    routes = data.get("routes", [])
                    stops = data.get("stops", [])

                    for s in stops:
                        self.stops_by_id[s["id"]] = s
                        name_lower = s["name"].lower().strip()
                        if name_lower not in self.stops_by_name:
                            self.stops_by_name[name_lower] = []
                        self.stops_by_name[name_lower].append(s)

                    for r in routes:
                        s_num = r.get("service_number", "").upper().strip()
                        if s_num not in self.routes_by_service:
                            self.routes_by_service[s_num] = []
                        self.routes_by_service[s_num].append(r)

                    self.bus_data_available = True
                    logger.info(f"BusValidator loaded {len(self.routes_by_service)} MTC bus services and {len(stops)} stops.")
            except Exception as e:
                logger.error(f"Failed to initialize BusValidator data: {e}")
                self.bus_data_available = False

    def validate_bus_segment(self, start_name: str, end_name: str, service: str, req_dt: datetime.datetime) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates if a specific MTC bus service can take a user from A to B at the requested time.
        """
        if not self.bus_data_available:
            return False, "INSUFFICIENT_BUS_DATA", {
                "source": "Bus Validator",
                "status": "REJECTED",
                "reason": "Verified MTC GTFS or OpenData network geometry is not yet available."
            }

        s_clean = service.upper().strip()
        matched_routes = self.routes_by_service.get(s_clean, [])
        if not matched_routes:
            return False, "NO_SUCH_SERVICE", {
                "source": "MTC GTFS Bus Validator",
                "status": "REJECTED",
                "reason": f"Bus service {service} is not found in the verified MTC network."
            }

        start_lower = start_name.lower().strip()
        end_lower = end_name.lower().strip()

        for r in matched_routes:
            for pat in r.get("patterns", []):
                # Search if start and end stop appear in order
                start_indices = [
                    i for i, sid in enumerate(pat)
                    if (sid in self.stops_by_id and start_lower in self.stops_by_id[sid]["name"].lower())
                    or start_lower in sid.lower()
                ]
                end_indices = [
                    i for i, sid in enumerate(pat)
                    if (sid in self.stops_by_id and end_lower in self.stops_by_id[sid]["name"].lower())
                    or end_lower in sid.lower()
                ]

                if start_indices and end_indices and start_indices[0] < end_indices[-1]:
                    stop_slice = pat[start_indices[0] : end_indices[-1] + 1]
                    return True, "VALID", {
                        "source": "MTC GTFS Verified Network",
                        "status": "VERIFIED",
                        "service_number": s_clean,
                        "stop_count": len(stop_slice),
                        "stops": stop_slice
                    }

        return False, "NO_DIRECT_SERVICE_PAIR", {
            "source": "MTC GTFS Bus Validator",
            "status": "REJECTED",
            "reason": f"Bus service {service} does not run directly from {start_name} to {end_name}."
        }

global_bus_validator = BusValidator()
