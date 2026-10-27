from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.tools.specialized.poi_tool import POITool

class AssistantAgent(BaseSpecializedAgent):
    def __init__(self):
        super().__init__()
        self.poi_tool = POITool()

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        query = context.get("query")
        poi_data = None
        query_str = str(query or "").lower()
        poi_keywords = [
            "shop", "store", "pharmaci", "pharmacy", "medical", "chemist", "medicine",
            "hospital", "clinic", "supermarket", "grocery", "cafe", "coffee",
            "restaurant", "atm", "bank", "food", "fuel", "police", "facility", "facilities"
        ]
        if query_str and any(kw in query_str for kw in poi_keywords):
            inferred_cat = context.get("category")
            if not inferred_cat:
                if any(k in query_str for k in ["pharmaci", "pharmacy", "chemist", "medicin"]):
                    inferred_cat = "pharmacy"
                elif any(k in query_str for k in ["hospital", "emergency"]):
                    inferred_cat = "hospital"
                elif any(k in query_str for k in ["clinic", "doctor"]):
                    inferred_cat = "clinic"
                elif any(k in query_str for k in ["police", "cop"]):
                    inferred_cat = "police"
                elif any(k in query_str for k in ["cafe", "coffee", "tea"]):
                    inferred_cat = "cafe"
                elif any(k in query_str for k in ["restaurant", "food", "dine"]):
                    inferred_cat = "restaurant"
                elif any(k in query_str for k in ["atm", "bank"]):
                    inferred_cat = "bank_atm"

            try:
                poi_data = await self.poi_tool.execute({
                    "place": context.get("place") or context.get("location_name"),
                    "category": inferred_cat,
                    "lon": context.get("lon"),
                    "lat": context.get("lat")
                })
            except Exception:
                poi_data = None

        return {
            "status": "READY",
            "query": query,
            "agent": "AssistantAgent",
            "poi_data": poi_data
        }
