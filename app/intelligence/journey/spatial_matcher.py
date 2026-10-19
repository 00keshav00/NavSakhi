import logging
import math
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

import numpy as np
import pandas as pd
import pyproj
from shapely.geometry import LineString, Point, MultiLineString, shape
from shapely import points as shapely_points
from shapely.strtree import STRtree

from app.schemas.spatial_schemas import (
    MatchStatus,
    FeatureStatus,
    MatchedSegmentResult,
    UnmatchedInterval,
    RouteCoverageMetrics,
    RouteSpatialMatchResponse,
)
from app.ml.schemas import (
    CANONICAL_PREDICTOR_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
)

logger = logging.getLogger(__name__)

DEFAULT_ROAD_SEGMENTS_PATH = Path("app/ml/Hack/ml/datasets/processed/road_segments.parquet")
DEFAULT_MASTER_FEATURE_PATH = Path("app/ml/Hack/ml/datasets/processed/master_feature_table.parquet")


class _SegmentRecords:
    """
    Lightweight memory-efficient proxy for segment metadata.
    Avoids pre-allocating over 1,000,000 separate Python dictionary objects,
    reducing memory consumption by over 240 MB while maintaining dict-like subscripting.
    """
    def __init__(self, segment_ids, way_ids, road_types, length_ms):
        self.segment_ids = segment_ids
        self.way_ids = way_ids
        self.road_types = road_types
        self.length_ms = length_ms

    def __len__(self) -> int:
        return len(self.segment_ids)

    def __getitem__(self, idx: Any) -> Any:
        if isinstance(idx, slice):
            return [self[i] for i in range(*idx.indices(len(self)))]
        wid = self.way_ids[idx]
        return {
            "segment_id": self.segment_ids[idx],
            "way_id": int(wid) if wid is not None and not (isinstance(wid, float) and math.isnan(wid)) else None,
            "road_type": self.road_types[idx],
            "length_m": float(self.length_ms[idx]),
        }


class SpatialMatchingService:
    """
    High-performance route-to-road-segment spatial matching and feature-row bridge.
    
    Responsibilities:
    1. Metric projection and coordinate normalization (EPSG:4326 to EPSG:32644 UTM 44N).
    2. Vectorized spatial indexing via Shapely STRtree for sub-millisecond candidate lookup.
    3. Traversal-ordered candidate snapping with configurable distance threshold and ambiguity detection.
    4. Consecutive deduplication that preserves legitimate route return loops.
    5. Route coverage and unmatched-interval accounting.
    6. Feature bridging to authoritative master feature table (41 canonical predictor features).
    """

    def __init__(
        self,
        road_segments_df: Optional[pd.DataFrame] = None,
        feature_table_df: Optional[pd.DataFrame] = None,
        road_segments_path: Optional[Union[str, Path]] = None,
        master_feature_path: Optional[Union[str, Path]] = None,
        max_match_distance_m: float = 35.0,
        ambiguity_delta_m: float = 5.0,
        sample_interval_m: float = 25.0,
        projected_crs: str = "EPSG:32644",
        geographic_crs: str = "EPSG:4326",
        auto_build_index: bool = True,
    ):
        self.max_match_distance_m = float(max_match_distance_m)
        self.ambiguity_delta_m = float(ambiguity_delta_m)
        self.sample_interval_m = float(sample_interval_m)
        self.projected_crs = projected_crs
        self.geographic_crs = geographic_crs

        self.road_segments_path = Path(road_segments_path) if road_segments_path else DEFAULT_ROAD_SEGMENTS_PATH
        self.master_feature_path = Path(master_feature_path) if master_feature_path else DEFAULT_MASTER_FEATURE_PATH

        # Projection transformers (always_xy=True ensures (lon, lat) -> (easting, northing) order)
        self.transformer = pyproj.Transformer.from_crs(self.geographic_crs, self.projected_crs, always_xy=True)
        self.inv_transformer = pyproj.Transformer.from_crs(self.projected_crs, self.geographic_crs, always_xy=True)

        self._road_segments_df: Optional[pd.DataFrame] = road_segments_df
        self._feature_table_df: Optional[pd.DataFrame] = feature_table_df

        self._index: Optional[STRtree] = None
        self._index_geoms: Optional[List[Any]] = None
        self._segment_records: List[Dict[str, Any]] = []
        self._feature_cache: Dict[str, Dict[str, Any]] = {}
        self._index_metadata: Dict[str, Any] = {}

        if auto_build_index and (road_segments_df is not None or self.road_segments_path.exists()):
            self.build_index()

    def _ensure_index_for_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float, margin: float = 0.03) -> None:
        """
        Ensures the spatial index covers the specified route bounding box.
        If self._road_segments_df was supplied explicitly (e.g. in tests), builds index from it.
        Otherwise, lazily loads only the road segments within the bounding box from parquet,
        preventing multi-gigabyte memory spikes and process termination on Render's 512MB RAM tier.
        """
        if self._road_segments_df is not None:
            if self._index is None:
                self.build_index()
            return

        target_bbox = (min_lon - margin, min_lat - margin, max_lon + margin, max_lat + margin)
        if self._index is not None and getattr(self, "_indexed_bbox", None) is not None:
            ib = self._indexed_bbox
            if ib[0] <= target_bbox[0] and ib[1] <= target_bbox[1] and ib[2] >= target_bbox[2] and ib[3] >= target_bbox[3]:
                return

        if not self.road_segments_path.exists():
            return

        import pyarrow.dataset as ds
        logger.info(f"Loading route-bounded road segments for lon [{target_bbox[0]:.4f}, {target_bbox[2]:.4f}], lat [{target_bbox[1]:.4f}, {target_bbox[3]:.4f}]...")
        road_dataset = ds.dataset(str(self.road_segments_path), format="parquet")
        filter_expr = (
            (ds.field("longitude") >= target_bbox[0]) & (ds.field("longitude") <= target_bbox[2]) &
            (ds.field("latitude") >= target_bbox[1]) & (ds.field("latitude") <= target_bbox[3])
        )
        cols = ["segment_id", "way_id", "latitude", "longitude", "length_m", "road_type"]
        table = road_dataset.to_table(filter=filter_expr, columns=cols)
        sub_df = table.to_pandas()
        self.build_index(road_segments_df=sub_df)
        self._indexed_bbox = target_bbox

    # --- Index Management ---

    def _load_road_segments_data(self) -> pd.DataFrame:
        if self._road_segments_df is not None:
            return self._road_segments_df
        if not self.road_segments_path.exists():
            raise FileNotFoundError(f"Road segments file not found at {self.road_segments_path}")
        logger.info(f"Loading road segments dataset from {self.road_segments_path}...")
        columns_to_load = ["segment_id", "way_id", "latitude", "longitude", "length_m", "road_type"]
        self._road_segments_df = pd.read_parquet(self.road_segments_path, columns=columns_to_load)
        return self._road_segments_df

    def _load_feature_table_data(self) -> pd.DataFrame:
        if self._feature_table_df is not None:
            return self._feature_table_df
        if not self.master_feature_path.exists():
            logger.warning(f"Master feature table not found at {self.master_feature_path}. Feature bridging will be disabled.")
            self._feature_table_df = pd.DataFrame()
            return self._feature_table_df
        logger.info(f"Loading master feature table from {self.master_feature_path}...")
        cols = ["segment_id"] + [c for c in CANONICAL_PREDICTOR_FEATURES]
        self._feature_table_df = pd.read_parquet(self.master_feature_path, columns=cols)
        return self._feature_table_df

    def build_index(self, road_segments_df: Optional[pd.DataFrame] = None) -> None:
        """Builds or rebuilds the metric spatial index (STRtree)."""
        t0 = time.perf_counter()
        if road_segments_df is not None:
            df = road_segments_df
            self._road_segments_df = road_segments_df
        else:
            df = self._load_road_segments_data()

        if len(df) == 0:
            logger.warning("Empty road segments dataset provided to build_index.")
            self._index = None
            self._segment_records = []
            return

        # Check for duplicate segment_id in source data
        dup_mask = df["segment_id"].duplicated(keep="first")
        if dup_mask.any():
            duplicate_ids = df.loc[dup_mask, "segment_id"].unique().tolist()
            logger.warning(f"Detected {len(duplicate_ids)} duplicate segment_ids in source data. Deduplicating on first occurrence.")
            df = df.loc[~dup_mask]
        else:
            duplicate_ids = []

        # Project coordinates or geometries into metric CRS
        if "geometry" in df.columns and hasattr(df["geometry"].iloc[0], "geom_type"):
            raw_geoms = df["geometry"].values
            # If already Shapely objects in WGS84, transform coordinates
            metric_geoms = []
            for g in raw_geoms:
                if isinstance(g, Point):
                    mx, my = self.transformer.transform(g.x, g.y)
                    metric_geoms.append(Point(mx, my))
                elif isinstance(g, LineString):
                    coords = [self.transformer.transform(x, y) for x, y in g.coords]
                    metric_geoms.append(LineString(coords))
                else:
                    metric_geoms.append(g)
            self._index_geoms = metric_geoms
        else:
            # Centroid points from longitude, latitude
            lons = df["longitude"].values
            lats = df["latitude"].values
            mx, my = self.transformer.transform(lons, lats)
            self._index_geoms = shapely_points(mx, my)

        # Build Shapely STRtree
        self._index = STRtree(self._index_geoms)

        # Store metadata aligned with index positions
        segment_ids = df["segment_id"].astype(str).tolist()
        way_ids = df["way_id"].tolist() if "way_id" in df.columns else [None] * len(df)
        road_types = df["road_type"].astype(str).tolist() if "road_type" in df.columns else ["unknown"] * len(df)
        length_ms = df["length_m"].fillna(0.0).astype(float).tolist() if "length_m" in df.columns else [0.0] * len(df)

        self._segment_records = _SegmentRecords(segment_ids, way_ids, road_types, length_ms)

        build_time_ms = (time.perf_counter() - t0) * 1000.0
        self._index_metadata = {
            "feature_count": len(self._segment_records),
            "projected_crs": self.projected_crs,
            "build_time_ms": round(build_time_ms, 2),
            "duplicate_ids_count": len(duplicate_ids),
        }
        logger.info(f"Built spatial index for {len(self._segment_records)} road segments in {build_time_ms:.2f}ms.")

    # --- Geometry Normalization ---

    def normalize_route_geometry(self, geom_input: Any) -> Tuple[LineString, List[Tuple[float, float]], Dict[str, Any]]:
        """
        Validates, orders, and projects route geometry to a metric LineString.
        
        Accepts:
        - GeoJSON dict: {"type": "LineString", "coordinates": [[lon, lat], ...]}
        - Coordinate list: [[lon, lat], ...]
        - Shapely LineString (assumed WGS84 coordinates)
        
        Returns:
            (metric_linestring, normalized_wgs84_coords, diagnostics)
        """
        diagnostics: Dict[str, Any] = {"coordinate_swapped": False, "original_point_count": 0}

        if geom_input is None:
            raise ValueError("Route geometry cannot be None")

        raw_coords = []
        if isinstance(geom_input, dict):
            geom_type = geom_input.get("type", "")
            if geom_type == "LineString":
                raw_coords = geom_input.get("coordinates", [])
            elif geom_type == "MultiLineString":
                # Flatten MultiLineString coordinates
                for line_coords in geom_input.get("coordinates", []):
                    raw_coords.extend(line_coords)
            else:
                raise ValueError(f"Unsupported GeoJSON geometry type: {geom_type}")
        elif isinstance(geom_input, (list, tuple)):
            raw_coords = geom_input
        elif isinstance(geom_input, LineString):
            raw_coords = list(geom_input.coords)
        else:
            raise ValueError(f"Unsupported geometry format: {type(geom_input).__name__}")

        if not raw_coords or len(raw_coords) < 2:
            raise ValueError(f"Route geometry must contain at least 2 points (got {len(raw_coords)})")

        diagnostics["original_point_count"] = len(raw_coords)

        # Validate finite values and enforce [lon, lat] ordering
        normalized_wgs84: List[Tuple[float, float]] = []
        for i, pt in enumerate(raw_coords):
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise ValueError(f"Invalid coordinate point at index {i}: {pt}")
            c0, c1 = float(pt[0]), float(pt[1])
            if not (math.isfinite(c0) and math.isfinite(c1)):
                raise ValueError(f"Non-finite coordinate value at index {i}: ({c0}, {c1})")

            # India coordinate sanity check: Longitude ~77-81 > Latitude ~10-14
            # If c0 < c1 (e.g. [13.08, 80.25]), it's latitude, longitude order
            if c0 < c1 and (10.0 <= c0 <= 15.0 and 75.0 <= c1 <= 85.0):
                lon, lat = c1, c0
                diagnostics["coordinate_swapped"] = True
            else:
                lon, lat = c0, c1

            normalized_wgs84.append((lon, lat))

        # Project coordinates into metric CRS (meters)
        lons = [p[0] for p in normalized_wgs84]
        lats = [p[1] for p in normalized_wgs84]
        mx, my = self.transformer.transform(lons, lats)
        metric_coords = list(zip(mx, my))

        metric_line = LineString(metric_coords)
        if metric_line.length <= 0.0:
            raise ValueError("Route geometry has 0.0 metric length (identical start and end points)")

        return metric_line, normalized_wgs84, diagnostics

    # --- Spatial Snapping Algorithm ---

    def match_route(
        self,
        route_input: Any,
        route_identifier: str = "route_0",
        travel_mode: str = "Road",
        leg_index: int = 0,
        distance_offset_m: float = 0.0,
    ) -> RouteSpatialMatchResponse:
        """
        Snaps a single continuous route geometry against the indexed road segments.
        """
        # Ensure spatial index covers route bounding box (bounded lazy loading)
        if self._index is None or getattr(self, "_indexed_bbox", None) is not None:
            try:
                coords = []
                if isinstance(route_input, dict) and "coordinates" in route_input:
                    coords = route_input["coordinates"]
                elif hasattr(route_input, "coords"):
                    coords = list(route_input.coords)
                elif isinstance(route_input, (list, tuple)):
                    coords = route_input
                if coords:
                    lons = [c[0] for c in coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    lats = [c[1] for c in coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    if lons and lats:
                        self._ensure_index_for_bbox(min(lons), min(lats), max(lons), max(lats))
            except Exception as e:
                logger.debug(f"Route-bounded index check: {e}")

        # Validate index (build lazily if data available)
        if (self._index is None or len(self._segment_records) == 0) and (self._road_segments_df is not None or self.road_segments_path.exists()):
            try:
                self.build_index()
            except Exception as e:
                logger.warning(f"Lazy index building failed: {e}")

        if self._index is None or len(self._segment_records) == 0:
            coverage = RouteCoverageMetrics(
                total_route_length_m=0.0,
                matched_length_m=0.0,
                unmatched_length_m=0.0,
                coverage_ratio=0.0,
                total_samples=0,
                matched_samples=0,
                unmatched_samples=0,
                ambiguous_samples=0,
            )
            return RouteSpatialMatchResponse(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                status="FAILED",
                coverage=coverage,
                matched_segments=[],
                unmatched_intervals=[],
                diagnostics={"error": "Spatial index is empty or not built"},
            )

        # Normalize and project geometry
        try:
            metric_line, wgs84_coords, geom_diag = self.normalize_route_geometry(route_input)
        except Exception as e:
            coverage = RouteCoverageMetrics(
                total_route_length_m=0.0,
                matched_length_m=0.0,
                unmatched_length_m=0.0,
                coverage_ratio=0.0,
                total_samples=0,
                matched_samples=0,
                unmatched_samples=0,
                ambiguous_samples=0,
            )
            return RouteSpatialMatchResponse(
                route_identifier=route_identifier,
                travel_mode=travel_mode,
                status="FAILED",
                coverage=coverage,
                matched_segments=[
                    MatchedSegmentResult(
                        traversal_index=0,
                        leg_index=leg_index,
                        match_status=MatchStatus.INVALID_GEOMETRY,
                        match_method="validation_check",
                        diagnostics={"error": str(e)},
                    )
                ],
                unmatched_intervals=[],
                diagnostics={"geometry_error": str(e)},
            )

        total_length_m = metric_line.length

        # Generate dense metric evaluation points along the route polyline
        sample_distances = np.arange(0.0, total_length_m, self.sample_interval_m).tolist()
        if not sample_distances or sample_distances[-1] < total_length_m:
            sample_distances.append(total_length_m)

        sample_points = [metric_line.interpolate(d) for d in sample_distances]
        total_samples = len(sample_points)

        sample_results: List[Dict[str, Any]] = []
        last_matched_way_id: Optional[int] = None

        for s_idx, (dist_along_m, pt) in enumerate(zip(sample_distances, sample_points)):
            # Spatial query: query nearest candidates within max_match_distance_m
            # Using query with buffer to catch parallel candidates for ambiguity audit
            buffer_geom = pt.buffer(self.max_match_distance_m)
            candidate_indices = self._index.query(buffer_geom)

            if len(candidate_indices) == 0:
                # No road within max_match_distance_m
                sample_results.append({
                    "sample_idx": s_idx,
                    "dist_along_m": dist_along_m,
                    "status": MatchStatus.UNMATCHED,
                    "segment_idx": None,
                    "distance_m": None,
                    "candidates": [],
                })
                continue

            # Compute metric distances to all candidates in buffer
            cand_distances = []
            for c_idx in candidate_indices:
                ref_geom = self._index_geoms[c_idx]
                d_m = pt.distance(ref_geom)
                cand_distances.append((c_idx, d_m))

            cand_distances.sort(key=lambda x: x[1])
            best_idx, best_dist = cand_distances[0]
            rec_best = self._segment_records[best_idx]

            # Ambiguity evaluation: check if runner-up candidate is within ambiguity_delta_m
            is_ambiguous = False
            ambig_cand_ids = []
            if len(cand_distances) > 1:
                second_idx, second_dist = cand_distances[1]
                rec_second = self._segment_records[second_idx]
                # Segments of the SAME way_id are adjacent parts of the same continuous road, not ambiguous parallel roads
                if (
                    rec_best["segment_id"] != rec_second["segment_id"]
                    and rec_best.get("way_id") != rec_second.get("way_id")
                ):
                    # If vehicle is continuing on its active way_id, an intersecting side street does not trigger false ambiguity
                    if (
                        last_matched_way_id is not None
                        and rec_best.get("way_id") == last_matched_way_id
                        and rec_second.get("way_id") != last_matched_way_id
                    ):
                        is_ambiguous = False
                    elif (second_dist - best_dist) <= self.ambiguity_delta_m:
                        is_ambiguous = True
                        ambig_cand_ids = [
                            rec_best["segment_id"],
                            rec_second["segment_id"],
                        ]

            if is_ambiguous:
                sample_results.append({
                    "sample_idx": s_idx,
                    "dist_along_m": dist_along_m,
                    "status": MatchStatus.AMBIGUOUS,
                    "segment_idx": best_idx,
                    "distance_m": round(best_dist, 2),
                    "candidates": ambig_cand_ids,
                })
            else:
                last_matched_way_id = rec_best.get("way_id")
                sample_results.append({
                    "sample_idx": s_idx,
                    "dist_along_m": dist_along_m,
                    "status": MatchStatus.MATCHED,
                    "segment_idx": best_idx,
                    "distance_m": round(best_dist, 2),
                    "candidates": [rec_best["segment_id"]],
                })

        # Compute sample interval weights for continuous metric coverage
        weights: List[float] = []
        for i in range(total_samples):
            if total_samples == 1:
                w = total_length_m
            elif i == 0:
                w = (sample_distances[1] - sample_distances[0]) / 2.0
            elif i == total_samples - 1:
                w = (sample_distances[-1] - sample_distances[-2]) / 2.0
            else:
                w = (sample_distances[i + 1] - sample_distances[i - 1]) / 2.0
            weights.append(w)

        # --- Traversal Sequencing, Deduplication, and Unmatched Interval Detection ---
        matched_segments: List[MatchedSegmentResult] = []
        unmatched_intervals: List[UnmatchedInterval] = []

        traversal_idx = 0
        current_matched_seg_id: Optional[str] = None
        current_matched_record: Optional[Dict[str, Any]] = None
        current_start_m = 0.0
        current_end_m = 0.0
        current_dists: List[float] = []
        current_weight = 0.0

        unmatched_start: Optional[float] = None
        unmatched_reason: Optional[str] = None

        matched_length_total = 0.0
        unmatched_length_total = 0.0

        matched_sample_count = sum(1 for s in sample_results if s["status"] == MatchStatus.MATCHED)
        unmatched_sample_count = sum(1 for s in sample_results if s["status"] == MatchStatus.UNMATCHED)
        ambiguous_sample_count = sum(1 for s in sample_results if s["status"] == MatchStatus.AMBIGUOUS)

        for s_idx, (s, w_i) in enumerate(zip(sample_results, weights)):
            s_dist = s["dist_along_m"]
            s_status = s["status"]

            if s_status == MatchStatus.MATCHED:
                matched_length_total += w_i
                seg_idx = s["segment_idx"]
                seg_meta = self._segment_records[seg_idx]
                seg_id = seg_meta["segment_id"]

                # If we were tracking an unmatched interval, close it
                if unmatched_start is not None:
                    u_len = s_dist - unmatched_start
                    if u_len > 0:
                        unmatched_intervals.append(
                            UnmatchedInterval(
                                start_distance_m=round(unmatched_start + distance_offset_m, 2),
                                end_distance_m=round(s_dist + distance_offset_m, 2),
                                length_m=round(u_len, 2),
                                reason=unmatched_reason or "UNMATCHED",
                                leg_index=leg_index,
                            )
                        )
                    unmatched_start = None
                    unmatched_reason = None

                if current_matched_seg_id == seg_id:
                    # Consecutive sample on same segment: extend interval
                    current_end_m = s_dist
                    current_dists.append(s["distance_m"])
                    current_weight += w_i
                else:
                    # Switched to a new segment: save previous segment if exists
                    if current_matched_seg_id is not None:
                        matched_segments.append(
                            MatchedSegmentResult(
                                traversal_index=traversal_idx,
                                leg_index=leg_index,
                                segment_id=current_matched_record["segment_id"],
                                way_id=current_matched_record["way_id"],
                                road_type=current_matched_record["road_type"],
                                match_status=MatchStatus.MATCHED,
                                match_method="strtree_metric_proximity",
                                match_distance_m=round(float(np.mean(current_dists)), 2),
                                route_start_m=round(current_start_m + distance_offset_m, 2),
                                route_end_m=round(current_end_m + distance_offset_m, 2),
                                ambiguity_candidates=[],
                                diagnostics={"sample_count": len(current_dists), "span_m": round(current_weight, 2)},
                            )
                        )
                        traversal_idx += 1

                    # Start new segment traversal
                    current_matched_seg_id = seg_id
                    current_matched_record = seg_meta
                    current_start_m = s_dist
                    current_end_m = s_dist
                    current_dists = [s["distance_m"]]
                    current_weight = w_i

            else:
                # UNMATCHED or AMBIGUOUS
                unmatched_length_total += w_i
                # Close ongoing matched segment if exists
                if current_matched_seg_id is not None:
                    matched_segments.append(
                        MatchedSegmentResult(
                            traversal_index=traversal_idx,
                            leg_index=leg_index,
                            segment_id=current_matched_record["segment_id"],
                            way_id=current_matched_record["way_id"],
                            road_type=current_matched_record["road_type"],
                            match_status=MatchStatus.MATCHED,
                            match_method="strtree_metric_proximity",
                            match_distance_m=round(float(np.mean(current_dists)), 2),
                            route_start_m=round(current_start_m + distance_offset_m, 2),
                            route_end_m=round(current_end_m + distance_offset_m, 2),
                            ambiguity_candidates=[],
                            diagnostics={"sample_count": len(current_dists), "span_m": round(current_weight, 2)},
                        )
                    )
                    traversal_idx += 1
                    current_matched_seg_id = None
                    current_matched_record = None
                    current_dists = []
                    current_weight = 0.0

                # If ambiguous, also record as an ambiguous segment in matched_segments for auditing
                if s_status == MatchStatus.AMBIGUOUS:
                    matched_segments.append(
                        MatchedSegmentResult(
                            traversal_index=traversal_idx,
                            leg_index=leg_index,
                            segment_id=None,
                            way_id=None,
                            road_type=None,
                            match_status=MatchStatus.AMBIGUOUS,
                            match_method="ambiguity_conflict_detection",
                            match_distance_m=s["distance_m"],
                            route_start_m=round(s_dist + distance_offset_m, 2),
                            route_end_m=round(s_dist + distance_offset_m, 2),
                            ambiguity_candidates=s["candidates"],
                            diagnostics={"candidates_within_tolerance": s["candidates"]},
                        )
                    )
                    traversal_idx += 1

                # Track unmatched interval
                if unmatched_start is None:
                    unmatched_start = s_dist
                    unmatched_reason = "AMBIGUOUS_CONFLICT" if s_status == MatchStatus.AMBIGUOUS else "NO_CANDIDATE_WITHIN_THRESHOLD"

        # Final flush for trailing matched segment or unmatched interval
        if current_matched_seg_id is not None:
            matched_segments.append(
                MatchedSegmentResult(
                    traversal_index=traversal_idx,
                    leg_index=leg_index,
                    segment_id=current_matched_record["segment_id"],
                    way_id=current_matched_record["way_id"],
                    road_type=current_matched_record["road_type"],
                    match_status=MatchStatus.MATCHED,
                    match_method="strtree_metric_proximity",
                    match_distance_m=round(float(np.mean(current_dists)), 2),
                    route_start_m=round(current_start_m + distance_offset_m, 2),
                    route_end_m=round(current_end_m + distance_offset_m, 2),
                    ambiguity_candidates=[],
                    diagnostics={"sample_count": len(current_dists), "span_m": round(current_weight, 2)},
                )
            )

        if unmatched_start is not None:
            u_len = total_length_m - unmatched_start
            if u_len > 0:
                unmatched_intervals.append(
                    UnmatchedInterval(
                        start_distance_m=round(unmatched_start + distance_offset_m, 2),
                        end_distance_m=round(total_length_m + distance_offset_m, 2),
                        length_m=round(u_len, 2),
                        reason=unmatched_reason or "UNMATCHED",
                        leg_index=leg_index,
                    )
                )

        # Coverage calculation: continuous and bounded
        matched_length_total = min(total_length_m, matched_length_total)
        unmatched_length_calc = max(0.0, total_length_m - matched_length_total)
        coverage_ratio = float(matched_length_total / total_length_m) if total_length_m > 0 else 0.0
        coverage_ratio = max(0.0, min(1.0, coverage_ratio))

        coverage = RouteCoverageMetrics(
            total_route_length_m=round(total_length_m, 2),
            matched_length_m=round(matched_length_total, 2),
            unmatched_length_m=round(unmatched_length_calc, 2),
            coverage_ratio=round(coverage_ratio, 4),
            total_samples=total_samples,
            matched_samples=matched_sample_count,
            unmatched_samples=unmatched_sample_count,
            ambiguous_samples=ambiguous_sample_count,
        )

        # Bridge feature table
        self.bridge_features(matched_segments)

        overall_status = "SUCCESS" if coverage_ratio >= 0.80 else "PARTIAL" if coverage_ratio > 0.0 else "FAILED"

        return RouteSpatialMatchResponse(
            route_identifier=route_identifier,
            travel_mode=travel_mode,
            status=overall_status,
            coverage=coverage,
            matched_segments=matched_segments,
            unmatched_intervals=unmatched_intervals,
            diagnostics={
                **geom_diag,
                "projected_crs": self.projected_crs,
                "max_match_distance_m": self.max_match_distance_m,
                "sample_interval_m": self.sample_interval_m,
            },
        )

    # --- Multimodal Support ---

    def match_multimodal_route(
        self,
        legs: List[Dict[str, Any]],
        route_identifier: str = "multimodal_0",
    ) -> RouteSpatialMatchResponse:
        """
        Processes a multi-leg route (e.g. walk -> transit -> walk), combining all legs in traversal sequence.
        """
        # Ensure spatial index covers global multimodal bounding box
        if self._index is None or getattr(self, "_indexed_bbox", None) is not None:
            try:
                all_coords = []
                for leg in legs:
                    leg_geom = leg.get("geometry")
                    if isinstance(leg_geom, dict) and "coordinates" in leg_geom:
                        all_coords.extend(leg_geom["coordinates"])
                    elif isinstance(leg_geom, (list, tuple)):
                        all_coords.extend(leg_geom)
                if all_coords:
                    lons = [c[0] for c in all_coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    lats = [c[1] for c in all_coords if isinstance(c, (list, tuple)) and len(c) >= 2]
                    if lons and lats:
                        self._ensure_index_for_bbox(min(lons), min(lats), max(lons), max(lats))
            except Exception as e:
                logger.debug(f"Multimodal route-bounded index check: {e}")

        all_matched_segments: List[MatchedSegmentResult] = []
        all_unmatched_intervals: List[UnmatchedInterval] = []

        total_route_length_m = 0.0
        matched_length_m = 0.0
        unmatched_length_m = 0.0
        total_samples = 0
        matched_samples = 0
        unmatched_samples = 0
        ambiguous_samples = 0

        distance_offset = 0.0
        global_traversal_idx = 0

        for leg_idx, leg in enumerate(legs):
            leg_mode = leg.get("mode", f"Leg_{leg_idx}")
            leg_geom = leg.get("geometry")
            if not leg_geom:
                continue

            leg_res = self.match_route(
                route_input=leg_geom,
                route_identifier=f"{route_identifier}_leg_{leg_idx}",
                travel_mode=leg_mode,
                leg_index=leg_idx,
                distance_offset_m=distance_offset,
            )

            # Re-index traversal_index continuously across legs
            for seg in leg_res.matched_segments:
                seg.traversal_index = global_traversal_idx
                global_traversal_idx += 1
                all_matched_segments.append(seg)

            all_unmatched_intervals.extend(leg_res.unmatched_intervals)

            total_route_length_m += leg_res.coverage.total_route_length_m
            matched_length_m += leg_res.coverage.matched_length_m
            unmatched_length_m += leg_res.coverage.unmatched_length_m
            total_samples += leg_res.coverage.total_samples
            matched_samples += leg_res.coverage.matched_samples
            unmatched_samples += leg_res.coverage.unmatched_samples
            ambiguous_samples += leg_res.coverage.ambiguous_samples

            distance_offset += leg_res.coverage.total_route_length_m

        coverage_ratio = float(matched_length_m / total_route_length_m) if total_route_length_m > 0 else 0.0
        coverage = RouteCoverageMetrics(
            total_route_length_m=round(total_route_length_m, 2),
            matched_length_m=round(matched_length_m, 2),
            unmatched_length_m=round(unmatched_length_m, 2),
            coverage_ratio=round(coverage_ratio, 4),
            total_samples=total_samples,
            matched_samples=matched_samples,
            unmatched_samples=unmatched_samples,
            ambiguous_samples=ambiguous_samples,
        )

        overall_status = "SUCCESS" if coverage_ratio >= 0.80 else "PARTIAL" if coverage_ratio > 0.0 else "FAILED"

        return RouteSpatialMatchResponse(
            route_identifier=route_identifier,
            travel_mode="Multimodal",
            status=overall_status,
            coverage=coverage,
            matched_segments=all_matched_segments,
            unmatched_intervals=all_unmatched_intervals,
            diagnostics={"legs_processed": len(legs)},
        )

    # --- Feature Bridge ---

    def bridge_features(self, matched_segments: List[MatchedSegmentResult]) -> None:
        """
        Enriches matched segments with their authoritative 41 canonical predictor features.
        Uses memory-bounded pyarrow dataset row-level querying on disk to prevent loading
        the full multi-hundred-megabyte master feature table into memory.
        """
        needed_ids = [s.segment_id for s in matched_segments if s.segment_id and s.segment_id not in self._feature_cache]
        if needed_ids:
            if self._feature_table_df is not None and len(self._feature_table_df) > 0:
                mft = self._feature_table_df
                missing_table_cols = [c for c in CANONICAL_PREDICTOR_FEATURES if c not in mft.columns]
                if missing_table_cols:
                    for seg in matched_segments:
                        seg.feature_status = FeatureStatus.INCOMPLETE
                        seg.diagnostics["missing_features"] = missing_table_cols
                    return
                subset = mft[mft["segment_id"].isin(needed_ids)]
            elif self.master_feature_path.exists():
                import pyarrow.dataset as ds
                dataset = ds.dataset(str(self.master_feature_path), format="parquet")
                schema_cols = set(dataset.schema.names)
                missing_table_cols = [c for c in CANONICAL_PREDICTOR_FEATURES if c not in schema_cols]
                if missing_table_cols:
                    for seg in matched_segments:
                        seg.feature_status = FeatureStatus.INCOMPLETE
                        seg.diagnostics["missing_features"] = missing_table_cols
                    return
                cols = ["segment_id"] + [c for c in CANONICAL_PREDICTOR_FEATURES]
                filter_expr = ds.field("segment_id").isin(needed_ids)
                sub_table = dataset.to_table(filter=filter_expr, columns=[c for c in cols if c in schema_cols])
                subset = sub_table.to_pandas()
            else:
                for seg in matched_segments:
                    seg.feature_status = FeatureStatus.MISSING_ROW
                return

            for _, row in subset.iterrows():
                sid = str(row["segment_id"])
                row_dict = {}
                for col in CANONICAL_PREDICTOR_FEATURES:
                    if col in row:
                        val = row[col]
                        if col in NUMERICAL_FEATURES:
                            row_dict[col] = float(val) if pd.notna(val) else np.nan
                        else:
                            row_dict[col] = str(val) if pd.notna(val) else "unknown"
                self._feature_cache[sid] = row_dict

        for seg in matched_segments:
            if seg.match_status != MatchStatus.MATCHED or not seg.segment_id:
                seg.feature_status = FeatureStatus.NOT_APPLICABLE
                continue

            if seg.segment_id not in self._feature_cache:
                seg.feature_status = FeatureStatus.MISSING_ROW
                seg.diagnostics["feature_error"] = f"segment_id '{seg.segment_id}' not found in master feature table"
                continue

            feat_row = self._feature_cache[seg.segment_id]

            # Validate completeness
            missing_cols = [c for c in CANONICAL_PREDICTOR_FEATURES if c not in feat_row]
            if missing_cols:
                seg.feature_status = FeatureStatus.INCOMPLETE
                seg.diagnostics["missing_features"] = missing_cols
                continue

            # Validate numerical values are finite
            invalid_num_cols = []
            for col in NUMERICAL_FEATURES:
                val = feat_row.get(col)
                if val is None or not math.isfinite(val):
                    invalid_num_cols.append(col)

            if invalid_num_cols:
                seg.feature_status = FeatureStatus.INVALID_VALUES
                seg.diagnostics["non_finite_features"] = invalid_num_cols
                continue

            # Perfectly valid canonical record
            seg.feature_status = FeatureStatus.AVAILABLE
            seg.canonical_features = {c: feat_row[c] for c in CANONICAL_PREDICTOR_FEATURES}

    # --- Candidate Route Integration Boundary ---

    def enrich_candidate_route(self, candidate_route: Any) -> Any:
        """
        Enriches a CandidateRoute's metadata with spatial match results without modifying safety_score.
        Designed as the internal boundary for the Journey Coordinator.
        """
        route_meta = getattr(candidate_route, "route_metadata", {}) or {}

        # Check for multimodal dynamic_segments
        dynamic_segs = route_meta.get("dynamic_segments")
        if dynamic_segs and isinstance(dynamic_segs, list):
            res = self.match_multimodal_route(dynamic_segs, getattr(candidate_route, "route_identifier", "route"))
        else:
            geom = route_meta.get("geometry")
            res = self.match_route(geom, getattr(candidate_route, "route_identifier", "route"), route_meta.get("travel_mode", "Road"))

        route_meta["spatial_match"] = res.model_dump()
        candidate_route.route_metadata = route_meta
        return candidate_route
