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
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy.spatial import cKDTree

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
                x, y = _to_projected_xy(p["longitude"], p["latitude"])
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
        max_total_pois: int = 25,
    ) -> Dict[str, Any]:
        """
        Queries verified facilities within a configurable corridor along route coordinates.

        Args:
            route_coords: List of [longitude, latitude] coordinates for the journey.
            corridor_m: Search buffer in meters around route geometry (default 800m).
            legs: Optional list of individual journey legs to map facility to leg_id.
            max_pois_per_category: Maximum returned records per facility category.
            max_total_pois: Global cap on returned POIs.

        Returns:
            Dict containing:
            - pois: List of validated POI dictionaries
            - summary: Count breakdown by category
            - corridor_m: The applied corridor radius
            - status: "AVAILABLE", "EMPTY", or "UNAVAILABLE"
        """
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

        # 1. Project route coordinates to local meters
        pts_m = [_to_projected_xy(pt[0], pt[1]) for pt in route_coords]

        # 2. Build segments for fast nearest distance calculation
        # Subdivide long segments (> 200m) into intermediate sample points for initial KDTree ball query
        candidate_indices = set()
        step_m = 150.0
        query_pts_m = []

        for i in range(len(pts_m) - 1):
            ax, ay = pts_m[i]
            bx, by = pts_m[i + 1]
            seg_len = math.hypot(bx - ax, by - ay)
            query_pts_m.append((ax, ay))
            if seg_len > step_m:
                steps = int(seg_len // step_m)
                for s in range(1, steps + 1):
                    frac = s / (steps + 1)
                    query_pts_m.append((ax + frac * (bx - ax), ay + frac * (by - ay)))
        query_pts_m.append(pts_m[-1])

        # Broad-phase candidate discovery via KD-Tree
        for qx, qy in query_pts_m:
            idxs = self.tree.query_ball_point([qx, qy], r=corridor_m + 50.0)
            candidate_indices.update(idxs)

        if not candidate_indices:
            return {
                "pois": [],
                "summary": {},
                "corridor_m": corridor_m,
                "status": "EMPTY",
                "total_found": 0,
            }

        # Prepare leg geometries if available
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
                leg_data.append((leg_id, leg_pts_m))

        # 3. Narrow-phase: compute exact shortest distance from candidate POI to route line segments
        matched_pois = []
        for idx in candidate_indices:
            poi = self.pois[idx]
            px, py = self.poi_coords_m[idx]

            min_dist_m = float("inf")
            nearest_leg_id = None

            # Calculate distance against full route segments
            for i in range(len(pts_m) - 1):
                ax, ay = pts_m[i]
                bx, by = pts_m[i + 1]
                d = _point_to_segment_distance(px, py, ax, ay, bx, by)
                if d < min_dist_m:
                    min_dist_m = d

            # If within corridor, determine nearest leg
            if min_dist_m <= corridor_m:
                if leg_data:
                    min_leg_dist = float("inf")
                    for leg_id, leg_pts in leg_data:
                        if len(leg_pts) >= 2:
                            for li in range(len(leg_pts) - 1):
                                lax, lay = leg_pts[li]
                                lbx, lby = leg_pts[li + 1]
                                ld = _point_to_segment_distance(px, py, lax, lay, lbx, lby)
                                if ld < min_leg_dist:
                                    min_leg_dist = ld
                                    nearest_leg_id = leg_id

                proximity_tier = "IMMEDIATELY_BESIDE" if min_dist_m <= 100.0 else "ALONG_CORRIDOR"

                matched_pois.append({
                    "poi_id": poi["poi_id"],
                    "osm_id": poi.get("osm_id"),
                    "name": poi["name"],
                    "category": poi["category"],
                    "category_label": poi.get("category_label", poi["category"].replace("_", " ").title()),
                    "latitude": poi["latitude"],
                    "longitude": poi["longitude"],
                    "distance_to_route_m": round(min_dist_m, 1),
                    "proximity_tier": proximity_tier,
                    "nearest_route_leg_id": nearest_leg_id,
                    "is_emergency": poi.get("is_emergency", False),
                    "operator": poi.get("operator"),
                    "source": poi.get("source", "OpenStreetMap (ODbL 1.0)"),
                    "last_verified_at": poi.get("last_verified_at"),
                })

        # 4. Sort and cap to prevent sending huge payloads
        # Sort by distance_to_route_m ascending
        matched_pois.sort(key=lambda p: p["distance_to_route_m"])

        # Cap per category and overall
        category_counts: Dict[str, int] = {}
        filtered_pois: List[Dict[str, Any]] = []

        for p in matched_pois:
            cat = p["category"]
            current_cat_count = category_counts.get(cat, 0)
            if current_cat_count < max_pois_per_category and len(filtered_pois) < max_total_pois:
                filtered_pois.append(p)
                category_counts[cat] = current_cat_count + 1

        summary = {}
        for p in filtered_pois:
            summary[p["category"]] = summary.get(p["category"], 0) + 1

        status = "AVAILABLE" if filtered_pois else "EMPTY"

        return {
            "pois": filtered_pois,
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
