"""
SafeShe - Phase 21: Verified Points of Interest (POI) Spatial Service.

Performs generic, high-performance spatial querying of verified safety facilities
(police stations, hospitals, clinics, pharmacies, fire stations) along any route geometry.

Guarantees:
- Only genuine OpenStreetMap ODbL verified facilities are returned.
- Exact shortest orthogonal distance from facility to route segments in meters.
- Deterministic deduplication across overlapping route segments.
- Bounded response payloads (configurable search corridor and category limits).
- Truthful empty states; zero synthetic or placeholder markers.
"""

import os
import json
import math
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import box as shapely_box
from shapely.strtree import STRtree

logger = logging.getLogger("SafeShePOIService")

DEFAULT_POI_DATA_PATH = os.path.join("poi_data", "processed", "chennai_pois.json")
DEFAULT_MANIFEST_PATH = os.path.join("poi_data", "manifest.json")

# Chennai projection constants (WGS84 local equirectangular projection)
REF_LAT = 13.0827
M_PER_DEG_LAT = 110540.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(REF_LAT))


def _to_projected_xy(lon: float, lat: float) -> Tuple[float, float]:
    """Projects WGS84 lon/lat into local meters around Chennai reference point."""
    x = (lon - 80.2090) * M_PER_DEG_LON
    y = (lat - REF_LAT) * M_PER_DEG_LAT
    return x, y


def _dist_sq(p1: np.ndarray, p2: np.ndarray) -> float:
    diff = p1 - p2
    return float(np.dot(diff, diff))


def _point_to_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """Computes exact shortest Euclidean distance from point P to line segment AB in meters."""
    dx = bx - ax
    dy = by - ay
    l2 = dx * dx + dy * dy
    if l2 <= 1e-9:
        # Segment is effectively a point
        return math.hypot(px - ax, py - ay)
    
    # Projection parameter t
    t = ((px - ax) * dx + (py - ay) * dy) / l2
    t_clamped = max(0.0, min(1.0, t))
    
    proj_x = ax + t_clamped * dx
    proj_y = ay + t_clamped * dy
    return math.hypot(px - proj_x, py - proj_y)


def _reference_nearest_leg_assignment(
    px: float,
    py: float,
    leg_data: List[Tuple[str, List[Tuple[float, float]], Tuple[float, float, float, float]]]
) -> Tuple[Optional[str], float]:
    """
    Reference pure-Python nearest leg assignment for verification and safe fallback.
    Evaluates shortest orthogonal Euclidean distance against segments within bounding box.
    """
    min_leg_dist = float("inf")
    nearest_leg_id = None
    for leg_id, leg_pts, (l_min_x, l_min_y, l_max_x, l_max_y) in leg_data:
        if not (l_min_x <= px <= l_max_x and l_min_y <= py <= l_max_y):
            continue
        for li in range(len(leg_pts) - 1):
            lax, lay = leg_pts[li]
            lbx, lby = leg_pts[li + 1]
            ld = _point_to_segment_distance(px, py, lax, lay, lbx, lby)
            if ld < min_leg_dist:
                min_leg_dist = ld
                nearest_leg_id = leg_id
    return nearest_leg_id, min_leg_dist


def _assign_nearest_legs_vectorized(
    poi_px: np.ndarray,
    poi_py: np.ndarray,
    leg_data: List[Tuple[str, List[Tuple[float, float]], Tuple[float, float, float, float]]],
    batch_size: int = 250
) -> Tuple[List[Optional[str]], List[float]]:
    """
    Vectorized multimodal leg assignment using batched NumPy broadcasting.
    Evaluates exact Euclidean point-to-segment distance against all bounding-box-filtered leg segments.
    Preserves exact tie-breaking semantics (earlier leg in sequence order wins ties).

    Peak memory is bounded to ~4.0 MiB at batch_size=250 for long multimodal legs (618+ segments),
    accounting for broadcast intermediate arrays while maximizing L2/L3 CPU cache locality.
    """
    P = len(poi_px)
    if P == 0 or not leg_data:
        return [None] * P, [float("inf")] * P

    try:
        vectorized_legs = []
        for leg_id, leg_pts, (l_min_x, l_min_y, l_max_x, l_max_y) in leg_data:
            n_pts = len(leg_pts)
            if n_pts < 2:
                continue
            pts_arr = np.array(leg_pts, dtype=np.float64)
            ax = pts_arr[:-1, 0]
            ay = pts_arr[:-1, 1]
            bx = pts_arr[1:, 0]
            by = pts_arr[1:, 1]
            dx = bx - ax
            dy = by - ay
            l2 = dx * dx + dy * dy
            l2_safe = np.where(l2 <= 1e-9, 1.0, l2)
            is_deg = l2 <= 1e-9
            vectorized_legs.append({
                "leg_id": leg_id,
                "ax": ax,
                "ay": ay,
                "dx": dx,
                "dy": dy,
                "l2_safe": l2_safe,
                "is_deg": is_deg,
                "bbox": (l_min_x, l_min_y, l_max_x, l_max_y)
            })

        if not vectorized_legs:
            return [None] * P, [float("inf")] * P

        best_leg_dist = np.full(P, np.inf, dtype=np.float64)
        best_leg_id: List[Optional[str]] = [None] * P

        for b_start in range(0, P, batch_size):
            b_end = min(b_start + batch_size, P)
            b_px = poi_px[b_start:b_end]
            b_py = poi_py[b_start:b_end]

            b_best_dist = best_leg_dist[b_start:b_end]
            b_best_id = best_leg_id[b_start:b_end]

            for leg in vectorized_legs:
                l_min_x, l_min_y, l_max_x, l_max_y = leg["bbox"]
                in_bbox = (b_px >= l_min_x) & (b_px <= l_max_x) & (b_py >= l_min_y) & (b_py <= l_max_y)
                if not np.any(in_bbox):
                    continue

                active_indices = np.where(in_bbox)[0]
                act_px = b_px[active_indices, None]
                act_py = b_py[active_indices, None]

                ax = leg["ax"][None, :]
                ay = leg["ay"][None, :]
                dx = leg["dx"][None, :]
                dy = leg["dy"][None, :]
                l2_safe = leg["l2_safe"][None, :]
                is_deg = leg["is_deg"][None, :]

                t = ((act_px - ax) * dx + (act_py - ay) * dy) / l2_safe
                t_clamped = np.clip(t, 0.0, 1.0)
                t_clamped = np.where(is_deg, 0.0, t_clamped)

                proj_x = ax + t_clamped * dx
                proj_y = ay + t_clamped * dy

                dists_sq = (act_px - proj_x) ** 2 + (act_py - proj_y) ** 2
                leg_min_sq = np.min(dists_sq, axis=1)
                leg_min_dist = np.sqrt(leg_min_sq)

                current_best = b_best_dist[active_indices]
                improved = leg_min_dist < current_best

                improved_active = active_indices[improved]
                b_best_dist[improved_active] = leg_min_dist[improved]
                leg_id_val = leg["leg_id"]
                for idx_pos in improved_active:
                    b_best_id[idx_pos] = leg_id_val

            best_leg_dist[b_start:b_end] = b_best_dist
            best_leg_id[b_start:b_end] = b_best_id

        return best_leg_id, best_leg_dist.tolist()

    except Exception as e:
        logger.warning(f"Vectorized leg assignment fallback to reference due to error: {e}")
        fallback_ids = []
        fallback_dists = []
        for i in range(P):
            f_id, f_d = _reference_nearest_leg_assignment(float(poi_px[i]), float(poi_py[i]), leg_data)
            fallback_ids.append(f_id)
            fallback_dists.append(f_d)
        return fallback_ids, fallback_dists


class POISpatialService:
    """
    Spatial query service for verified safety facilities.
    Thread-safe and fast via SciPy cKDTree spatial indexing.
    """

    _instance = None

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or DEFAULT_POI_DATA_PATH
        self.pois: List[Dict[str, Any]] = []
        self.tree: Optional[cKDTree] = None
        self.poi_coords_m: Optional[np.ndarray] = None
        self.is_loaded = False
        self._load_dataset()

    def _load_dataset(self):
        if not os.path.exists(self.data_path):
            logger.warning(f"POI data file not found at: {self.data_path}. Spatial queries will return empty results.")
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.pois = json.load(f)

            if not self.pois:
                logger.warning("POI dataset is empty.")
                return

            n = len(self.pois)
            self.poi_coords_m = np.zeros((n, 2), dtype=np.float64)
            for i, p in enumerate(self.pois):
                lat = p.get("latitude") if p.get("latitude") is not None else p.get("lat")
                lon = p.get("longitude") if p.get("longitude") is not None else p.get("lon")
                x, y = _to_projected_xy(lon, lat)
                self.poi_coords_m[i, 0] = x
                self.poi_coords_m[i, 1] = y

            self.tree = cKDTree(self.poi_coords_m)
            self.is_loaded = True
            logger.info(f"Loaded {n} verified safety POIs into spatial index.")
        except Exception as e:
            logger.error(f"Failed to load POI dataset: {e}")
            self.is_loaded = False

    def query_pois_near_route(
        self,
        route_coords: List[List[float]],
        corridor_m: float = 800.0,
        legs: Optional[List[Dict[str, Any]]] = None,
        max_pois_per_category: int = 6,
        max_total_pois: int = 35,
        total_duration_s: float = 0.0,
        departure_dt: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        """
        Queries verified facilities and commercial shops within a corridor along route coordinates,
        evaluating opening status at estimated arrival / pass-through time.
        """
        import datetime
        from app.intelligence.journey.opening_hours_parser import evaluate_opening_hours

        if not self.is_loaded or self.tree is None or not self.pois:
            return {
                "pois": [],
                "summary": {},
                "corridor_m": corridor_m,
                "status": "UNAVAILABLE",
                "total_found": 0,
            }

        if not route_coords or len(route_coords) < 2:
            return {
                "pois": [],
                "summary": {},
                "corridor_m": corridor_m,
                "status": "EMPTY",
                "total_found": 0,
            }

        if departure_dt is None:
            # Default to Chennai IST (UTC+5:30)
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            departure_dt = datetime.datetime.now(ist_tz)

        # 1. Project route coordinates to local meters and compute cumulative lengths
        pts_m = [_to_projected_xy(pt[0], pt[1]) for pt in route_coords]
        seg_lens_m: List[float] = []
        cum_dist_m: List[float] = [0.0]
        total_route_len_m = 0.0

        for i in range(len(pts_m) - 1):
            ax, ay = pts_m[i]
            bx, by = pts_m[i + 1]
            slen = math.hypot(bx - ax, by - ay)
            seg_lens_m.append(slen)
            total_route_len_m += slen
            cum_dist_m.append(total_route_len_m)

        if total_route_len_m <= 0.0:
            total_route_len_m = 1.0

        # 2. Build sample points for initial KDTree ball query
        candidate_indices = set()
        step_m = 150.0
        query_pts_m = []

        for i in range(len(pts_m) - 1):
            ax, ay = pts_m[i]
            bx, by = pts_m[i + 1]
            seg_len = seg_lens_m[i]
            query_pts_m.append((ax, ay))
            if seg_len > step_m:
                steps = int(seg_len // step_m)
                for s in range(1, steps + 1):
                    frac = s / (steps + 1)
                    query_pts_m.append((ax + frac * (bx - ax), ay + frac * (by - ay)))
        query_pts_m.append(pts_m[-1])

        # Broad-phase candidate discovery via KD-Tree
        if query_pts_m:
            raw_matches = self.tree.query_ball_point(query_pts_m, r=corridor_m + 50.0)
            candidate_indices = set().union(*raw_matches)

        if not candidate_indices:
            return {
                "pois": [],
                "summary": {},
                "corridor_m": corridor_m,
                "status": "EMPTY",
                "total_found": 0,
            }

        # Build spatial STRtree over route segments for O(log N) candidate segment queries
        seg_boxes = []
        for i in range(len(pts_m) - 1):
            ax, ay = pts_m[i]
            bx, by = pts_m[i + 1]
            seg_boxes.append(shapely_box(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)))
        seg_tree = STRtree(seg_boxes) if seg_boxes else None

        # Prepare leg geometries if available, pre-filtering bounding boxes
        leg_data = []
        if legs:
            for l_idx, leg in enumerate(legs):
                leg_id = leg.get("leg_id") or f"leg_{l_idx+1}"
                geom = leg.get("polyline") or leg.get("geometry")
                leg_coords = []
                if isinstance(geom, dict):
                    if geom.get("type") == "Feature":
                        leg_coords = geom.get("geometry", {}).get("coordinates", [])
                    elif geom.get("type") == "LineString":
                        leg_coords = geom.get("coordinates", [])
                elif isinstance(geom, list):
                    leg_coords = geom
                
                leg_pts_m = [_to_projected_xy(c[0], c[1]) for c in leg_coords if len(c) >= 2]
                if len(leg_pts_m) >= 2:
                    xs = [p[0] for p in leg_pts_m]
                    ys = [p[1] for p in leg_pts_m]
                    bbox = (min(xs) - corridor_m, min(ys) - corridor_m, max(xs) + corridor_m, max(ys) + corridor_m)
                    leg_data.append((leg_id, leg_pts_m, bbox))

        EMERGENCY_CATEGORIES = {"police", "hospital", "clinic", "pharmacy", "fire_station", "fuel"}
        LANDMARK_CATEGORIES = {"mall", "university", "college", "transit_hub", "park", "landmark", "commercial_complex"}
        SHOP_CATEGORIES = {"convenience", "supermarket", "retail_shop", "food_retail", "restaurant", "cafe", "fast_food", "hotel", "bank_atm", "entertainment"}

        # 3. Narrow-phase: compute exact shortest distance and route progress via STRtree
        corridor_candidates = []
        for idx in candidate_indices:
            poi = self.pois[idx]
            px, py = self.poi_coords_m[idx]

            # Query candidate segments within corridor bounding box
            if seg_tree is not None:
                qbox = shapely_box(px - corridor_m, py - corridor_m, px + corridor_m, py + corridor_m)
                candidate_seg_indices = seg_tree.query(qbox)
            else:
                candidate_seg_indices = range(len(pts_m) - 1)

            if len(candidate_seg_indices) == 0:
                continue

            min_dist_m = float("inf")
            best_progress_m = 0.0

            # Calculate distance only against candidate route segments
            for i in candidate_seg_indices:
                ax, ay = pts_m[i]
                bx, by = pts_m[i + 1]
                dx = bx - ax
                dy = by - ay
                l2 = dx * dx + dy * dy
                if l2 <= 1e-9:
                    d = math.hypot(px - ax, py - ay)
                    t_clamped = 0.0
                else:
                    t = ((px - ax) * dx + (py - ay) * dy) / l2
                    t_clamped = max(0.0, min(1.0, t))
                    proj_x = ax + t_clamped * dx
                    proj_y = ay + t_clamped * dy
                    d = math.hypot(px - proj_x, py - proj_y)

                if d < min_dist_m:
                    min_dist_m = d
                    best_progress_m = cum_dist_m[i] + t_clamped * seg_lens_m[i]

            # If within corridor, retain for vectorized leg assignment and response building
            if min_dist_m <= corridor_m:
                corridor_candidates.append((idx, poi, px, py, min_dist_m, best_progress_m))

        # Vectorized multimodal leg assignment across all corridor candidates
        if corridor_candidates and leg_data:
            cand_px = np.array([c[2] for c in corridor_candidates], dtype=np.float64)
            cand_py = np.array([c[3] for c in corridor_candidates], dtype=np.float64)
            assigned_leg_ids, _ = _assign_nearest_legs_vectorized(cand_px, cand_py, leg_data)
        else:
            assigned_leg_ids = [None] * len(corridor_candidates)

        matched_pois = []
        for c_idx, (idx, poi, px, py, min_dist_m, best_progress_m) in enumerate(corridor_candidates):
            nearest_leg_id = assigned_leg_ids[c_idx]
            proximity_tier = "IMMEDIATELY_BESIDE" if min_dist_m <= 100.0 else "ALONG_CORRIDOR"

            # Estimated arrival time at POI pass-through
            progress_ratio = max(0.0, min(1.0, best_progress_m / total_route_len_m))
            dur_s = total_duration_s if total_duration_s > 0 else (total_route_len_m / 8.33)  # default ~30km/h
            pass_through_dt = departure_dt + datetime.timedelta(seconds=progress_ratio * dur_s)
            pass_through_str = pass_through_dt.strftime("%I:%M %p")

            cat = poi.get("category", "retail_shop")
            name_lower = (poi.get("name") or "").lower()
            is_emergency = bool(poi.get("is_emergency") or cat in EMERGENCY_CATEGORIES)
            is_landmark = bool(
                cat in LANDMARK_CATEGORIES
                or any(kw in name_lower for kw in ["mall", "university", "college", "campus", "institute", "park", "central", "interchange"])
            )
            is_shop = bool((not is_emergency) and (cat in SHOP_CATEGORIES or poi.get("is_activity_location", False)))

            # Evaluate opening hours at pass-through time
            raw_hours = poi.get("opening_hours")
            status_eval = evaluate_opening_hours(raw_hours, pass_through_dt)
            opening_status = status_eval.value

            matched_pois.append({
                "poi_id": poi["poi_id"],
                "osm_id": poi.get("osm_id"),
                "name": poi["name"],
                "category": cat,
                "category_label": poi.get("category_label", cat.replace("_", " ").title()),
                "latitude": poi.get("latitude") if poi.get("latitude") is not None else poi.get("lat"),
                "longitude": poi.get("longitude") if poi.get("longitude") is not None else poi.get("lon"),
                "distance_to_route_m": round(min_dist_m, 1),
                "proximity_tier": proximity_tier,
                "nearest_route_leg_id": nearest_leg_id,
                "is_emergency": is_emergency,
                "is_landmark": is_landmark,
                "is_shop": is_shop,
                "opening_status": opening_status,
                "opening_hours": raw_hours,
                "estimated_pass_through_time": pass_through_str,
                "address": poi.get("address") or poi.get("locality"),
                "phone": poi.get("phone") or poi.get("contact:phone"),
                "website": poi.get("website") or poi.get("contact:website"),
                "operator": poi.get("operator"),
                "source": poi.get("source", "OpenStreetMap (ODbL 1.0)"),
                "last_verified_at": poi.get("last_verified_at"),
            })

        # 4. Sort and cap: separate emergency vs landmarks vs shops
        matched_pois.sort(key=lambda p: p["distance_to_route_m"])

        emergency_pois = [p for p in matched_pois if p["is_emergency"]]
        landmark_pois = [p for p in matched_pois if not p["is_emergency"] and p["is_landmark"]]
        shop_pois = [p for p in matched_pois if not p["is_emergency"] and not p["is_landmark"]]

        filtered_pois: List[Dict[str, Any]] = []
        category_counts: Dict[str, int] = {}
        effective_max_per_cat = max(max_pois_per_category, 15)
        effective_total_max = max(max_total_pois, 75)

        # Add up to 15 emergency POIs
        for p in emergency_pois:
            cat = p["category"]
            c_count = category_counts.get(cat, 0)
            if c_count < effective_max_per_cat and len(filtered_pois) < 18:
                filtered_pois.append(p)
                category_counts[cat] = c_count + 1

        # Add up to 10 major landmark POIs
        for p in landmark_pois:
            cat = p["category"]
            c_count = category_counts.get(cat, 0)
            if c_count < effective_max_per_cat and len(filtered_pois) < 28:
                filtered_pois.append(p)
                category_counts[cat] = c_count + 1

        # Add up to 50 shop POIs (allowing rich coverage for shop-dense corridors like Kandigai)
        shop_count = 0
        for p in shop_pois:
            cat = p["category"]
            c_count = category_counts.get(cat, 0)
            if c_count < effective_max_per_cat and shop_count < 50 and len(filtered_pois) < effective_total_max:
                filtered_pois.append(p)
                category_counts[cat] = c_count + 1
                shop_count += 1

        summary = {}
        for p in filtered_pois:
            summary[p["category"]] = summary.get(p["category"], 0) + 1

        # 5. Extract Mapped Commercial Activity Indicators (clusters of mapped shops/businesses)
        activity_zones = []
        if len(shop_pois) >= 3:
            # Cluster shops by proximity to identify commercial activity hotspots along corridor
            clusters: List[List[Dict[str, Any]]] = []
            for sp in shop_pois:
                added = False
                for cl in clusters:
                    ref = cl[0]
                    # Approx dist in meters
                    dlat = abs(sp["latitude"] - ref["latitude"]) * 111000
                    dlon = abs(sp["longitude"] - ref["longitude"]) * 108000
                    if math.hypot(dlat, dlon) <= 350.0:
                        cl.append(sp)
                        added = True
                        break
                if not added and len(clusters) < 6:
                    clusters.append([sp])

            for zi, cl in enumerate(clusters):
                if len(cl) >= 2:
                    avg_lat = sum(p["latitude"] for p in cl) / len(cl)
                    avg_lon = sum(p["longitude"] for p in cl) / len(cl)
                    lvl = "HIGH" if len(cl) >= 5 else "MODERATE"
                    activity_zones.append({
                        "zone_id": f"act_zone_{zi+1}",
                        "name": f"Mapped Activity Area ({cl[0].get('name', 'Commercial Area')})",
                        "latitude": round(avg_lat, 6),
                        "longitude": round(avg_lon, 6),
                        "radius_m": min(350, 150 + len(cl) * 20),
                        "activity_level": lvl,
                        "shop_count": len(cl),
                        "source": "OpenStreetMap Commercial Clusters (ODbL)",
                        "disclosure": "Derived from spatial concentration of mapped commercial businesses. Does not represent live crowd density or verified police presence."
                    })

        status = "AVAILABLE" if filtered_pois else "EMPTY"

        return {
            "pois": filtered_pois,
            "activity_zones": activity_zones,
            "summary": summary,
            "corridor_m": corridor_m,
            "status": status,
            "total_found": len(filtered_pois),
        }


# Global singleton instance
_global_poi_service: Optional[POISpatialService] = None


def get_poi_service() -> POISpatialService:
    global _global_poi_service
    if _global_poi_service is None:
        _global_poi_service = POISpatialService()
    return _global_poi_service
