import json
import logging
import difflib
import math
from app.intelligence.journey.transit_graph import global_transit_graph, get_graph_for_mode
from app.intelligence.journey.schedule_engine import global_schedule_engine
from app.intelligence.journey.bus_network import global_bus_validator
import datetime
from typing import List, Dict, Any, Optional

try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def ensure_lat_lon(pt: list) -> list:
    if not pt or len(pt) < 2:
        return [12.8448, 80.1527]
    # In India, lon is ~77-81 and lat is ~10-14
    if pt[0] > pt[1]:
        return [pt[1], pt[0]]
    return [pt[0], pt[1]]

def ensure_lon_lat(pt: list) -> list:
    if not pt or len(pt) < 2:
        return [80.1527, 12.8448]
    if pt[0] < pt[1]:
        return [pt[1], pt[0]]
    return [pt[0], pt[1]]

class TransportNode:
    def __init__(self, data: dict):
        self.id = data.get("name", "")
        self.name = data.get("name", "")
        self.type = data.get("type", "UNKNOWN")
        coords = data.get("coordinates", [0, 0])
        # JSON stores [lat, lon]
        self.latitude = coords[0]
        self.longitude = coords[1]
        self.operational_status = data.get("operational_status", "UNKNOWN")
        self.entrances = data.get("entrances", [])
        self.aliases = [a.lower() for a in data.get("aliases", [])]
        self.exits = data.get("exits", [])
        
        name_lower = self.name.lower()
        if name_lower not in self.aliases:
            self.aliases.append(name_lower)
        clean_name = name_lower.replace("metro station", "").replace("railway station", "").replace("metro", "").replace("station", "").strip()
        if clean_name and clean_name not in self.aliases:
            self.aliases.append(clean_name)
        if "airport" in name_lower and "airport" not in self.aliases:
            self.aliases.append("airport")
            
    def get_best_entry(self):
        if self.entrances and len(self.entrances) > 0:
            return self.entrances[0], "station_entry"
        return [self.latitude, self.longitude], "station_centroid"
        
    def get_best_exit(self):
        if self.exits and len(self.exits) > 0:
            return self.exits[0], "station_exit"
        return [self.latitude, self.longitude], "station_centroid"
            
    def is_operational(self) -> bool:
        return self.operational_status.upper() == "OPERATIONAL"

class TransportIndex:
    def __init__(self, json_path: str):
        self.nodes: List[TransportNode] = []
        self.name_map = {}
        self.kd_tree = None
        self.load_data(json_path)
        
    def load_data(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            coords = []
            for item in raw_data:
                node = TransportNode(item)
                self.nodes.append(node)
                self.name_map[node.name.lower()] = node
                coords.append([node.latitude, node.longitude])
            
            if coords and HAS_SCIPY:
                self.kd_tree = cKDTree(coords)
                logger.info(f"Loaded {len(self.nodes)} transport nodes into spatial index.")
        except Exception as e:
            logger.error(f"Failed to load transport index: {e}")

    def find_nearest_station(self, lat: float, lon: float, mode: str = None) -> Optional[TransportNode]:
        if not self.kd_tree:
            best_node = None
            best_dist = float('inf')
            for node in self.nodes:
                if mode and mode.lower() not in node.type.lower():
                    continue
                dist = (node.latitude - lat)**2 + (node.longitude - lon)**2
                if dist < best_dist:
                    best_dist = dist
                    best_node = node
            return best_node

        dist, idx = self.kd_tree.query([lat, lon], k=20)
        
        import numpy as np
        if not isinstance(idx, (list, tuple, np.ndarray)):
            idx = [idx]
            
        for i in idx:
            if i < len(self.nodes):
                node = self.nodes[i]
                if mode is None or mode.lower() in node.type.lower():
                    return node
        return None

class EntityResolver:
    def __init__(self, index: TransportIndex):
        self.index = index
        self.all_aliases = {}
        for node in self.index.nodes:
            self.all_aliases[node.name.lower()] = node
            for alias in node.aliases:
                self.all_aliases[alias.lower()] = node
                
    def resolve(self, gemini_name: str) -> dict:
        if not gemini_name:
            return {"resolved": False, "reason": "EMPTY_NAME"}
            
        gemini_name_lower = gemini_name.lower().strip()
        gemini_name_lower = gemini_name_lower.replace('railway station', '').replace('metro station', '').replace('station', '').strip()
        
        # 1. Exact match
        if gemini_name_lower in self.all_aliases:
            node = self.all_aliases[gemini_name_lower]
            return {
                "resolved": True,
                "entity_type": node.type,
                "node": node,
                "confidence": 1.0,
                "reason": "EXACT_MATCH"
            }
            
        # 2. Fuzzy match
        matches = difflib.get_close_matches(gemini_name_lower, list(self.all_aliases.keys()), n=1, cutoff=0.55)
        if matches:
            node = self.all_aliases[matches[0]]
            return {
                "resolved": True,
                "entity_type": node.type,
                "node": node,
                "confidence": 0.8,
                "reason": "FUZZY_MATCH"
            }
            
        return {
            "resolved": False,
            "reason": "NO_VERIFIED_MATCH"
        }

TRANSFER_WALK_THRESHOLD_M = 100
TRANSFER_MAX_DISTANCE_M = 2000

class TransitValidator:
    def __init__(self, index: TransportIndex, resolver: EntityResolver):
        self.index = index
        self.resolver = resolver
        
    def check_service_availability(self, node: TransportNode, datetime_req: Any) -> dict:
        if not node.is_operational():
            return {"available": False, "reason": "SERVICE_NOT_OPERATIONAL", "source": "all_stations.json"}
            
        if datetime_req:
            hour = datetime_req.hour if isinstance(datetime_req, datetime.datetime) else 12
            if (hour >= 23 or hour <= 4) and node.type.lower() == "metro":
                return {"available": False, "reason": "SERVICE_NOT_AVAILABLE_AT_REQUESTED_TIME", "source": "schedule_heuristic"}
        
        return {"available": True, "reason": "AVAILABLE", "confidence": 0.9, "source": "all_stations.json"}

    def validate_strategy(self, strategy: dict, source_coords: list, dest_coords: list, req_time=None) -> dict:
        diagnostics = []
        is_valid = True
        rejection_reason = None
        raw_segments = []
        
        s_lat, s_lon = ensure_lat_lon(source_coords)
        d_lat, d_lon = ensure_lat_lon(dest_coords)
        trip_sl_dist_m = haversine_m(s_lat, s_lon, d_lat, d_lon)
        
        steps = strategy.get("steps", [])
        if not steps:
            return {
                "strategy_name": strategy.get("strategy_name", "Unknown"),
                "validation": {"status": "REJECTED", "rejection_reason": "NO_STEPS", "diagnostics": ["Empty steps"]},
                "segments": [],
                "geometry_complete": False
            }
            
        diagnostics.append(f"[TRANSIT] Evaluating strategy: {strategy.get('strategy_name')} ({len(steps)} steps)")
        
        for step_idx, step in enumerate(steps):
            mode = step.get("mode", "").lower().strip()
            
            # Normalize mode string
            if "suburban" in mode or "local train" in mode: mode = "suburban"
            elif "metro" in mode: mode = "metro"
            elif "mrts" in mode: mode = "mrts"
            elif "bus" in mode: mode = "bus"
            elif "train" in mode: mode = "suburban"
            elif "auto" in mode: mode = "auto"
            elif "cab" in mode: mode = "cab"
            elif "walk" in mode: mode = "walk"
            elif "two_wheeler" in mode or "bike" in mode: mode = "two_wheeler"
            else: mode = "auto"
            
            entry_name = (step.get("entry") or "").strip()
            exit_name = (step.get("exit") or "").strip()
            
            if mode in ["metro", "suburban", "mrts", "bus"]:
                if not entry_name or not exit_name:
                    diagnostics.append(f"[{mode.upper()}] Missing entry/exit stations.")
                    is_valid = False
                    rejection_reason = "INSUFFICIENT_DATA"
                    break
                    
                res_entry = self.resolver.resolve(entry_name)
                res_exit = self.resolver.resolve(exit_name)
                
                if not res_entry["resolved"]:
                    diagnostics.append(f"[RESOLVE] '{entry_name}' -> unresolved.")
                    is_valid = False
                    rejection_reason = "NO_VERIFIED_STATION"
                    break
                    
                if not res_exit["resolved"]:
                    diagnostics.append(f"[RESOLVE] '{exit_name}' -> unresolved.")
                    is_valid = False
                    rejection_reason = "NO_VERIFIED_STATION"
                    break
                    
                entry_node = res_entry["node"]
                exit_node = res_exit["node"]
                
                if entry_node.name == exit_node.name:
                    diagnostics.append(f"[{mode.upper()}] Same entry and exit station ({entry_node.name}).")
                    is_valid = False
                    rejection_reason = "IDENTICAL_STATIONS"
                    break
                    
                avail_entry = self.check_service_availability(entry_node, req_time)
                if not avail_entry["available"]:
                    diagnostics.append(f"[SERVICE] {entry_node.name} operational={avail_entry['available']}")
                    is_valid = False
                    rejection_reason = avail_entry.get("reason")
                    break
                    
                # Schedule window check in IST (UTC+5:30)
                req_dt = None
                if req_time:
                    try:
                        req_dt = datetime.datetime.fromisoformat(req_time.replace("Z", "+00:00"))
                    except:
                        req_dt = None
                        
                if req_dt is not None:
                    if req_dt.tzinfo is not None:
                        ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                        ist_dt = req_dt.astimezone(ist_offset)
                    else:
                        ist_dt = req_dt + datetime.timedelta(hours=5, minutes=30)
                else:
                    # Default daytime window (09:00 AM IST) for preview when no explicit time requested
                    now_utc = datetime.datetime.utcnow()
                    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
                    if now_ist.hour < 5 or now_ist.hour >= 23:
                        ist_dt = now_ist.replace(hour=9, minute=0, second=0)
                    else:
                        ist_dt = now_ist
                    
                avail_status, avail_meta = global_schedule_engine.get_service_availability(mode, f"{entry_name} to {exit_name}", ist_dt)
                if avail_status == "UNAVAILABLE":
                    diagnostics.append(f"[{mode.upper()}] Service unavailable at requested time ({ist_dt.time()}).")
                    is_valid = False
                    rejection_reason = "SERVICE_UNAVAILABLE_AT_REQUESTED_TIME"
                    break
                    
                entry_coords, entry_precision = entry_node.get_best_entry()
                exit_coords, exit_precision = exit_node.get_best_exit()
                
                # Progress Invariant: Transit MUST bring user closer to destination!
                dist_entry_to_dest = haversine_m(entry_coords[0], entry_coords[1], d_lat, d_lon)
                dist_exit_to_dest = haversine_m(exit_coords[0], exit_coords[1], d_lat, d_lon)
                if dist_exit_to_dest >= dist_entry_to_dest:
                    diagnostics.append(f"[{mode.upper()}] Transit leg moves away from destination (entry->dest {dist_entry_to_dest:.0f}m, exit->dest {dist_exit_to_dest:.0f}m).")
                    is_valid = False
                    rejection_reason = "BACKTRACKING_TRANSIT_ROUTE"
                    break
                    
                # Build Transit Segment Geometry using mode subgraph
                graph = get_graph_for_mode(mode)
                geom_coords = None
                geom_dist = 0
                geom_status = "UNAVAILABLE"
                
                if graph:
                    geom_coords, geom_dist, geom_status = graph.build_transit_segment(
                        mode, entry_coords[0], entry_coords[1], exit_coords[0], exit_coords[1]
                    )
                elif mode == "bus":
                    bus_valid, bus_reason, bus_meta = global_bus_validator.validate_bus_segment(entry_name, exit_name, "any", ist_dt)
                    if not bus_valid:
                        diagnostics.append(f"[BUS] Rejected: {bus_reason}")
                        is_valid = False
                        rejection_reason = bus_reason
                        break
                        
                if geom_status == "NO_NETWORK_CONNECTION" or not geom_coords:
                    diagnostics.append(f"[{mode.upper()}] No network connection between {entry_node.name} and {exit_node.name}.")
                    is_valid = False
                    rejection_reason = "NO_NETWORK_CONNECTION"
                    break
                    
                # Waiting & Transfer Times
                wait_sec = avail_meta.get("waiting_time", 8) * 60
                transit_speed_mps = 11.1 if mode == "suburban" else 9.7 # ~40km/h suburban, ~35km/h metro
                dur_s = (geom_dist / transit_speed_mps) + wait_sec + 180 # 3 min station exit
                
                raw_segments.append({
                    "mode": mode,
                    "start_name": entry_node.name,
                    "end_name": exit_node.name,
                    "waiting_time_s": wait_sec,
                    "start_coordinates": [entry_coords[0], entry_coords[1]], # [lat, lon]
                    "end_coordinates": [exit_coords[0], exit_coords[1]],     # [lat, lon]
                    "distance_m": geom_dist,
                    "duration_s": dur_s,
                    "geometry": {"type": "LineString", "coordinates": geom_coords},
                    "geometry_source": "VERIFIED_TRANSIT_NETWORK",
                    "validation_status": "VALID",
                    "geometry_complete": True,
                    "precision_level": f"start:{entry_precision}_end:{exit_precision}"
                })
                
            elif mode in ["auto", "cab", "walk", "two_wheeler"]:
                # Resolve access or egress coordinates
                if entry_name.lower() in ["source", "origin", "start", "point", ""] and step_idx == 0:
                    start_lat_lon = [s_lat, s_lon]
                    start_label = "Origin"
                else:
                    res_entry = self.resolver.resolve(entry_name)
                    if res_entry["resolved"]:
                        start_lat_lon = [res_entry["node"].latitude, res_entry["node"].longitude]
                        start_label = res_entry["node"].name
                    else:
                        start_lat_lon = [s_lat, s_lon]
                        start_label = entry_name or "Point"
                        
                if exit_name.lower() in ["destination", "dest", "end", "point", ""] and step_idx == len(steps) - 1:
                    end_lat_lon = [d_lat, d_lon]
                    end_label = "Destination"
                else:
                    res_exit = self.resolver.resolve(exit_name)
                    if res_exit["resolved"]:
                        end_lat_lon = [res_exit["node"].latitude, res_exit["node"].longitude]
                        end_label = res_exit["node"].name
                    else:
                        end_lat_lon = [d_lat, d_lon]
                        end_label = exit_name or "Point"
                        
                leg_sl_dist = haversine_m(start_lat_lon[0], start_lat_lon[1], end_lat_lon[0], end_lat_lon[1])
                
                # Check for excessive access detour
                if step_idx == 0 and len(steps) > 1:
                    # Access leg must not exceed 50% of direct trip distance or 12 km
                    if trip_sl_dist_m < 20000 and leg_sl_dist > max(6000, 0.45 * trip_sl_dist_m * 1.3):
                        diagnostics.append(f"[{mode.upper()}] Access leg to {end_label} is excessive detour ({leg_sl_dist:.0f}m vs direct {trip_sl_dist_m:.0f}m).")
                        is_valid = False
                        rejection_reason = "EXCESSIVE_STATION_ACCESS_DETOUR"
                        break
                elif step_idx == len(steps) - 1 and len(steps) > 1:
                    if trip_sl_dist_m < 20000 and leg_sl_dist > max(6000, 0.45 * trip_sl_dist_m * 1.3):
                        diagnostics.append(f"[{mode.upper()}] Egress leg from {start_label} is excessive detour ({leg_sl_dist:.0f}m vs direct {trip_sl_dist_m:.0f}m).")
                        is_valid = False
                        rejection_reason = "EXCESSIVE_STATION_EGRESS_DETOUR"
                        break
                        
                raw_segments.append({
                    "mode": mode,
                    "start_name": start_label,
                    "end_name": end_label,
                    "start_coordinates": start_lat_lon, # [lat, lon]
                    "end_coordinates": end_lat_lon,     # [lat, lon]
                    "validation_status": "PENDING_GEOMETRY",
                    "geometry_complete": False
                })

        # STRICT CONTINUITY & TRANSFER GAP CHECK
        final_segments = []
        if is_valid and raw_segments:
            for i in range(len(raw_segments)):
                final_segments.append(raw_segments[i])
                if i < len(raw_segments) - 1:
                    cur_end = raw_segments[i].get("end_coordinates")
                    next_start = raw_segments[i+1].get("start_coordinates")
                    
                    if cur_end and next_start:
                        transfer_dist = haversine_m(cur_end[0], cur_end[1], next_start[0], next_start[1])
                        if transfer_dist > TRANSFER_MAX_DISTANCE_M:
                            diagnostics.append(f"[CONTINUITY] Disconnected gap between leg {i+1} and leg {i+2} ({int(transfer_dist)}m > {TRANSFER_MAX_DISTANCE_M}m).")
                            is_valid = False
                            rejection_reason = "DISCONNECTED_NETWORK_LEGS"
                            break
                        elif transfer_dist > TRANSFER_WALK_THRESHOLD_M:
                            # Inject explicit pedestrian transfer
                            final_segments.append({
                                "mode": "walk",
                                "start_name": f"Transfer from {raw_segments[i]['end_name']}",
                                "end_name": raw_segments[i+1]['start_name'],
                                "waiting_time_s": 0,
                                "start_coordinates": cur_end,
                                "end_coordinates": next_start,
                                "distance_m": transfer_dist,
                                "duration_s": transfer_dist / 1.3,
                                "validation_status": "PENDING_GEOMETRY",
                                "geometry_complete": False
                            })
                            
        # DETOUR RATIO SANITY CHECK
        if is_valid and final_segments and len(final_segments) > 1:
            total_est_dist = sum(s.get("distance_m", haversine_m(s["start_coordinates"][0], s["start_coordinates"][1], s["end_coordinates"][0], s["end_coordinates"][1])) for s in final_segments)
            if trip_sl_dist_m > 0 and total_est_dist > trip_sl_dist_m * 2.2:
                diagnostics.append(f"[DETOUR] Total multimodal distance ({total_est_dist/1000:.1f}km) exceeds 2.2x straight-line ({trip_sl_dist_m/1000:.1f}km).")
                is_valid = False
                rejection_reason = "EXCESSIVE_TOTAL_DETOUR"

        status = "VALID" if is_valid else "REJECTED"
        if status == "VALID":
            diagnostics.append("[VALIDATOR] Strategy validated with strict geographic continuity.")
        else:
            diagnostics.append(f"[VALIDATOR] Strategy REJECTED: {rejection_reason}")
            
        return {
            "strategy_name": strategy.get("strategy_name", "Unknown"),
            "validation": {
                "status": status,
                "rejection_reason": rejection_reason,
                "diagnostics": diagnostics
            },
            "segments": final_segments if is_valid else [],
            "geometry_complete": False
        }

import os
default_index_path = os.path.join(os.getcwd(), "all_stations.json")
if os.path.exists(default_index_path):
    global_index = TransportIndex(default_index_path)
    global_resolver = EntityResolver(global_index)
    global_validator = TransitValidator(global_index, global_resolver)
else:
    global_index = None
    global_resolver = None
    global_validator = None
