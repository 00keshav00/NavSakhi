import logging
from typing import List, Any
import math

logger = logging.getLogger(__name__)

ROUTE_DEDUP_JACCARD_THRESHOLD = 0.85
ROUTE_DEDUP_OVERLAP_THRESHOLD = 0.85

def _round_coord(c, precision=4):
    """
    Rounds coordinates to a specific decimal precision.
    4 decimal places is roughly 11 meters at the equator.
    """
    return (round(c[0], precision), round(c[1], precision))

def get_normalized_cells(coordinates: List[List[float]], precision=4) -> set:
    """
    Converts a geometry array into a set of normalized spatial cells.
    """
    cells = set()
    for c in coordinates:
        cells.add(_round_coord(c, precision))
    return cells

def calculate_jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Calculates Jaccard similarity between two sets of spatial cells.
    |A ∩ B| / |A ∪ B|
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union

def calculate_asymmetric_overlap(reference_set: set, other_set: set) -> float:
    """
    Calculates what percentage of the reference_set is contained within other_set.
    |Ref ∩ Other| / |Ref|
    """
    if not reference_set:
        return 0.0
    intersection = len(reference_set.intersection(other_set))
    return intersection / len(reference_set)

def _get_mode_category(cand: Any) -> str:
    """Extract a normalized transport mode category from CandidateRoute or dict."""
    mode = ""
    route_name = ""
    if hasattr(cand, "route_metadata") and isinstance(cand.route_metadata, dict):
        mode = cand.route_metadata.get("travel_mode", "") or cand.route_metadata.get("mode", "")
        route_name = cand.route_metadata.get("route_name", "")
        dyn_segs = cand.route_metadata.get("dynamic_segments", [])
        for s in dyn_segs:
            s_m = s.get("mode", "").lower()
            if "bus" in s_m: return "bus"
            if "metro" in s_m: return "metro"
            if "suburban" in s_m or "rail" in s_m or "train" in s_m: return "suburban"
            if "mrts" in s_m: return "mrts"
    if not mode and hasattr(cand, "mode"):
        mode = getattr(cand, "mode", "")
    full_str = f"{mode} {route_name}".lower().strip().replace("-", "_").replace(" ", "_")
    if any(k in full_str for k in ["walk", "foot", "pedestrian"]):
        return "walking"
    if any(k in full_str for k in ["bike", "bicycle", "two_wheeler", "scooter", "motorcycle"]):
        return "two_wheeler"
    if any(k in full_str for k in ["bus"]):
        return "bus"
    if any(k in full_str for k in ["metro"]):
        return "metro"
    if any(k in full_str for k in ["suburban", "rail", "train"]):
        return "suburban"
    if any(k in full_str for k in ["mrts"]):
        return "mrts"
    if any(k in full_str for k in ["multimodal", "transit"]):
        return "transit"
    if any(k in full_str for k in ["cab", "taxi"]):
        return "cab"
    return "driving"

def deduplicate_routes(candidates: List[Any], 
                       jaccard_threshold=ROUTE_DEDUP_JACCARD_THRESHOLD,
                       overlap_threshold=ROUTE_DEDUP_OVERLAP_THRESHOLD) -> List[Any]:
    """
    Filters out near-duplicate routes using mode-aware spatial normalization and overlap metrics.
    Routes with genuinely different transport modes (e.g. Walking vs Two Wheeler vs Driving vs Transit)
    are preserved as distinct mobility choices. Within the same mode, routes are only considered duplicates
    if both their spatial overlap exceeds thresholds and their durations/distances closely match.
    """
    if not candidates:
        return []
        
    distinct_routes = []
    
    for cand in candidates:
        cand_mode = _get_mode_category(cand)
        cand_dist = getattr(cand, "distance", 0.0) or 0.0
        cand_dur = getattr(cand, "duration", 0.0) or 0.0

        # Extract coordinates. Assumes CandidateRoute has geometry or coordinates accessible.
        coords = []
        if hasattr(cand, "geometry") and cand.geometry:
            if isinstance(cand.geometry, dict) and "coordinates" in cand.geometry:
                coords = cand.geometry["coordinates"]
            elif isinstance(cand.geometry, list):
                coords = cand.geometry
        elif hasattr(cand, "route_metadata") and isinstance(cand.route_metadata, dict) and "geometry" in cand.route_metadata:
            geom = cand.route_metadata["geometry"]
            if isinstance(geom, dict):
                coords = geom.get("coordinates", [])
            elif isinstance(geom, list):
                coords = geom
            
        if not coords:
            # If we can't extract geometry, we keep it safely.
            if hasattr(cand, "route_metadata") and isinstance(cand.route_metadata, dict):
                cand.route_metadata["distinctness_status"] = "DISTINCT"
                cand.route_metadata["overlap_metrics"] = {"jaccard": 0.0, "reason": "NO_GEOMETRY"}
            else:
                try:
                    setattr(cand, "distinctness_status", "DISTINCT")
                    setattr(cand, "overlap_metrics", {"jaccard": 0.0, "reason": "NO_GEOMETRY"})
                except Exception:
                    pass
            distinct_routes.append(cand)
            continue
            
        cells = get_normalized_cells(coords, precision=3) # ~110m precision for robust highway overlap
        
        is_duplicate = False
        duplicate_reason = None
        max_jaccard = 0.0
        
        for accepted in distinct_routes:
            accepted_mode = _get_mode_category(accepted)
            
            # Different travel modes represent fundamentally different journey options for the user
            if cand_mode != accepted_mode:
                continue
                
            accepted_cells = getattr(accepted, "_normalized_cells", set())
            
            jaccard = calculate_jaccard_similarity(cells, accepted_cells)
            max_jaccard = max(max_jaccard, jaccard)
            
            overlap_of_cand = calculate_asymmetric_overlap(cells, accepted_cells)

            # Within the same mode, check duration & distance similarity
            accepted_dur = getattr(accepted, "duration", 0.0) or 0.0
            accepted_dist = getattr(accepted, "distance", 0.0) or 0.0
            dur_diff_ratio = abs(cand_dur - accepted_dur) / max(accepted_dur, 1.0)
            dist_diff_ratio = abs(cand_dist - accepted_dist) / max(accepted_dist, 1.0)
            
            # Only consider duplicate if spatial overlap is high AND duration/distance are nearly identical
            if (jaccard > jaccard_threshold or overlap_of_cand > overlap_threshold) and (dur_diff_ratio < 0.15 and dist_diff_ratio < 0.15):
                is_duplicate = True
                duplicate_reason = f"Mode '{cand_mode}' duplicate: Jaccard {jaccard:.2f}, Overlap {overlap_of_cand:.2f}, DurDiff {dur_diff_ratio:.2f}"
                break
                
        if not is_duplicate:
            setattr(cand, "_normalized_cells", cells)
            if not hasattr(cand, "route_metadata"):
                cand.route_metadata = {}
            cand.route_metadata["distinctness_status"] = "DISTINCT"
            cand.route_metadata["overlap_metrics"] = {"max_jaccard_with_accepted": max_jaccard}
            distinct_routes.append(cand)
        else:
            logger.info(f"Filtered duplicate route. Reason: {duplicate_reason}")
            
    # Clean up temporary attribute
    for cand in distinct_routes:
        if hasattr(cand, "_normalized_cells"):
            delattr(cand, "_normalized_cells")
            
    return distinct_routes
