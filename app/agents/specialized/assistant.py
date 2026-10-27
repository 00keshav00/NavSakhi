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
        if query and any(kw in str(query).lower() for kw in ["shop", "store", "pharmacy", "hospital", "clinic", "supermarket", "cafe", "restaurant", "atm"]):
            try:
                poi_data = await self.poi_tool.execute({
                    "place": context.get("place") or context.get("location_name"),
                    "category": context.get("category"),
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
