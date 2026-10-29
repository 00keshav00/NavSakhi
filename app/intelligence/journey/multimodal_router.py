import os
import json
import math
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import datetime

try:
    from scipy.spatial import cKDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from app.models.journey import CandidateRoute, Location
from app.intelligence.journey.transit_graph import (
    global_metro_graph,
    global_suburban_graph,
    get_graph_for_mode
)
from app.intelligence.journey.schedule_engine import global_schedule_engine
from app.intelligence.journey.fare_engine import global_fare_engine

logger = logging.getLogger(__name__)

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class MultimodalRouter:
    """
    Data-driven, generic multimodal routing engine.
    Ingests and queries GTFS-derived networks for Metro, Suburban Rail, MRTS, and Government Bus (MTC).
    Operates generically on normalized network entities without hardcoding station names or bus routes.
    """
    def __init__(self, data_dir: str = "transit_data/processed"):
        self.data_dir = data_dir
        self.metro_stations = []
        self.metro_routes = []
        self.metro_shapes = {}
        self.metro_tree = None

        self.suburban_stations = []
        self.suburban_routes = []
        self.suburban_tree = None

        self.bus_stops = []
        self.bus_routes = []
        self.bus_stop_map = {}
        self.bus_stop_routes = {}  # stop_id -> list of route metadata dicts
        self.bus_tree = None

        self.interchanges = []
        self.load_all_networks()

    def load_all_networks(self):
        # 1. Metro Network
        metro_file = os.path.join(self.data_dir, "metro_network.json")
        if os.path.exists(metro_file):
            try:
                with open(metro_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metro_stations = data.get("stations", [])
                    self.metro_routes = data.get("routes", [])
                    self.metro_shapes = data.get("shapes", {})
                    if HAS_SCIPY and self.metro_stations:
                        coords = [[s["lat"], s["lon"]] for s in self.metro_stations]
                        self.metro_tree = cKDTree(coords)
                logger.info(f"Loaded {len(self.metro_stations)} normalized Metro stations into generic router.")
            except Exception as e:
                logger.error(f"Failed to load metro_network.json: {e}")

        # 2. Suburban & MRTS Network
        suburban_file = os.path.join(self.data_dir, "suburban_network.json")
        if os.path.exists(suburban_file):
            try:
                with open(suburban_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.suburban_stations = data.get("stations", [])
                    self.suburban_routes = data.get("routes", [])
                    if HAS_SCIPY and self.suburban_stations:
                        coords = [[s["lat"], s["lon"]] for s in self.suburban_stations]
                        self.suburban_tree = cKDTree(coords)
                logger.info(f"Loaded {len(self.suburban_stations)} normalized Suburban/MRTS stations into generic router.")
            except Exception as e:
                logger.error(f"Failed to load suburban_network.json: {e}")

        # 3. MTC Bus Network
        bus_file = os.path.join(self.data_dir, "bus_network.json")
        if os.path.exists(bus_file):
            try:
                with open(bus_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.bus_stops = data.get("stops", [])
                    self.bus_routes = data.get("routes", [])
                    for s in self.bus_stops:
                        self.bus_stop_map[s["id"]] = s
                    
                    # Build inverted index: stop_id -> routes serving it
                    for r in self.bus_routes:
                        rid = r["route_id"]
                        s_num = r["service_number"]
                        l_name = r["route_long_name"]
                        for p_idx, pat in enumerate(r["patterns"]):
                            for st_idx, sid in enumerate(pat):
                                if sid not in self.bus_stop_routes:
                                    self.bus_stop_routes[sid] = []
                                self.bus_stop_routes[sid].append({
                                    "route_id": rid,
                                    "service_number": s_num,
                                    "route_long_name": l_name,
                                    "pattern_idx": p_idx,
                                    "stop_idx": st_idx,
                                    "pattern": pat
                                })

                    if HAS_SCIPY and self.bus_stops:
                        coords = [[s["lat"], s["lon"]] for s in self.bus_stops]
                        self.bus_tree = cKDTree(coords)
                logger.info(f"Loaded {len(self.bus_stops)} Bus stops and {len(self.bus_routes)} Bus routes into generic router.")
            except Exception as e:
                logger.error(f"Failed to load bus_network.json: {e}")

        # 4. Interchanges
        int_file = os.path.join(self.data_dir, "interchanges.json")
        if os.path.exists(int_file):
            try:
                with open(int_file, "r", encoding="utf-8") as f:
                    self.interchanges = json.load(f)
                logger.info(f"Loaded {len(self.interchanges)} multimodal transfer hubs.")
            except Exception as e:
                logger.error(f"Failed to load interchanges.json: {e}")

    def query_nearby_stations(self, lat: float, lon: float, mode: str, max_dist_m: float, k: int = 8) -> List[Dict[str, Any]]:
        """Finds stations or stops within distance radius."""
        if mode == "metro" and self.metro_tree:
            dist_deg = max_dist_m / 111000.0
            idxs = self.metro_tree.query_ball_point([lat, lon], r=dist_deg)
            res = []
            for i in idxs:
                st = self.metro_stations[i]
                d = haversine_m(lat, lon, st["lat"], st["lon"])
                if d <= max_dist_m:
                    res.append((d, st))
            res.sort(key=lambda x: x[0])
            return [item[1] for item in res[:k]]

        elif mode in ["suburban", "mrts"] and self.suburban_tree:
            dist_deg = max_dist_m / 111000.0
            idxs = self.suburban_tree.query_ball_point([lat, lon], r=dist_deg)
            res = []
            for i in idxs:
                st = self.suburban_stations[i]
                if mode == "mrts" and st.get("type") != "MRTS":
                    continue
                d = haversine_m(lat, lon, st["lat"], st["lon"])
                if d <= max_dist_m:
                    res.append((d, st))
            res.sort(key=lambda x: x[0])
            return [item[1] for item in res[:k]]

        elif mode == "bus" and self.bus_tree:
            dist_deg = max_dist_m / 111000.0
            idxs = self.bus_tree.query_ball_point([lat, lon], r=dist_deg)
            res = []
            for i in idxs:
                st = self.bus_stops[i]
                d = haversine_m(lat, lon, st["lat"], st["lon"])
                if d <= max_dist_m:
                    res.append((d, st))
            res.sort(key=lambda x: x[0])
            return [item[1] for item in res[:k]]

        return []

    async def search_candidates(
        self,
        source_loc: Location,
        dest_loc: Location,
        direct_road_dist_m: float,
        direct_road_dur_s: float,
        route_provider: Any,
        ist_dt: datetime.datetime,
        preferences: List[str]
    ) -> List[CandidateRoute]:
        """
        Generates validated multimodal transit candidates across Metro, Suburban Rail, MRTS, and Government Bus.
        Evaluates dynamic station selection, destination access, and GTFS timetable availability.
        """
        s_lon, s_lat = source_loc.coordinates[0], source_loc.coordinates[1]
        d_lon, d_lat = dest_loc.coordinates[0], dest_loc.coordinates[1]
        dist_direct = haversine_m(s_lat, s_lon, d_lat, d_lon)

        candidates = []

        # -------------------------------------------------------------
        # 1. DIRECT GOVERNMENT BUS (MTC) CORRIDORS
        # -------------------------------------------------------------
        try:
            # Bus stop catchments: origin walk up to 1.2 km or 30% of trip; dest walk up to 1.2 km
            bus_walk_max = min(1200.0, max(800.0, direct_road_dist_m * 0.35))
            orig_bus_stops = self.query_nearby_stations(s_lat, s_lon, "bus", max_dist_m=bus_walk_max, k=8)
            dest_bus_stops = self.query_nearby_stations(d_lat, d_lon, "bus", max_dist_m=bus_walk_max, k=8)

            dest_stop_ids = {s["id"]: s for s in dest_bus_stops}
            found_bus_pairs = []

            for o_stop in orig_bus_stops:
                oid = o_stop["id"]
                serving_routes = self.bus_stop_routes.get(oid, [])
                for route_info in serving_routes:
                    pat = route_info["pattern"]
                    o_idx = route_info["stop_idx"]
                    # Search if any dest_stop is later in this pattern
                    for d_idx in range(o_idx + 1, len(pat)):
                        did = pat[d_idx]
                        if did in dest_stop_ids:
                            d_stop = dest_stop_ids[did]
                            # Direction invariant: destination stop must bring user closer to destination
                            d_orig_to_dest = haversine_m(o_stop["lat"], o_stop["lon"], d_lat, d_lon)
                            d_dest_to_dest = haversine_m(d_stop["lat"], d_stop["lon"], d_lat, d_lon)
                            progress = d_orig_to_dest - d_dest_to_dest
                            
                            # Meaningful forward progress requirement (scaled by trip length)
                            min_progress = min(600.0, max(150.0, dist_direct * 0.25))
                            if progress >= min_progress:
                                sub_stops = pat[o_idx : d_idx + 1]
                                walk_access_est = haversine_m(s_lat, s_lon, o_stop["lat"], o_stop["lon"])
                                walk_egress_est = haversine_m(d_lat, d_lon, d_stop["lat"], d_stop["lon"])
                                found_bus_pairs.append({
                                    "route_info": route_info,
                                    "orig_stop": o_stop,
                                    "dest_stop": d_stop,
                                    "stop_count": len(sub_stops),
                                    "stop_ids": sub_stops,
                                    "progress": progress,
                                    "walk_est": walk_access_est + walk_egress_est
                                })
                    if len(found_bus_pairs) >= 30:
                        break
                if len(found_bus_pairs) >= 30:
                    break

            # Sort candidate stop pairs to prioritize shortest walking access/egress and highest transit progress
            found_bus_pairs.sort(key=lambda bp: (bp["walk_est"], -bp["progress"]))

            seen_bus_services = set()
            bus_candidates_added = 0

            for bus_cand in found_bus_pairs:
                if bus_candidates_added >= 2:
                    break

                r_info = bus_cand["route_info"]
                o_st = bus_cand["orig_stop"]
                d_st = bus_cand["dest_stop"]
                s_num = r_info["service_number"]
                l_name = r_info["route_long_name"]
                stop_ids = bus_cand["stop_ids"]

                # Prioritize distinct bus service numbers for diverse choices (e.g. 555G and 555P)
                if s_num in seen_bus_services:
                    continue
                seen_bus_services.add(s_num)

                # Check schedule availability using ScheduleEngine operating window (04:30 - 22:30 IST)
                sched_status, sched_meta = global_schedule_engine.get_service_availability("bus", f"Bus {s_num}", ist_dt)
                if sched_status == "OUT_OF_SERVICE_HOURS":
                    logger.info(f"Bus {s_num} candidate skipped: outside operating hours ({sched_meta.get('reason')})")
                    continue

                # Build bus leg geometry from ordered stop coordinates
                bus_geom_coords = []
                bus_dist_m = 0.0
                last_pt = None
                for sid in stop_ids:
                    st_obj = self.bus_stop_map.get(sid)
                    if st_obj:
                        pt = [st_obj["lon"], st_obj["lat"]]
                        if last_pt:
                            bus_dist_m += haversine_m(last_pt[1], last_pt[0], pt[1], pt[0])
                        bus_geom_coords.append(pt)
                        last_pt = pt

                # Meaningful bus ride: at least 2 stops and 400m bus distance
                if len(bus_geom_coords) < 2 or bus_dist_m < 250:
                    continue

                # Access and Egress legs via OSRM in parallel
                acc_routes, egr_routes = await asyncio.gather(
                    route_provider.get_routes(
                        source_loc, Location(type="Point", coordinates=[o_st["lon"], o_st["lat"]]),
                        mode="foot", alternatives="false"
                    ),
                    route_provider.get_routes(
                        Location(type="Point", coordinates=[d_st["lon"], d_st["lat"]]), dest_loc,
                        mode="foot", alternatives="false"
                    )
                )

                if acc_routes and egr_routes:
                    acc_r = acc_routes[0]
                    egr_r = egr_routes[0]
                    
                    # Typical city bus speed ~18 km/h (5.0 m/s) + 30s dwell time per stop + 8 min expected wait
                    bus_wait_s = 480
                    bus_dur_s = (bus_dist_m / 5.0) + (len(stop_ids) * 30) + bus_wait_s
                    total_dur = acc_r.duration + bus_dur_s + egr_r.duration
                    total_dist = acc_r.distance + bus_dist_m + egr_r.distance

                    # Viability check: total walking distance must be significantly less than direct distance,
                    # and total distance must not exceed 1.7x direct road
                    walk_saving = (acc_r.distance + egr_r.distance) <= max(direct_road_dist_m * 0.95, direct_road_dist_m - 30.0)
                    dist_ok = total_dist <= max(direct_road_dist_m * 1.70, direct_road_dist_m + 800)
                    # Realistic urban bus duration threshold: allow for stopping city bus pace vs unobstructed personal vehicle
                    dur_ok = total_dur <= max(direct_road_dur_s * 4.5, direct_road_dur_s + 3600, 5400)

                    if (walk_saving or direct_road_dist_m > 2500) and dist_ok and dur_ok:
                        acc_coords = acc_r.route_metadata.get("geometry", {}).get("coordinates", [])
                        egr_coords = egr_r.route_metadata.get("geometry", {}).get("coordinates", [])

                        # Ensure strict endpoint continuity
                        o_pt = [o_st["lon"], o_st["lat"]]
                        d_pt = [d_st["lon"], d_st["lat"]]
                        if not acc_coords: acc_coords = [[s_lon, s_lat], o_pt]
                        elif acc_coords[-1] != o_pt: acc_coords.append(o_pt)
                        if bus_geom_coords[0] != o_pt: bus_geom_coords.insert(0, o_pt)
                        if bus_geom_coords[-1] != d_pt: bus_geom_coords.append(d_pt)
                        if not egr_coords: egr_coords = [d_pt, [d_lon, d_lat]]
                        elif egr_coords[0] != d_pt: egr_coords.insert(0, d_pt)

                        all_bus_coords = []
                        for pt in acc_coords:
                            if not all_bus_coords or all_bus_coords[-1] != pt: all_bus_coords.append(pt)
                        for pt in bus_geom_coords:
                            if not all_bus_coords or all_bus_coords[-1] != pt: all_bus_coords.append(pt)
                        for pt in egr_coords:
                            if not all_bus_coords or all_bus_coords[-1] != pt: all_bus_coords.append(pt)

                        cand = CandidateRoute(
                            route_identifier=f"verified_bus_{len(candidates)}",
                            distance=total_dist,
                            duration=total_dur,
                            recommendation_status="AVAILABLE"
                        )
                        bus_fare = global_fare_engine.calculate_bus_fare(
                            s_num, o_st["name"], d_st["name"], bus_dist_m
                        )
                        cand.route_metadata = {
                            "geometry": {"type": "LineString", "coordinates": all_bus_coords},
                            "travel_mode": "Multimodal",
                            "route_name": f"Walk + MTC Bus {s_num} ({o_st['name']} to {d_st['name']}) + Walk",
                            "cost": bus_fare.display_text,
                            "fare": bus_fare.model_dump(),
                            "distinctness_status": "DISTINCT",
                            "dynamic_segments": [
                                {
                                    "mode": "walk",
                                    "start_name": "Origin",
                                    "end_name": o_st["name"],
                                    "distance_m": acc_r.distance,
                                    "duration_s": acc_r.duration,
                                    "geometry": {"type": "LineString", "coordinates": acc_coords},
                                    "geometry_complete": True
                                },
                                {
                                    "mode": "bus",
                                    "service_number": s_num,
                                    "start_name": o_st["name"],
                                    "end_name": d_st["name"],
                                    "distance_m": bus_dist_m,
                                    "duration_s": bus_dur_s,
                                    "waiting_time_s": bus_wait_s,
                                    "geometry": {"type": "LineString", "coordinates": bus_geom_coords},
                                    "geometry_complete": True,
                                    "stops_count": len(stop_ids),
                                    "schedule_source": sched_meta.get("source", "MTC GTFS Verified Operating Hours"),
                                    "operational_status": sched_status
                                },
                                {
                                    "mode": "walk",
                                    "start_name": d_st["name"],
                                    "end_name": "Destination",
                                    "distance_m": egr_r.distance,
                                    "duration_s": egr_r.duration,
                                    "geometry": {"type": "LineString", "coordinates": egr_coords},
                                    "geometry_complete": True
                                }
                            ]
                        }
                        candidates.append(cand)
                        bus_candidates_added += 1
                        logger.info(f"Discovered direct MTC Bus candidate: Bus {s_num} ({len(stop_ids)} stops, {bus_dist_m:.0f}m)")
        except Exception as e:
            logger.warning(f"Error querying bus network candidates: {e}")

        # -------------------------------------------------------------
        # 2. METRO & SUBURBAN RAILWAY CANDIDATES
        # -------------------------------------------------------------
        try:
            # Catchment distances: access up to 12 km or 65% of trip; egress up to 14 km or 45% of trip
            max_acc_m = min(12000.0, max(3000.0, direct_road_dist_m * 0.65))
            max_egr_m = min(14000.0, max(2500.0, direct_road_dist_m * 0.45))

            for rail_mode in ["suburban", "metro"]:
                if len(candidates) >= 3:
                    break

                graph = get_graph_for_mode(rail_mode)
                if not graph:
                    continue

                orig_stations = self.query_nearby_stations(s_lat, s_lon, rail_mode, max_dist_m=max_acc_m, k=6)
                dest_stations = self.query_nearby_stations(d_lat, d_lon, rail_mode, max_dist_m=max_egr_m, k=6)

                feasible_itineraries = []

                for orig_st in orig_stations:
                    for dest_st in dest_stations:
                        if orig_st["name"] == dest_st["name"]:
                            continue

                        d_orig_to_dest = haversine_m(orig_st["lat"], orig_st["lon"], d_lat, d_lon)
                        d_dest_to_dest = haversine_m(dest_st["lat"], dest_st["lon"], d_lat, d_lon)

                        # Progress invariant: destination station must be closer to final destination
                        if d_dest_to_dest >= (d_orig_to_dest - 1200):
                            continue

                        # Direction invariant: track distance must be meaningful
                        st_dist = haversine_m(orig_st["lat"], orig_st["lon"], dest_st["lat"], dest_st["lon"])
                        if st_dist < 1200 or (d_orig_to_dest - d_dest_to_dest) < (0.35 * st_dist):
                            continue

                        # Check operating hours and GTFS timetables
                        avail_status, avail_meta = global_schedule_engine.get_service_availability(
                            rail_mode, f"{orig_st['name']} to {dest_st['name']}", ist_dt
                        )
                        if avail_status == "UNAVAILABLE":
                            continue

                        # Build actual track geometry from mode-specific graph
                        track_coords, track_dist, track_status = graph.build_transit_segment(
                            rail_mode, orig_st["lat"], orig_st["lon"], dest_st["lat"], dest_st["lon"]
                        )
                        if track_status != "SUCCESS" or not track_coords or track_dist < 1200:
                            continue

                        # Determine access and egress travel modes (foot if <= 1.2km, else driving/auto)
                        acc_dist_direct = haversine_m(s_lat, s_lon, orig_st["lat"], orig_st["lon"])
                        egr_dist_direct = haversine_m(dest_st["lat"], dest_st["lon"], d_lat, d_lon)
                        acc_osrm = "foot" if acc_dist_direct <= 1200 else "driving"
                        egr_osrm = "foot" if egr_dist_direct <= 1200 else "driving"
                        acc_disp = "walk" if acc_osrm == "foot" else "auto"
                        egr_disp = "walk" if egr_osrm == "foot" else "auto"

                        # Door-to-Door cost heuristic for ranking station pairs:
                        # Prioritize pairs with shorter egress walk/auto and direct track connections
                        # to eliminate destination overshoots and backtracking
                        wait_secs = avail_meta.get("waiting_time", 10) * 60 if avail_meta else (8 * 60 if "metro" in rail_mode else 14 * 60)
                        speed_mps = 11.1 if "suburban" in rail_mode else 9.7
                        transit_dur = (track_dist / speed_mps) + wait_secs + 180
                        
                        est_total_dist = acc_dist_direct * 1.3 + track_dist + egr_dist_direct * 1.3
                        est_egress_dur = (egr_dist_direct / 1.3) if egr_disp == "walk" else (egr_dist_direct / 8.0)
                        
                        # Penalty for long egress distance (prevents overshooting like Central -> Beach)
                        cost_score = transit_dur + (est_egress_dur * 1.5) + (egr_dist_direct * 0.1)

                        feasible_itineraries.append({
                            "orig_st": orig_st,
                            "dest_st": dest_st,
                            "acc_osrm": acc_osrm,
                            "egr_osrm": egr_osrm,
                            "acc_disp": acc_disp,
                            "egr_disp": egr_disp,
                            "track_coords": track_coords,
                            "track_dist": track_dist,
                            "transit_dur": transit_dur,
                            "wait_secs": wait_secs,
                            "avail_meta": avail_meta,
                            "cost_score": cost_score,
                            "egr_dist_direct": egr_dist_direct
                        })

                # Sort feasible itineraries by cost score (optimal station selection)
                feasible_itineraries.sort(key=lambda x: x["cost_score"])

                for itin in feasible_itineraries[:2]:
                    orig_st = itin["orig_st"]
                    dest_st = itin["dest_st"]
                    track_coords = itin["track_coords"]
                    track_dist = itin["track_dist"]
                    transit_dur = itin["transit_dur"]
                    wait_secs = itin["wait_secs"]
                    avail_meta = itin["avail_meta"]
                    acc_disp = itin["acc_disp"]
                    egr_disp = itin["egr_disp"]

                    acc_r, egr_r = await asyncio.gather(
                        route_provider.get_routes(
                            source_loc, Location(type="Point", coordinates=[orig_st["lon"], orig_st["lat"]]),
                            mode=itin["acc_osrm"], alternatives="false"
                        ),
                        route_provider.get_routes(
                            Location(type="Point", coordinates=[dest_st["lon"], dest_st["lat"]]), dest_loc,
                            mode=itin["egr_osrm"], alternatives="false"
                        )
                    )
                    if not acc_r or not egr_r:
                        continue

                    acc_dist = acc_r[0].distance
                    egr_dist = egr_r[0].distance
                    total_dist = acc_dist + track_dist + egr_dist
                    total_dur = acc_r[0].duration + transit_dur + egr_r[0].duration

                    # Detour check: must not exceed 1.55x direct road
                    if total_dist > max(direct_road_dist_m * 1.55, direct_road_dist_m + 3000):
                        continue
                    if (track_dist / total_dist) < 0.20:
                        continue

                    acc_geom = acc_r[0].route_metadata.get("geometry", {}).get("coordinates", [])
                    egr_geom = egr_r[0].route_metadata.get("geometry", {}).get("coordinates", [])

                    # Strict continuity
                    o_pt = [orig_st["lon"], orig_st["lat"]]
                    d_pt = [dest_st["lon"], dest_st["lat"]]
                    if not acc_geom: acc_geom = [[s_lon, s_lat], o_pt]
                    elif acc_geom[-1] != o_pt: acc_geom.append(o_pt)
                    if track_coords[0] != o_pt: track_coords.insert(0, o_pt)
                    if track_coords[-1] != d_pt: track_coords.append(d_pt)
                    if not egr_geom: egr_geom = [d_pt, [d_lon, d_lat]]
                    elif egr_geom[0] != d_pt: egr_geom.insert(0, d_pt)

                    full_coords = []
                    for pt in acc_geom:
                        if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                    for pt in track_coords:
                        if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                    for pt in egr_geom:
                        if not full_coords or full_coords[-1] != pt: full_coords.append(pt)

                    mode_name = orig_st.get("type", rail_mode.capitalize())
                    cand = CandidateRoute(
                        route_identifier=f"verified_rail_{len(candidates)}",
                        distance=total_dist,
                        duration=total_dur,
                        recommendation_status="AVAILABLE"
                    )

                    rail_seg_meta = {
                        "mode": rail_mode,
                        "start_name": orig_st["name"],
                        "end_name": dest_st["name"],
                        "distance_m": track_dist,
                        "duration_s": transit_dur,
                        "waiting_time_s": wait_secs,
                        "geometry": {"type": "LineString", "coordinates": track_coords},
                        "geometry_complete": True
                    }
                    if avail_meta and avail_meta.get("data_type") == "GTFS_TIMETABLE_DEPARTURE":
                        rail_seg_meta["departure_time"] = avail_meta.get("departure_time")
                        rail_seg_meta["arrival_time"] = avail_meta.get("arrival_time")
                        rail_seg_meta["trip_id"] = avail_meta.get("trip_id")
                        rail_seg_meta["service_headsign"] = avail_meta.get("headsign")
                        rail_seg_meta["data_type"] = "GTFS_TIMETABLE_DEPARTURE"

                    if "metro" in rail_mode:
                        rail_fare = global_fare_engine.calculate_metro_fare(orig_st["name"], dest_st["name"])
                    else:
                        rail_fare = global_fare_engine.calculate_suburban_fare(orig_st["name"], dest_st["name"], track_dist)

                    cand.route_metadata = {
                        "geometry": {"type": "LineString", "coordinates": full_coords},
                        "travel_mode": "Multimodal",
                        "route_name": f"{acc_disp.capitalize()} + {mode_name} ({orig_st['name']} to {dest_st['name']}) + {egr_disp.capitalize()}",
                        "cost": rail_fare.display_text,
                        "fare": rail_fare.model_dump(),
                        "distinctness_status": "DISTINCT",
                        "dynamic_segments": [
                            {
                                "mode": acc_disp,
                                "start_name": "Origin",
                                "end_name": orig_st["name"],
                                "distance_m": acc_dist,
                                "duration_s": acc_r[0].duration,
                                "geometry": {"type": "LineString", "coordinates": acc_geom},
                                "geometry_complete": True
                            },
                            rail_seg_meta,
                            {
                                "mode": egr_disp,
                                "start_name": dest_st["name"],
                                "end_name": "Destination",
                                "distance_m": egr_dist,
                                "duration_s": egr_r[0].duration,
                                "geometry": {"type": "LineString", "coordinates": egr_geom},
                                "geometry_complete": True
                            }
                        ]
                    }
                    candidates.append(cand)
                    logger.info(f"Discovered optimized {rail_mode} candidate: {orig_st['name']} -> {dest_st['name']} (score={itin['cost_score']:.1f})")
                    break
        except Exception as e:
            logger.warning(f"Error querying rail candidates: {e}")

        # -------------------------------------------------------------
        # 3. GENERIC MULTIMODAL RAIL-TO-BUS INTERCHANGE CORRIDORS
        # -------------------------------------------------------------
        try:
            # Query multimodal transfers if few transit candidates exist or trip exceeds 8km
            if len(candidates) < 3 and direct_road_dist_m > 8000:
                # 3A. Destination feeder bus stop catchment (up to 2000m from destination)
                dest_bus_stops = self.query_nearby_stations(d_lat, d_lon, "bus", max_dist_m=2000, k=8)
                dest_stop_ids = {s["id"]: s for s in dest_bus_stops}

                # 3B. Origin rail station catchment
                max_acc_m = min(12000.0, max(3000.0, direct_road_dist_m * 0.65))
                rail_modes_to_check = ["suburban", "metro"]

                transfer_found = False
                for rail_mode in rail_modes_to_check:
                    if len(candidates) >= 3 or transfer_found:
                        break

                    graph = get_graph_for_mode(rail_mode)
                    if not graph:
                        continue

                    orig_stations = self.query_nearby_stations(s_lat, s_lon, rail_mode, max_dist_m=max_acc_m, k=5)
                    if not orig_stations:
                        continue

                    seen_combos = set()
                    for d_sid, d_st in dest_stop_ids.items():
                        if transfer_found:
                            break
                        routes = self.bus_stop_routes.get(d_sid, [])
                        for r in routes:
                            if transfer_found:
                                break
                            s_num = r["service_number"]
                            pat = r["pattern"]
                            d_idx = r["stop_idx"]

                            # Scan earlier stops in the bus pattern for rail transfer proximity (within 800m)
                            for st_idx in range(0, d_idx):
                                if transfer_found:
                                    break
                                tr_sid = pat[st_idx]
                                tr_bus_stop = self.bus_stop_map.get(tr_sid)
                                if not tr_bus_stop:
                                    continue

                                nearby_rail = self.query_nearby_stations(
                                    tr_bus_stop["lat"], tr_bus_stop["lon"], rail_mode, max_dist_m=800, k=2
                                )
                                for tr_rail_st in nearby_rail:
                                    if transfer_found:
                                        break
                                    combo_key = (orig_stations[0]["name"], tr_rail_st["name"], s_num)
                                    if combo_key in seen_combos:
                                        continue
                                    seen_combos.add(combo_key)

                                    for orig_st in orig_stations:
                                        if orig_st["name"] == tr_rail_st["name"]:
                                            continue

                                        d_orig_to_dest = haversine_m(orig_st["lat"], orig_st["lon"], d_lat, d_lon)
                                        d_tr_to_dest = haversine_m(tr_rail_st["lat"], tr_rail_st["lon"], d_lat, d_lon)

                                        # Progress check: transfer station must be significantly closer to destination than origin
                                        if d_tr_to_dest >= (d_orig_to_dest - 2500):
                                            continue

                                        # Rail segment geometry
                                        track_coords, track_dist, track_status = graph.build_transit_segment(
                                            rail_mode, orig_st["lat"], orig_st["lon"], tr_rail_st["lat"], tr_rail_st["lon"]
                                        )
                                        if track_status != "SUCCESS" or not track_coords or track_dist < 2000:
                                            continue

                                        # Bus segment geometry from transfer stop to destination stop
                                        bus_sub_pat = pat[st_idx:d_idx+1]
                                        bus_geom_coords = []
                                        bus_dist_m = 0.0
                                        last_pt = None
                                        for sid in bus_sub_pat:
                                            st_obj = self.bus_stop_map.get(sid)
                                            if st_obj:
                                                pt = [st_obj["lon"], st_obj["lat"]]
                                                if last_pt:
                                                    bus_dist_m += haversine_m(last_pt[1], last_pt[0], pt[1], pt[0])
                                                bus_geom_coords.append(pt)
                                                last_pt = pt

                                        if len(bus_geom_coords) < 2 or bus_dist_m < 800:
                                            continue

                                        # Walking access to origin rail station
                                        acc_routes = await route_provider.get_routes(
                                            source_loc, Location(type="Point", coordinates=[orig_st["lon"], orig_st["lat"]]),
                                            mode="foot", alternatives="false"
                                        )
                                        
                                        # Transfer walk from rail station to bus stand (synthesize if <= 500m to avoid external network delay)
                                        tr_walk_dist = haversine_m(tr_rail_st["lat"], tr_rail_st["lon"], tr_bus_stop["lat"], tr_bus_stop["lon"])
                                        if tr_walk_dist <= 500.0:
                                            class SyntheticTransferWalk:
                                                distance = tr_walk_dist
                                                duration = max(60.0, tr_walk_dist / 1.2)
                                                route_metadata = {
                                                    "geometry": {
                                                        "type": "LineString",
                                                        "coordinates": [
                                                            [tr_rail_st["lon"], tr_rail_st["lat"]],
                                                            [tr_bus_stop["lon"], tr_bus_stop["lat"]]
                                                        ]
                                                    }
                                                }
                                            tr_walk_routes = [SyntheticTransferWalk()]
                                        else:
                                            tr_walk_routes = await route_provider.get_routes(
                                                Location(type="Point", coordinates=[tr_rail_st["lon"], tr_rail_st["lat"]]),
                                                Location(type="Point", coordinates=[tr_bus_stop["lon"], tr_bus_stop["lat"]]),
                                                mode="foot", alternatives="false"
                                            )
                                            
                                        # Egress walk from destination bus stop to final destination
                                        egr_routes = await route_provider.get_routes(
                                            Location(type="Point", coordinates=[d_st["lon"], d_st["lat"]]),
                                            dest_loc,
                                            mode="foot", alternatives="false"
                                        )

                                        if not acc_routes or not tr_walk_routes or not egr_routes:
                                            continue

                                        acc_r = acc_routes[0]
                                        tr_w_r = tr_walk_routes[0]
                                        egr_r = egr_routes[0]

                                        # Speeds and durations
                                        rail_speed = 11.1 if "suburban" in rail_mode else 9.7
                                        rail_wait = 10 * 60 if "suburban" in rail_mode else 6 * 60
                                        rail_dur = (track_dist / rail_speed) + rail_wait

                                        bus_wait = 8 * 60  # average wait at transfer hub
                                        bus_dur = (bus_dist_m / 5.0) + (len(bus_sub_pat) * 30) + bus_wait

                                        total_dist = acc_r.distance + track_dist + tr_w_r.distance + bus_dist_m + egr_r.distance
                                        total_dur = acc_r.duration + rail_dur + tr_w_r.duration + bus_dur + egr_r.duration

                                        # Continuity
                                        acc_geom = acc_r.route_metadata.get("geometry", {}).get("coordinates", [])
                                        tr_w_geom = tr_w_r.route_metadata.get("geometry", {}).get("coordinates", [])
                                        egr_geom = egr_r.route_metadata.get("geometry", {}).get("coordinates", [])

                                        o_pt = [orig_st["lon"], orig_st["lat"]]
                                        tr_rail_pt = [tr_rail_st["lon"], tr_rail_st["lat"]]
                                        tr_bus_pt = [tr_bus_stop["lon"], tr_bus_stop["lat"]]
                                        d_bus_pt = [d_st["lon"], d_st["lat"]]

                                        full_coords = []
                                        for pt in (acc_geom or [[s_lon, s_lat], o_pt]):
                                            if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                                        for pt in track_coords:
                                            if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                                        for pt in (tr_w_geom or [tr_rail_pt, tr_bus_pt]):
                                            if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                                        for pt in bus_geom_coords:
                                            if not full_coords or full_coords[-1] != pt: full_coords.append(pt)
                                        for pt in (egr_geom or [d_bus_pt, [d_lon, d_lat]]):
                                            if not full_coords or full_coords[-1] != pt: full_coords.append(pt)

                                        # Calculate fares
                                        if "metro" in rail_mode:
                                            rail_fare = global_fare_engine.calculate_metro_fare(orig_st["name"], tr_rail_st["name"])
                                        else:
                                            rail_fare = global_fare_engine.calculate_suburban_fare(orig_st["name"], tr_rail_st["name"], track_dist)
                                        bus_fare = global_fare_engine.calculate_bus_fare(s_num, tr_bus_stop["name"], d_st["name"], bus_dist_m)

                                        combined_amount = (rail_fare.amount or 0.0) + (bus_fare.amount or 0.0)
                                        if rail_fare.is_official and bus_fare.is_official:
                                            fare_display = f"₹ {combined_amount:.0f}"
                                            is_off = True
                                        elif rail_fare.amount is not None:
                                            fare_display = f"₹ {combined_amount:.0f} (estimated)" if bus_fare.amount else f"{rail_fare.display_text} + Bus"
                                            is_off = False
                                        else:
                                            fare_display = "Fare unavailable"
                                            is_off = False

                                        mode_title = orig_st.get("type", rail_mode.capitalize())
                                        cand = CandidateRoute(
                                            route_identifier=f"multimodal_transfer_{len(candidates)}",
                                            distance=total_dist,
                                            duration=total_dur,
                                            recommendation_status="AVAILABLE"
                                        )
                                        cand.route_metadata = {
                                            "geometry": {"type": "LineString", "coordinates": full_coords},
                                            "travel_mode": "Multimodal",
                                            "route_name": f"Walk + {mode_title} to {tr_rail_st['name']} + MTC Bus {s_num} to {d_st['name']} + Walk",
                                            "cost": fare_display,
                                            "fare": {
                                                "fare_type": "OFFICIAL_FARE" if is_off else "ESTIMATED_FARE",
                                                "currency": "INR",
                                                "amount": combined_amount if combined_amount > 0 else None,
                                                "display_text": fare_display,
                                                "source_label": f"{rail_fare.source_label} + {bus_fare.source_label}",
                                                "is_official": is_off
                                            },
                                            "distinctness_status": "DISTINCT",
                                            "dynamic_segments": [
                                                {
                                                    "mode": "walk",
                                                    "start_name": "Origin",
                                                    "end_name": orig_st["name"],
                                                    "distance_m": acc_r.distance,
                                                    "duration_s": acc_r.duration,
                                                    "geometry": {"type": "LineString", "coordinates": acc_geom},
                                                    "geometry_complete": True
                                                },
                                                {
                                                    "mode": rail_mode,
                                                    "start_name": orig_st["name"],
                                                    "end_name": tr_rail_st["name"],
                                                    "distance_m": track_dist,
                                                    "duration_s": rail_dur,
                                                    "waiting_time_s": rail_wait,
                                                    "geometry": {"type": "LineString", "coordinates": track_coords},
                                                    "geometry_complete": True
                                                },
                                                {
                                                    "mode": "walk",
                                                    "start_name": tr_rail_st["name"],
                                                    "end_name": tr_bus_stop["name"],
                                                    "distance_m": tr_w_r.distance,
                                                    "duration_s": tr_w_r.duration,
                                                    "geometry": {"type": "LineString", "coordinates": tr_w_geom},
                                                    "geometry_complete": True
                                                },
                                                {
                                                    "mode": "bus",
                                                    "service_number": s_num,
                                                    "start_name": tr_bus_stop["name"],
                                                    "end_name": d_st["name"],
                                                    "distance_m": bus_dist_m,
                                                    "duration_s": bus_dur,
                                                    "waiting_time_s": bus_wait,
                                                    "geometry": {"type": "LineString", "coordinates": bus_geom_coords},
                                                    "geometry_complete": True,
                                                    "stops_count": len(bus_sub_pat)
                                                },
                                                {
                                                    "mode": "walk",
                                                    "start_name": d_st["name"],
                                                    "end_name": "Destination",
                                                    "distance_m": egr_r.distance,
                                                    "duration_s": egr_r.duration,
                                                    "geometry": {"type": "LineString", "coordinates": egr_geom},
                                                    "geometry_complete": True
                                                }
                                            ]
                                        }
                                        candidates.append(cand)
                                        logger.info(f"Discovered multimodal transfer route: {orig_st['name']} -> {tr_rail_st['name']} -> Bus {s_num} -> {d_st['name']}")
                                        transfer_found = True
                                        break
        except Exception as e:
            logger.warning(f"Error querying multimodal transfer candidates: {e}")

        return candidates

global_multimodal_router = MultimodalRouter()
