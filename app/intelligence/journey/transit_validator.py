import json
import logging
import difflib
from app.intelligence.journey.transit_graph import global_transit_graph
from app.intelligence.journey.schedule_engine import global_schedule_engine
from app.intelligence.journey.bus_network import global_bus_validator
import datetime
import datetime
from typing import List, Dict, Any, Optional

try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

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
        self.aliases = data.get("aliases", [])
        self.exits = data.get("exits", [])
        
    def get_best_entry(self):
        if self.entrances and len(self.entrances) > 0:
            return self.entrances[0], "station_entry"
        return [self.latitude, self.longitude], "station_centroid"
        
    def get_best_exit(self):
        if self.exits and len(self.exits) > 0:
            return self.exits[0], "station_exit"
        return [self.latitude, self.longitude], "station_centroid"

        
        self.aliases = [self.name.lower()]
        if "metro" in self.name.lower():
            self.aliases.append(self.name.lower().replace("metro", "").strip())
        if "railway" in self.name.lower():
            self.aliases.append(self.name.lower().replace("railway station", "").strip())
            
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
            # Fallback linear scan
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


# =========================================================
# TRANSFER THRESHOLD CONFIGURATION
# =========================================================
# TRANSFER_WALK_THRESHOLD_M: If a transfer distance exceeds this (100m),
# we explicitly inject a 'walk' segment into the route to represent
# the physical act of walking between platforms/stations.
TRANSFER_WALK_THRESHOLD_M = 100

# TRANSFER_MAX_DISTANCE_M: The absolute maximum allowable distance (2000m)
# for a transfer. If exceeded, the route is rejected entirely as it is
# physically impractical to walk between these transit nodes as a single
# journey transfer step.
TRANSFER_MAX_DISTANCE_M = 2000
# =========================================================

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
        segments = []
        
        diagnostics.append(f"[TRANSIT] Gemini proposed: {strategy.get('strategy_name')}")
        
        for step in strategy.get("steps", []):
            mode = step.get("mode", "").lower()
            
            # Normalize Gemini hallucinated mode strings
            if "suburban" in mode or "local train" in mode: mode = "suburban"
            elif "metro" in mode: mode = "metro"
            elif "mrts" in mode: mode = "mrts"
            elif "bus" in mode: mode = "bus"
            elif "train" in mode: mode = "train"
            
            if mode in ["metro", "suburban", "mrts", "bus", "train"]:
                entry_name = step.get("entry")
                exit_name = step.get("exit")
                
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
                diagnostics.append(f"[RESOLVE] '{entry_name}' -> verified {entry_node.name} ({entry_node.type})")
                diagnostics.append(f"[RESOLVE] '{exit_name}' -> verified {exit_node.name} ({exit_node.type})")
                
                avail_entry = self.check_service_availability(entry_node, req_time)
                if not avail_entry["available"]:
                    diagnostics.append(f"[SERVICE] {entry_node.name} operational={avail_entry['available']}")
                    is_valid = False
                    rejection_reason = avail_entry.get("reason")
                    break
                    
                geom_coords = None
                geom_dist = 0
                geom_status = "UNAVAILABLE"
                
                # 1. Check Schedule Engine
                req_dt = None
                if req_time:
                    try:
                        req_dt = datetime.datetime.fromisoformat(req_time.replace("Z", "+00:00"))
                    except:
                        req_dt = datetime.datetime.now()
                else:
                    req_dt = datetime.datetime.now()
                    
                avail_status, avail_meta = global_schedule_engine.get_service_availability(mode, f"{entry_name} to {exit_name}", req_dt)
                
                if avail_status == "UNAVAILABLE":
                    diagnostics.append(f"[{mode.upper()}] Service unavailable at requested time ({req_dt.time()}).")
                    is_valid = False
                    rejection_reason = "SERVICE_UNAVAILABLE_AT_REQUESTED_TIME"
                    break
                    
                
                # Extract precise coordinates
                entry_coords, entry_precision = entry_node.get_best_entry()
                exit_coords, exit_precision = exit_node.get_best_exit()
                
                # 2. Build Transit Segment Geometry
                if mode in ["metro", "suburban", "mrts", "train", "suburban_rail"] and global_transit_graph:
                    geom_coords, geom_dist, geom_status = global_transit_graph.build_transit_segment(
                        mode, entry_coords[0], entry_coords[1], exit_coords[0], exit_coords[1]
                    )
                elif mode == "bus":
                    bus_valid, bus_reason, bus_meta = global_bus_validator.validate_bus_segment(entry_name, exit_name, "any", req_dt)
                    if not bus_valid:
                        diagnostics.append(f"[BUS] Rejected: {bus_reason}")
                        is_valid = False
                        rejection_reason = bus_reason
                        geom_status = bus_reason
                        break
                
                if geom_status == "NO_NETWORK_CONNECTION":
                    diagnostics.append(f"[{mode.upper()}] No network connection found in graph.")
                    is_valid = False
                    rejection_reason = "NO_NETWORK_CONNECTION"
                    break
                    
                geometry_complete = geom_coords is not None
                segment_geom = {"type": "LineString", "coordinates": geom_coords} if geometry_complete else None
                
                # Transfer Penalty Validation
                if len(segments) > 0:
                    prev_end = segments[-1].get("end_coordinates")
                    if prev_end and isinstance(prev_end, list) and len(prev_end) == 2:
                        prev_end_lat, prev_end_lon = prev_end
                        from app.intelligence.journey.deduplication import haversine
                        transfer_dist_m = haversine(prev_end_lat, prev_end_lon, entry_coords[0], entry_coords[1]) * 1000
                        if transfer_dist_m > TRANSFER_MAX_DISTANCE_M:
                            diagnostics.append(f"[{mode.upper()}] Transfer distance too high ({int(transfer_dist_m)}m).")
                            is_valid = False
                            rejection_reason = "EXCESSIVE_TRANSFER_DISTANCE"
                            break
                        elif transfer_dist_m > TRANSFER_WALK_THRESHOLD_M:
                            segments.append({
                                "mode": "walk",
                                "start_name": "Transfer",
                                "end_name": entry_node.name,
                                "waiting_time_s": 0,
                                "start_coordinates": [prev_end_lat, prev_end_lon],
                                "end_coordinates": entry_coords,
                                "distance_m": transfer_dist_m,
                                "duration_s": transfer_dist_m / 1.4,
                                "geometry_complete": False
                            })
                
                segments.append({
                    "mode": mode,
                    "start_name": entry_node.name,
                    "end_name": exit_node.name,
                    "waiting_time_s": avail_meta.get("waiting_time", 0) * 60,
                    "start_coordinates": entry_coords,
                    "end_coordinates": exit_coords,
                    "distance_m": geom_dist,
                    "duration_s": geom_dist / 11.0, # ~40km/h
                    "geometry": segment_geom,
                    "geometry_source": "VERIFIED_TRANSIT_NETWORK" if geometry_complete else "NONE",
                    "validation_status": "VALID" if geometry_complete else "MISSING_GEOMETRY",
                    "geometry_complete": geometry_complete,
                    "precision_level": f"start:{entry_precision}_end:{exit_precision}"
                })
                
            elif mode in ["auto", "cab", "walk"]:
                segments.append({
                    "mode": mode,
                    "start_name": step.get("start_name", "Point"),
                    "end_name": step.get("end_name", "Point"),
                    "validation_status": "PENDING_GEOMETRY",
                    "geometry_complete": False
                })
        
        status = "VALID" if is_valid else "REJECTED"
        if status == "VALID":
            diagnostics.append("[VALIDATOR] strategy VALID (Pending Geometry)")
        else:
            diagnostics.append(f"[VALIDATOR] strategy REJECTED - {rejection_reason}")
            
        return {
            "strategy_name": strategy.get("strategy_name", "Unknown"),
            "validation": {
                "status": status,
                "rejection_reason": rejection_reason,
                "diagnostics": diagnostics
            },
            "segments": segments,
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
