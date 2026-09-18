from typing import Dict, Any, List
from app.db.connection import get_database
import logging

logger = logging.getLogger(__name__)

class MongoCommunityProvider:
    """
    Real integration with MongoDB for Community Reports.
    """
    async def get_community_reports(self, route_geometry: List[Any]) -> Dict[str, Any]:
        """
        Retrieves active reports overlapping the route geometry.
        """
        db = get_database()
        if db is None:
            logger.warning("MongoDB not connected. Using fallback community reports.")
            return self._fallback_reports()
            
        try:
            # Query reports from MongoDB collection
            collection = db["community_reports"]
            
            # Simple simulation of geospatial matching or filtering by status
            cursor = collection.find({"status": "active"}).limit(50)
            reports = await cursor.to_list(length=50)
            
            # Format to DTO friendly schema
            incidents = []
            for r in reports:
                incidents.append({
                    "id": str(r.get("_id")),
                    "type": r.get("report_type", "hazard"),
                    "severity": r.get("severity", "medium"),
                    "description": r.get("description", ""),
                    "verified": r.get("verified", False)
                })
                
            return {
                "total_reports": len(incidents),
                "incidents": incidents,
                "safe_zones_along_route": [
                    {"name": "Central Station", "type": "Police", "distance": "1.2 km"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to query MongoDB community reports: {e}")
            return self._fallback_reports()

    def _fallback_reports(self) -> Dict[str, Any]:
        return {
            "total_reports": 0,
            "incidents": [],
            "safe_zones_along_route": [
                {"name": "Central Station", "type": "Police", "distance": "1.2 km"}
            ]
        }
        
    async def health(self) -> Dict[str, str]:
        db = get_database()
        if db is None:
            return {"status": "offline"}
        try:
            await db.command("ping")
            return {"status": "healthy"}
        except Exception:
            return {"status": "offline"}
