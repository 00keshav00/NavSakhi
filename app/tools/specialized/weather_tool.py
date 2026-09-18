from typing import Dict, Any
from app.tools.base import BaseTool, ToolMetadata
from app.tools.weather import WeatherTool as CoreWeatherTool

class WeatherTool(BaseTool):
    @property
    def name(self) -> str:
        return "SpecializedWeatherTool"

    @property
    def description(self) -> str:
        return "Specialized tool for weather data."

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            capability="Weather",
            required_inputs=["location"],
            output_schema={"type": "dict"}
        )

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = CoreWeatherTool()
        return await tool.execute(params)
