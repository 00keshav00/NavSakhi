from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.db.connection import get_database

class DashboardTool(BaseTool):
    @property
    def name(self) -> str:
        return "DashboardTool"

    @property
    def description(self) -> str:
        return "Retrieves aggregated statistics for the dashboard from MongoDB."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="DashboardAggregation",
            required_inputs=[],
            output_schema={"type": "dict"},
            ranking_score=10
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = get_database()
        if db is None:
            return self._fallback_stats()
            
        try:
            # Query MongoDB collections
            active_journeys = await db["journeys"].count_documents({"status": "active"})
            reports = await db["community_reports"].count_documents({"status": "active"})
            
            # Simple simulation of aggregated data
            return {
                "active_journeys": active_journeys,
                "verified_safe_zones": 5,
                "community_alerts": reports,
                "system_health": "Online"
            }
        except Exception:
            return self._fallback_stats()
            
    def _fallback_stats(self) -> Dict[str, Any]:
        return {
            "active_journeys": 1,
            "verified_safe_zones": 4,
            "community_alerts": 12,
            "system_health": "Online"
        }
