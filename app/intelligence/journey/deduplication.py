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

def deduplicate_routes(candidates: List[Any], 
                       jaccard_threshold=ROUTE_DEDUP_JACCARD_THRESHOLD,
                       overlap_threshold=ROUTE_DEDUP_OVERLAP_THRESHOLD) -> List[Any]:
    """
    Filters out near-duplicate routes using spatial normalization and overlap metrics.
    Retains the first encountered route among duplicates (assumed to be ranked higher by OSRM).
    """
    if not candidates:
        return []
        
    distinct_routes = []
    
    for cand in candidates:
        # Extract coordinates. Assumes CandidateRoute has geometry or coordinates accessible.
        coords = []
        if hasattr(cand, "geometry") and cand.geometry and "coordinates" in cand.geometry:
            coords = cand.geometry["coordinates"]
        elif hasattr(cand, "route_metadata") and "geometry" in cand.route_metadata:
            coords = cand.route_metadata["geometry"].get("coordinates", [])
            
        if not coords:
            # If we can't extract geometry, we keep it safely.
            cand.distinctness_status = "DISTINCT"
            cand.overlap_metrics = {"jaccard": 0.0, "reason": "NO_GEOMETRY"}
            distinct_routes.append(cand)
            continue
            
        cells = get_normalized_cells(coords, precision=3) # ~110m precision for robust highway overlap
        
        is_duplicate = False
        duplicate_reason = None
        max_jaccard = 0.0
        
        for accepted in distinct_routes:
            accepted_cells = getattr(accepted, "_normalized_cells", set())
            
            jaccard = calculate_jaccard_similarity(cells, accepted_cells)
            max_jaccard = max(max_jaccard, jaccard)
            
            overlap_of_cand = calculate_asymmetric_overlap(cells, accepted_cells)
            
            if jaccard > jaccard_threshold or overlap_of_cand > overlap_threshold:
                is_duplicate = True
                duplicate_reason = f"Jaccard {jaccard:.2f}, Overlap {overlap_of_cand:.2f}"
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
