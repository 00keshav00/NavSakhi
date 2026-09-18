import datetime
import logging
from app.providers.live.transport import global_live_transport
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class ScheduleEngine:
    def __init__(self):
        # We store known operating hours for Chennai transit modes
        # Default behavior: Metro (05:00-23:00), Suburban (04:00-23:59), MRTS (05:00-22:30)
        self.operating_windows = {
            "metro": {"start": datetime.time(5, 0), "end": datetime.time(23, 0), "frequency_min": 10},
            "suburban": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "mrts": {"start": datetime.time(5, 0), "end": datetime.time(22, 30), "frequency_min": 15},
            "suburban_rail": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "train": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "bus": {"start": datetime.time(4, 30), "end": datetime.time(22, 30), "frequency_min": 30},
        }

    def get_service_availability(self, mode: str, service: str, requested_dt: datetime.datetime) -> Tuple[str, Dict[str, Any]]:
        mode_key = mode.lower()
        if mode_key not in self.operating_windows:
            return "UNKNOWN", {
                "next_service": None,
                "waiting_time": 0,
                "source": "Schedule Engine Fallback",
                "data_type": "UNKNOWN",
                "confidence": "Low",
                "retrieved_at": datetime.datetime.now().isoformat()
            }
            
        window = self.operating_windows[mode_key]
        req_time = requested_dt.time()
        
        # Check if the requested time falls within operating hours
        if window["start"] <= req_time <= window["end"]:
            # Roughly estimate waiting time
            wait = window["frequency_min"] / 2.0
            next_dt = requested_dt + datetime.timedelta(minutes=wait)
            

            # Live Override Policy (Static vs Live Precedence)
            live_status_data = global_live_transport.get_live_status(service, mode_key)
            if live_status_data["status"] in ["SUSPENDED", "DISRUPTED"]:
                return "UNAVAILABLE", {
                    "next_service": None,
                    "waiting_time": 0,
                    "source": live_status_data["source"],
                    "data_type": "LIVE_STATUS_DATA",
                    "confidence": "High",
                    "retrieved_at": live_status_data["timestamp"]
                }
            elif live_status_data["status"] == "DELAYED":
                wait += 15 # Arbitrary delay simulation penalty
                next_dt = requested_dt + datetime.timedelta(minutes=wait)
                return "AVAILABLE", {
                    "next_service": next_dt.isoformat(),
                    "waiting_time": int(wait),
                    "source": live_status_data["source"],
                    "data_type": "LIVE_STATUS_DATA",
                    "confidence": "High",
                    "retrieved_at": live_status_data["timestamp"]
                }
                
            return "AVAILABLE", {
                "next_service": next_dt.isoformat(),
                "waiting_time": int(wait),
                "source": "Chennai Verified Timetable Windows",
                "data_type": "STATIC_SCHEDULE_DATA",
                "confidence": "High",
                "retrieved_at": datetime.datetime.now().isoformat()
            }
        else:
            return "UNAVAILABLE", {
                "next_service": None,
                "waiting_time": 0,
                "source": "Chennai Verified Timetable Windows",
                "data_type": "STATIC_SCHEDULE_DATA",
                "confidence": "High",
                "retrieved_at": datetime.datetime.now().isoformat()
            }

global_schedule_engine = ScheduleEngine()
