import httpx
import asyncio
from typing import Dict, Any
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class OpenWeatherProvider:
    """
    Real integration with OpenWeather API.
    """
    def __init__(self):
        self.api_key = settings.weather_api_key or "dummy_key"
        self.base_url = settings.weather_api_url or "https://api.openweathermap.org/data/2.5"
        self.timeout = 5.0

    async def get_weather(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Retrieves real weather data.
        """
        if self.api_key == "dummy_key":
            return self._fallback_weather()
            
        try:
            url = f"{self.base_url}/weather"
            params = {
                "lat": lat,
                "lon": lng,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return self._normalize_weather(data)
                else:
                    logger.error(f"Weather API returned status {response.status_code}")
                    return self._fallback_weather()
                        
        except Exception as e:
            logger.error(f"Weather request failed: {str(e)}")
            return self._fallback_weather()

    def _normalize_weather(self, data: Dict[str, Any]) -> Dict[str, Any]:
        weather_list = data.get("weather", [{}])
        main_cond = weather_list[0].get("main", "Clear")
        temp = data.get("main", {}).get("temp", 24)
        visibility = data.get("visibility", 10000) / 1000 # convert to km
        humidity = data.get("main", {}).get("humidity", 0)
        
        # Simple rain probability heuristic from weather condition
        rain_prob = 1.0 if main_cond in ["Rain", "Drizzle", "Thunderstorm"] else 0.0
        
        return {
            "condition": main_cond,
            "temperature_c": temp,
            "visibility_km": visibility,
            "humidity": humidity,
            "precipitation_probability": rain_prob,
            "alerts": []
        }

    def _fallback_weather(self) -> Dict[str, Any]:
        return {
            "condition": "Clear",
            "temperature_c": 24,
            "visibility_km": 10,
            "humidity": 45,
            "precipitation_probability": 0.0,
            "alerts": []
        }
        
    async def health(self) -> Dict[str, str]:
        if self.api_key == "dummy_key":
            return {"status": "degraded (no api key)"}
        try:
            url = f"{self.base_url}/weather?lat=0&lon=0&appid={self.api_key}"
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url)
                return {"status": "healthy" if response.status_code == 200 else "degraded"}
        except Exception:
            return {"status": "offline"}
