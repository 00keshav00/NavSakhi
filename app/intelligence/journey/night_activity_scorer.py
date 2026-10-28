"""
NavSakhi - Phase 48: Night Activity Scorer (v2.0)

Evaluates dedicated nighttime activity intelligence along a journey corridor:
1. Geographic Coverage: Chennai Metropolitan Area (CMA) bounds enforcement (12.75 <= lat <= 13.35, 79.90 <= lon <= 80.45).
2. Activity Distribution & Segmentation: Continuous distance segmentation evaluating active open places along the entire route.
3. Anti-Isolation Penalty: Penalizes continuous dark / inactive corridor stretches.
4. Opening Hours Evaluation: Evaluates OSM opening_hours against estimated pass-through hour (OPEN, CLOSED, UNKNOWN).
5. Public Help & Emergency Proximity: Police stations, hospitals, clinics, and pharmacies.
6. Transit Access & Main Corridor Share: Access to transit nodes and major road vitality.
7. Public Surveillance Cameras: Real OSM surveillance cameras counted with explicit operational status disclaimer.
8. Component Maximums Sum to 100:
   - Coverage: 25.0
   - Corridor Continuity & Density: 20.0
   - Open Places & Vitality: 20.0
   - Emergency & Public Help: 15.0
   - Transit Access & Main Corridor: 10.0
   - Data Confidence: 10.0
   Total = 100.0 pts max.
9. Transparent Piecewise Normalization:
   D(S) = 4S for 0 <= S <= 10
   D(S) = 40 + 60(S-10)/90 for 10 < S <= 100
10. Explicit Concern Levels:
    - S <= 10: HIGH_CONCERN
    - 10 < S < 30: LIMITED_INDICATORS
    - S >= 30: SUPPORTED_INDICATORS
"""

import os
import json
import math
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from scipy.spatial import cKDTree

from app.schemas.journey_schemas import NightActivityScoreResponse

logger = logging.getLogger("NightActivityScorer")

# Chennai Metropolitan Area (CMA) Bounds
CMA_MIN_LAT = 12.75
CMA_MAX_LAT = 13.35
CMA_MIN_LON = 79.90
CMA_MAX_LON = 80.45

# Projection constants (WGS84 local equirectangular)
REF_LAT = 13.0827
M_PER_DEG_LAT = 110540.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(REF_LAT))

POI_DATA_PATH = os.path.join("poi_data", "processed", "chennai_pois.json")


def _to_xy(lon: float, lat: float) -> Tuple[float, float]:
    return (lon - 80.2090) * M_PER_DEG_LON, (lat - REF_LAT) * M_PER_DEG_LAT


class NightActivityScorer:
    """
    Dedicated heuristic Night Activity Assessment service.
    Operates alongside the frozen LightGBM model without altering ML semantics.
    """

    _instance = None

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or POI_DATA_PATH
        self.pois: List[Dict[str, Any]] = []
        self.cameras: List[Dict[str, Any]] = []
        self.tree: Optional[cKDTree] = None
        self.cam_tree: Optional[cKDTree] = None
        self.is_loaded = False
        self._load_pois()

    def _load_pois(self):
        if not os.path.exists(self.data_path):
            logger.warning(f"POI data file not found at {self.data_path}")
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_pois = json.load(f)

            self.pois = []
            self.cameras = []
            poi_coords = []
            cam_coords = []

            for p in raw_pois:
                lat = p.get("latitude") if p.get("latitude") is not None else p.get("lat")
                lon = p.get("longitude") if p.get("longitude") is not None else p.get("lon")
                if lat is None or lon is None:
                    continue
                x, y = _to_xy(lon, lat)

                cat = p.get("category", "")
                if cat in ["surveillance", "surveillance_camera"] or p.get("man_made") == "surveillance":
                    self.cameras.append(p)
                    cam_coords.append((x, y))
                else:
                    self.pois.append(p)
                    poi_coords.append((x, y))

            if poi_coords:
                self.tree = cKDTree(np.array(poi_coords, dtype=np.float64))
            if cam_coords:
                self.cam_tree = cKDTree(np.array(cam_coords, dtype=np.float64))

            self.is_loaded = True
            logger.info(f"Loaded {len(self.pois)} activity POIs and {len(self.cameras)} cameras into NightActivityScorer.")
        except Exception as e:
            logger.error(f"Failed to load POIs in NightActivityScorer: {e}")
            self.is_loaded = False

    def _parse_coordinates(self, coords: List[Any]) -> List[Tuple[float, float]]:
        """Parses list of (lat, lon) or [lon, lat] points into standard (lat, lon) tuples."""
        cleaned = []
        for pt in coords:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                c0, c1 = float(pt[0]), float(pt[1])
                # Disambiguate lat and lon
                if 12.0 <= c0 <= 14.5 and 79.0 <= c1 <= 81.5:
                    cleaned.append((c0, c1))
                elif 79.0 <= c0 <= 81.5 and 12.0 <= c1 <= 14.5:
                    cleaned.append((c1, c0))
                else:
                    # Default: assume (lat, lon)
                    cleaned.append((c0, c1))
        return cleaned

    def _is_within_cma(self, coords: List[Tuple[float, float]]) -> bool:
        """Verifies that all coordinates fall within the Chennai Metropolitan Area."""
        if not coords:
            return False
        for lat, lon in coords:
            if not (CMA_MIN_LAT <= lat <= CMA_MAX_LAT and CMA_MIN_LON <= lon <= CMA_MAX_LON):
                return False
        return True

    def _evaluate_opening_status(self, poi: Dict[str, Any], pass_through_hour: int) -> str:
        """
        Evaluates opening status at pass-through hour:
        Returns: 'OPEN', 'CLOSED', or 'UNKNOWN'
        """
        if poi.get("is_24_7") or poi.get("emergency") == "yes":
            return "OPEN"

        raw_hours = poi.get("opening_hours")
        if not raw_hours or not isinstance(raw_hours, str) or not raw_hours.strip():
            return "UNKNOWN"

        try:
            from app.intelligence.journey.opening_hours_parser import evaluate_opening_hours
            import datetime
            now = datetime.datetime.now()
            target_dt = now.replace(hour=pass_through_hour % 24, minute=0, second=0, microsecond=0)
            status = evaluate_opening_hours(raw_hours, target_dt)
            return status.value
        except Exception:
            return "UNKNOWN"

    def _compute_normalized_score(self, raw_score: float) -> float:
        """
        Applies documented piecewise linear normalization:
        D(S) = 4S for 0 <= S <= 10
        D(S) = 40 + 60(S-10)/90 for 10 < S <= 100
        """
        s = max(0.0, min(100.0, float(raw_score)))
        if s <= 10.0:
            return 4.0 * s
        else:
            return 40.0 + (60.0 * (s - 10.0) / 90.0)

    def _determine_concern_level(self, raw_score: float) -> str:
        if raw_score <= 10.0:
            return "HIGH_CONCERN"
        elif raw_score < 30.0:
            return "LIMITED_INDICATORS"
        else:
            return "SUPPORTED_INDICATORS"

    def evaluate_route(
        self,
        route_coords: List[Any],
        pass_through_hour: int = 22,
        corridor_m: float = 600.0,
    ) -> NightActivityScoreResponse:
        """
        Evaluates route coordinates for nighttime activity intelligence.
        """
        parsed_coords = self._parse_coordinates(route_coords)

        # 1. Geographic Boundary Check
        if not self._is_within_cma(parsed_coords):
            return NightActivityScoreResponse(
                overall_score=0.0,
                coverage_score=0.0,
                isolation_penalty=0.0,
                density_score=0.0,
                corridor_continuity_score=0.0,
                open_volume_score=0.0,
                emergency_score=0.0,
                transit_access_score=0.0,
                confidence_score=0.0,
                data_confidence_score=0.0,
                normalized_score=0.0,
                concern_level="HIGH_CONCERN",
                surveillance_cameras_count=0,
                corridor_open_places_count=0,
                total_corridor_places_count=0,
                corridor_unknown_hours_count=0,
                longest_dark_gap_meters=0.0,
                formula_version="v2.0",
                is_out_of_bounds=True,
                status="OUT_OF_BOUNDS",
            )

        if not self.is_loaded or self.tree is None or len(parsed_coords) < 2:
            return NightActivityScoreResponse(
                overall_score=10.0,
                coverage_score=2.5,
                isolation_penalty=0.0,
                density_score=2.0,
                corridor_continuity_score=2.0,
                open_volume_score=2.0,
                emergency_score=1.5,
                transit_access_score=1.0,
                confidence_score=1.0,
                data_confidence_score=1.0,
                normalized_score=40.0,
                concern_level="HIGH_CONCERN",
                surveillance_cameras_count=0,
                corridor_open_places_count=0,
                total_corridor_places_count=0,
                corridor_unknown_hours_count=0,
                longest_dark_gap_meters=0.0,
                formula_version="v2.0",
                is_out_of_bounds=False,
                status="DATA_UNAVAILABLE",
            )

        # 2. Project route coordinates and sample route at 100m intervals
        pts_xy = [_to_xy(lon, lat) for lat, lon in parsed_coords]
        sample_pts = []
        seg_lengths = []
        total_len_m = 0.0

        for i in range(len(pts_xy) - 1):
            x1, y1 = pts_xy[i]
            x2, y2 = pts_xy[i + 1]
            seg_dist = math.hypot(x2 - x1, y2 - y1)
            seg_lengths.append(seg_dist)
            total_len_m += seg_dist

            steps = max(1, int(seg_dist // 100.0))
            for s in range(steps):
                t = s / steps
                sample_pts.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
        sample_pts.append(pts_xy[-1])

        # 3. Discover corridor POIs
        corridor_poi_indices = set().union(*self.tree.query_ball_point(sample_pts, r=corridor_m))

        # Categorize discovered POIs
        confirmed_open = 0
        confirmed_closed = 0
        unknown_hours = 0
        emergency_count = 0
        transit_count = 0

        corridor_open_pts = []
        for idx in corridor_poi_indices:
            p = self.pois[idx]
            cat = p.get("category", "")
            if cat in ["police", "hospital", "clinic", "fire_station"]:
                emergency_count += 1

            if cat in ["transit_station", "bus_stop", "metro_station", "railway_station"] or "station" in cat:
                transit_count += 1

            status = self._evaluate_opening_status(p, pass_through_hour)
            if status == "OPEN":
                confirmed_open += 1
                corridor_open_pts.append(_to_xy(p["longitude"], p["latitude"]))
            elif status == "CLOSED":
                confirmed_closed += 1
            else:
                unknown_hours += 1

        total_corridor_places = len(corridor_poi_indices)

        # 4. Surveillance Cameras Discovery
        surveillance_cameras_count = 0
        if self.cam_tree is not None:
            cam_indices = set().union(*self.cam_tree.query_ball_point(sample_pts, r=corridor_m))
            surveillance_cameras_count = len(cam_indices)

        # 5. Measure Longest Dark / Inactive Gap along route
        longest_dark_gap = 0.0
        active_sample_count = 0

        if corridor_open_pts:
            open_tree = cKDTree(np.array(corridor_open_pts, dtype=np.float64))
            curr_gap = 0.0
            step_m = total_len_m / max(1, len(sample_pts) - 1)
            distances, _ = open_tree.query(sample_pts)

            for d in distances:
                if d <= corridor_m:
                    active_sample_count += 1
                    curr_gap = 0.0
                else:
                    curr_gap += step_m
                    if curr_gap > longest_dark_gap:
                        longest_dark_gap = curr_gap
        else:
            longest_dark_gap = total_len_m

        # 6. Compute Mathematical Subscores (Component Maximums sum to 100)
        # Component 1: Active Spatial Coverage [0, 25]
        coverage_ratio = active_sample_count / max(1, len(sample_pts))
        coverage_score = round(coverage_ratio * 25.0, 1)

        # Component 2: Corridor Continuity & Anti-Isolation [0, 20]
        # Penalizes long continuous dark gaps (> 800m)
        gap_penalty_ratio = min(1.0, longest_dark_gap / max(1200.0, total_len_m))
        corridor_continuity_score = round(max(0.0, (1.0 - gap_penalty_ratio) * 20.0), 1)

        # Component 3: Open Volume & Commercial Vitality [0, 20]
        # Scales with confirmed open places (target: 10+ places for full score)
        open_volume_score = round(min(20.0, (confirmed_open / 10.0) * 20.0), 1)

        # Component 4: Emergency & Public Help Proximity [0, 15]
        # Scales with presence of police/hospital/clinics (target: 3+ for full score)
        emergency_score = round(min(15.0, (emergency_count / 3.0) * 15.0), 1)

        # Component 5: Transit Access & Main Corridor [0, 10]
        # Scales with transit nodes along route (target: 2+ stations/stops)
        transit_access_score = round(min(10.0, (transit_count / 2.0) * 10.0), 1)

        # Component 6: Data Confidence & Hours Completeness [0, 10]
        # Ratio of known hours vs total places
        if total_corridor_places > 0:
            known_ratio = (confirmed_open + confirmed_closed) / total_corridor_places
            confidence_score = round(min(10.0, 4.0 + (known_ratio * 6.0)), 1)
        else:
            confidence_score = 4.0

        # Calculate Overall Raw Score (Sum of components [0, 100])
        overall_score = round(
            coverage_score +
            corridor_continuity_score +
            open_volume_score +
            emergency_score +
            transit_access_score +
            confidence_score,
            1
        )
        overall_score = max(0.0, min(100.0, overall_score))

        # 7. Calculate Normalized Score and Concern Level
        normalized_score = self._compute_normalized_score(overall_score)
        concern_level = self._determine_concern_level(overall_score)

        return NightActivityScoreResponse(
            overall_score=overall_score,
            coverage_score=coverage_score,
            isolation_penalty=round(gap_penalty_ratio * 20.0, 1),
            density_score=corridor_continuity_score,
            corridor_continuity_score=corridor_continuity_score,
            open_volume_score=open_volume_score,
            emergency_score=emergency_score,
            transit_access_score=transit_access_score,
            confidence_score=confidence_score,
            data_confidence_score=confidence_score,
            normalized_score=normalized_score,
            concern_level=concern_level,
            surveillance_cameras_count=surveillance_cameras_count,
            corridor_open_places_count=confirmed_open,
            total_corridor_places_count=total_corridor_places,
            corridor_unknown_hours_count=unknown_hours,
            longest_dark_gap_meters=round(longest_dark_gap, 1),
            formula_version="v2.0",
            is_out_of_bounds=False,
            status="CALCULATED",
        )


night_activity_scorer = NightActivityScorer()
