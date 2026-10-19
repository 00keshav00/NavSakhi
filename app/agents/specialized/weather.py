from typing import Dict, Any
from app.agents.specialized.base import BaseSpecializedAgent
from app.tools.specialized.weather_tool import WeatherTool

class WeatherAgent(BaseSpecializedAgent):
    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        tool = WeatherTool()
        return await tool.execute({
            "location": context.get("destination") or context.get("source")
        })
