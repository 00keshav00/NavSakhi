from pydantic import BaseModel
from typing import List, Dict, Any

class VendorRouteGeometry(BaseModel):
    coordinates: List[List[float]]
    type: str = "LineString"

class VendorRouteResponse(BaseModel):
    """Raw vendor response model (e.g. OSRM structure)"""
    code: str
    routes: List[Dict[str, Any]]
    waypoints: List[Dict[str, Any]]
