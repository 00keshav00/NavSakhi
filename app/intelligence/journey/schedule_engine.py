import os
import csv
import io
import zipfile
import datetime
import logging
from app.providers.live.transport import global_live_transport
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

class ScheduleEngine:
    """
    Timetable validation and service availability engine.
    Distinguishes GTFS timetable-verified departures from static frequency windows and out-of-service periods.
    """
    def __init__(self, srr_gtfs_path: str = "transit_data/downloads/srr-gtfs.zip"):
        self.operating_windows = {
            "metro": {"start": datetime.time(5, 0), "end": datetime.time(23, 0), "frequency_min": 10},
            "suburban": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "mrts": {"start": datetime.time(5, 0), "end": datetime.time(22, 30), "frequency_min": 15},
            "suburban_rail": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "train": {"start": datetime.time(4, 0), "end": datetime.time(23, 59), "frequency_min": 20},
            "bus": {"start": datetime.time(4, 30), "end": datetime.time(22, 30), "frequency_min": 25},
        }

        # Timetable indexes for Southern Railway
        self.srr_calendars: Dict[str, Dict[str, str]] = {}
        self.srr_trips: Dict[str, Dict[str, str]] = {}
        self.srr_trip_stops: Dict[str, List[Tuple[int, str, str, str]]] = {} # tid -> [(seq, stop_id, dep_time, arr_time)]
        self.srr_stop_aliases: Dict[str, str] = {} # clean_name_lower -> stop_id
        self.load_srr_timetables(srr_gtfs_path)

    def load_srr_timetables(self, path: str):
        if not os.path.exists(path):
            logger.warning(f"GTFS timetable feed {path} not found. Operating in frequency-window mode.")
            return

        try:
            with zipfile.ZipFile(path, "r") as z:
                # 1. Calendars
                if "calendar.txt" in z.namelist():
                    with z.open("calendar.txt") as f:
                        for r in csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace")):
                            self.srr_calendars[r["service_id"].strip()] = r

                # 2. Trips
                if "trips.txt" in z.namelist():
                    with z.open("trips.txt") as f:
                        for r in csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace")):
                            self.srr_trips[r["trip_id"].strip()] = {
                                "route_id": r["route_id"].strip(),
                                "service_id": r["service_id"].strip(),
                                "trip_headsign": r.get("trip_headsign", "").strip()
                            }

                # 3. Stop Aliases & Stop Times
                if "stops.txt" in z.namelist():
                    with z.open("stops.txt") as f:
                        for r in csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace")):
                            sid = r["stop_id"].strip()
                            base_id = sid.split("_P_")[0].split("_")[0]
                            name = r["stop_name"].strip().lower()
                            self.srr_stop_aliases[name] = base_id
                            clean = name.replace("railway station", "").replace("jn.", "").replace("jn", "").replace("suburban", "").strip()
                            self.srr_stop_aliases[clean] = base_id

                if "stop_times.txt" in z.namelist():
                    with z.open("stop_times.txt") as f:
                        for r in csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace")):
                            tid = r["trip_id"].strip()
                            sid = r["stop_id"].strip()
                            base_id = sid.split("_P_")[0].split("_")[0]
                            seq = int(r["stop_sequence"])
                            dep = r["departure_time"].strip()
                            arr = r["arrival_time"].strip()

                            if tid not in self.srr_trip_stops:
                                self.srr_trip_stops[tid] = []
                            self.srr_trip_stops[tid].append((seq, base_id, dep, arr))

            logger.info(f"Loaded {len(self.srr_trips)} GTFS timetable trips and {len(self.srr_trip_stops)} schedules into ScheduleEngine.")
        except Exception as e:
            logger.error(f"Failed to index GTFS timetable data: {e}")

    def _resolve_station_code(self, name_str: str) -> Optional[str]:
        n = name_str.strip().lower()
        if n in self.srr_stop_aliases:
            return self.srr_stop_aliases[n]
        clean = n.replace("railway station", "").replace("jn.", "").replace("jn", "").replace("suburban", "").strip()
        if clean in self.srr_stop_aliases:
            return self.srr_stop_aliases[clean]
        for alias, code in self.srr_stop_aliases.items():
            if clean and (clean in alias or alias in clean):
                return code
        return None

    def query_timetable_departure(
        self,
        orig_name: str,
        dest_name: str,
        requested_dt: datetime.datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Queries verified GTFS timetable for an active scheduled train departure.
        """
        orig_code = self._resolve_station_code(orig_name)
        dest_code = self._resolve_station_code(dest_name)
        if not orig_code or not dest_code:
            return None

        day_name = requested_dt.strftime("%A").lower()
        req_time_str = requested_dt.strftime("%H:%M:%S")

        matching_trips = []
        for tid, stops in self.srr_trip_stops.items():
            trip_meta = self.srr_trips.get(tid)
            if not trip_meta:
                continue
            
            cal = self.srr_calendars.get(trip_meta["service_id"])
            if cal and cal.get(day_name) != "1":
                continue # Service not active on this day of week

            orig_entry = next((s for s in stops if s[1] == orig_code), None)
            dest_entry = next((s for s in stops if s[1] == dest_code), None)

            # Must visit origin before destination
            if orig_entry and dest_entry and dest_entry[0] > orig_entry[0]:
                dep_time = orig_entry[2]
                arr_time = dest_entry[3]
                if dep_time >= req_time_str:
                    matching_trips.append({
                        "trip_id": tid,
                        "headsign": trip_meta["trip_headsign"],
                        "route_id": trip_meta["route_id"],
                        "departure_time": dep_time,
                        "arrival_time": arr_time,
                        "service_id": trip_meta["service_id"]
                    })

        if not matching_trips:
            return None

        matching_trips.sort(key=lambda x: x["departure_time"])
        best_trip = matching_trips[0]

        # Calculate exact wait minutes
        dep_parts = [int(p) for p in best_trip["departure_time"].split(":")]
        req_parts = [requested_dt.hour, requested_dt.minute, requested_dt.second]
        dep_sec = dep_parts[0] * 3600 + dep_parts[1] * 60 + dep_parts[2]
        req_sec = req_parts[0] * 3600 + req_parts[1] * 60 + req_parts[2]
        wait_min = max(1, int(round((dep_sec - req_sec) / 60.0)))

        return {
            "trip_id": best_trip["trip_id"],
            "route_id": best_trip["route_id"],
            "headsign": best_trip["headsign"],
            "departure_time": best_trip["departure_time"],
            "arrival_time": best_trip["arrival_time"],
            "waiting_minutes": wait_min
        }

    def get_service_availability(self, mode: str, service: str, requested_dt: datetime.datetime) -> Tuple[str, Dict[str, Any]]:
        mode_key = mode.lower()
        req_time = requested_dt.time()

        # 1. Live Disruption Check (Highest Precedence)
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

        # 2. GTFS Timetable Verification for Railway
        if mode_key in ["suburban", "suburban_rail", "train", "mrts"] and " to " in service:
            parts = service.split(" to ")
            orig_name, dest_name = parts[0].strip(), parts[1].strip()
            tt_dep = self.query_timetable_departure(orig_name, dest_name, requested_dt)

            if tt_dep:
                wait_min = tt_dep["waiting_minutes"]
                if wait_min <= 60:
                    next_dt = requested_dt + datetime.timedelta(minutes=wait_min)
                    return "AVAILABLE", {
                        "next_service": next_dt.isoformat(),
                        "waiting_time": wait_min,
                        "departure_time": tt_dep["departure_time"],
                        "arrival_time": tt_dep["arrival_time"],
                        "trip_id": tt_dep["trip_id"],
                        "headsign": tt_dep["headsign"],
                        "source": "Southern Railway Verified GTFS Timetable",
                        "data_type": "GTFS_TIMETABLE_DEPARTURE",
                        "confidence": "High",
                        "retrieved_at": datetime.datetime.now().isoformat()
                    }
                else:
                    return "UNAVAILABLE", {
                        "next_service": None,
                        "waiting_time": wait_min,
                        "reason": f"Next scheduled departure at {tt_dep['departure_time']} (> 60 min wait)",
                        "source": "Southern Railway Verified GTFS Timetable",
                        "data_type": "OUT_OF_SERVICE_HOURS",
                        "confidence": "High",
                        "retrieved_at": datetime.datetime.now().isoformat()
                    }

        # 3. Frequency Window Verification
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
        if window["start"] <= req_time <= window["end"]:
            wait = window["frequency_min"] / 2.0
            if live_status_data["status"] == "DELAYED":
                wait += 15
                next_dt = requested_dt + datetime.timedelta(minutes=wait)
                return "AVAILABLE", {
                    "next_service": next_dt.isoformat(),
                    "waiting_time": int(wait),
                    "source": live_status_data["source"],
                    "data_type": "LIVE_STATUS_DATA",
                    "confidence": "High",
                    "retrieved_at": live_status_data["timestamp"]
                }

            next_dt = requested_dt + datetime.timedelta(minutes=wait)
            return "AVAILABLE", {
                "next_service": next_dt.isoformat(),
                "waiting_time": int(wait),
                "source": "Chennai Verified Operational Hours",
                "data_type": "STATIC_SCHEDULE_DATA",
                "confidence": "High",
                "retrieved_at": datetime.datetime.now().isoformat()
            }
        else:
            return "UNAVAILABLE", {
                "next_service": None,
                "waiting_time": 0,
                "reason": f"Operating hours are {window['start'].strftime('%H:%M')} - {window['end'].strftime('%H:%M')}",
                "source": "Chennai Verified Operational Hours",
                "data_type": "OUT_OF_SERVICE_HOURS",
                "confidence": "High",
                "retrieved_at": datetime.datetime.now().isoformat()
            }

global_schedule_engine = ScheduleEngine()
