from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.emergency_tool import EmergencyTool
from app.tools.specialized.location_tool import LocationTool

class EmergencyAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        loc_tool = LocationTool()
        loc = await loc_tool.execute({"user_id": context.get("user_id")})
        
        em_tool = EmergencyTool()
        res = await em_tool.execute({"user_id": context.get("user_id"), "location": loc})
        
        return {
            "emergency_status": res,
            "location": loc
        }
