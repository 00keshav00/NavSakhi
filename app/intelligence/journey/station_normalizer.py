import os
import csv
import io
import json
import math
import zipfile
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def clean_station_name(name: str) -> str:
    n = name.strip()
    n = n.replace("PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO", "Chennai Central Metro")
    n = n.replace("PURATCHI THALAIVI DR. J. JAYALALITHAA CMBT METRO", "CMBT Metro")
    n = n.replace("CHENNAI CENTRAL SUBURBAN", "Chennai Central Suburban")
    n = n.title()
    for word in ["Metro Station", "Railway Station", "Jn.", "Jn"]:
        n = n.replace(word, "").strip()
    return n.strip()

class StationNormalizer:
    """
    Generic GTFS station and stop normalization engine.
    Resolves platforms, entrances, and stop-sequences into canonical logical station entities.
    Preserves parent-child relationships, coordinates, platforms, and operational details.
    """

    def __init__(self):
        self.diagnostics = {
            "suburban": {},
            "metro": {},
            "summary": {}
        }

    def normalize_gtfs_rail(
        self,
        zip_path: str,
        mode_prefix: str,
        mode_type: str,
        bbox: Optional[Tuple[float, float, float, float]] = (12.4, 79.6, 13.6, 80.4)
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Normalizes GTFS stops into canonical logical station entities.
        Returns (data_dict, diag_dict).
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"GTFS archive not found at {zip_path}")

        raw_stops = []
        with zipfile.ZipFile(zip_path, "r") as z:
            with z.open("stops.txt") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                for r in reader:
                    raw_stops.append(r)

            # 1. Identify canonical parent stations (location_type == '1' or designated stations)
            parents = {}
            for r in raw_stops:
                sid = r["stop_id"].strip()
                lt = r.get("location_type", "0").strip()
                lat = float(r["stop_lat"])
                lon = float(r["stop_lon"])

                # Spatial filter if bbox specified
                if bbox:
                    min_lat, min_lon, max_lat, max_lon = bbox
                    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                        continue

                if lt == "1":
                    parents[sid] = r

            # If no stops had location_type == '1', infer parents from base stop_id (e.g. CMRL base IDs)
            if not parents:
                for r in raw_stops:
                    sid = r["stop_id"].strip()
                    base_id = sid.split("_P_")[0].split("_")[0]
                    lat = float(r["stop_lat"])
                    lon = float(r["stop_lon"])
                    if bbox:
                        min_lat, min_lon, max_lat, max_lon = bbox
                        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                            continue
                    if base_id not in parents:
                        parents[base_id] = r

            # 2. Build logical station dictionary
            logical_stations = {}
            for pid, r in parents.items():
                name = r["stop_name"].strip()
                lat = float(r["stop_lat"])
                lon = float(r["stop_lon"])
                
                # Determine subtype
                st_type = mode_type
                if mode_type == "Suburban":
                    mrts_codes = ["VLCY", "TRMN", "TYMR", "KTPM", "PRGD", "GWYR", "MNDY", "MKMY", "MLHS", "CHTS", "MCPK", "MTCN", "MSF"]
                    if "mrts" in name.lower() or pid in mrts_codes:
                        st_type = "MRTS"

                logical_stations[pid] = {
                    "id": f"{mode_prefix}_{pid}",
                    "stop_id": pid,
                    "code": r.get("stop_code", pid),
                    "name": clean_station_name(name),
                    "raw_name": name,
                    "lat": lat,
                    "lon": lon,
                    "type": st_type,
                    "platforms": [],
                    "entrances": [],
                    "child_stop_ids": []
                }

            # 3. Associate platforms and entrances
            child_to_parent = {}
            unresolved_children = []
            platform_count = 0
            entrance_count = 0

            for r in raw_stops:
                sid = r["stop_id"].strip()
                lt = r.get("location_type", "0").strip()
                lat = float(r["stop_lat"])
                lon = float(r["stop_lon"])

                if bbox:
                    min_lat, min_lon, max_lat, max_lon = bbox
                    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                        continue

                if sid in logical_stations and lt == "1":
                    # This is the parent centroid itself
                    child_to_parent[sid] = sid
                    continue

                # Find parent
                pid = r.get("parent_station", "").strip()
                if not pid:
                    pid = sid.split("_P_")[0].split("_")[0]

                if pid in logical_stations:
                    child_to_parent[sid] = pid
                    logical_stations[pid]["child_stop_ids"].append(sid)
                    
                    is_platform = (lt == "0" or "_P_" in sid or r.get("platform_code"))
                    if is_platform:
                        platform_count += 1
                        logical_stations[pid]["platforms"].append({
                            "stop_id": sid,
                            "platform_code": r.get("platform_code", ""),
                            "lat": lat,
                            "lon": lon
                        })
                    else:
                        entrance_count += 1
                        logical_stations[pid]["entrances"].append({
                            "stop_id": sid,
                            "name": r.get("stop_name", "").strip(),
                            "lat": lat,
                            "lon": lon
                        })
                else:
                    unresolved_children.append(sid)

            # 4. Route and Stop Sequences
            trip_routes = {}
            if "trips.txt" in z.namelist():
                with z.open("trips.txt") as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                    for r in reader:
                        trip_routes[r["trip_id"].strip()] = {
                            "route_id": r["route_id"].strip(),
                            "headsign": r.get("trip_headsign", "").strip(),
                            "shape_id": r.get("shape_id", "").strip()
                        }

            trip_sequences = {}
            with z.open("stop_times.txt") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                for r in reader:
                    tid = r["trip_id"].strip()
                    sid_raw = r["stop_id"].strip()
                    seq = int(r["stop_sequence"])

                    # Resolve to logical parent
                    pid = child_to_parent.get(sid_raw)
                    if not pid:
                        base = sid_raw.split("_P_")[0].split("_")[0]
                        pid = base if base in logical_stations else None

                    if pid and pid in logical_stations:
                        if tid not in trip_sequences:
                            trip_sequences[tid] = []
                        trip_sequences[tid].append((seq, pid))

            # Routes dictionary
            routes = {}
            if "routes.txt" in z.namelist():
                with z.open("routes.txt") as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                    for r in reader:
                        rid = r["route_id"].strip()
                        color = r.get("route_color", "3B82F6" if mode_type == "Suburban" else "8B5CF6")
                        if not color.startswith("#"):
                            color = f"#{color}"
                        routes[rid] = {
                            "id": rid,
                            "short_name": r.get("route_short_name", rid).strip(),
                            "long_name": r.get("route_long_name", "").strip(),
                            "color": color,
                            "stop_sequences": []
                        }

            duplicate_edges_removed = 0
            unique_sequences = set()

            for tid, meta in trip_routes.items():
                rid = meta["route_id"]
                if rid in routes and tid in trip_sequences:
                    sorted_stops = [item[1] for item in sorted(trip_sequences[tid], key=lambda x: x[0])]
                    # Collapse consecutive identical visits (e.g. changing platforms at same station)
                    collapsed = []
                    for st in sorted_stops:
                        if not collapsed or collapsed[-1] != st:
                            collapsed.append(st)
                    
                    if len(collapsed) >= 2:
                        seq_key = tuple(collapsed)
                        if seq_key not in unique_sequences:
                            unique_sequences.add(seq_key)
                            full_seq = [f"{mode_prefix}_{st}" for st in collapsed]
                            routes[rid]["stop_sequences"].append(full_seq)
                        else:
                            duplicate_edges_removed += 1

            # Shapes if available
            shapes = {}
            if "shapes.txt" in z.namelist():
                with z.open("shapes.txt") as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
                    for r in reader:
                        sh_id = r["shape_id"].strip()
                        pt = [float(r["shape_pt_lon"]), float(r["shape_pt_lat"])]
                        seq = int(r["shape_pt_sequence"])
                        if sh_id not in shapes:
                            shapes[sh_id] = []
                        shapes[sh_id].append((seq, pt))
                for sh_id in shapes:
                    shapes[sh_id] = [item[1] for item in sorted(shapes[sh_id], key=lambda x: x[0])]

            data = {
                "mode": mode_type,
                "station_count": len(logical_stations),
                "stations": list(logical_stations.values()),
                "routes": [r for r in routes.values() if r["stop_sequences"]],
                "shapes": shapes
            }

            diag = {
                "feed": os.path.basename(zip_path),
                "mode": mode_type,
                "raw_stop_records": len(raw_stops),
                "logical_stations_count": len(logical_stations),
                "platform_records_associated": platform_count,
                "entrance_records_associated": entrance_count,
                "total_children_resolved": len(child_to_parent),
                "unresolved_records": len(unresolved_children),
                "unresolved_sample": unresolved_children[:5],
                "active_routes_count": len(data["routes"]),
                "service_sequences_count": len(unique_sequences),
                "duplicate_sequences_removed": duplicate_edges_removed
            }

            return data, diag

station_normalizer = StationNormalizer()
