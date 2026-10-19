from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "WeatherTool"

    @property
    def description(self) -> str:
        return "Retrieves current and forecasted weather for a location."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Weather",
            required_inputs=["lat", "lng"],
            output_schema={"type": "dict", "properties": {"condition": "string", "temp": "float"}},
            ranking_score=8
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects: 'lat', 'lng'
        """
        from app.providers.real.weather import OpenWeatherProvider
        provider = OpenWeatherProvider()
        return await provider.get_weather(
            lat=params.get("lat", 0.0),
            lng=params.get("lng", 0.0)
        )
