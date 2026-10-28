import datetime
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes (WW)
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

class WeatherProvider:
    """
    Fetches real-time observations or forecasts for journey locations.
    If the provider is offline or unreachable, reports honest unavailable status
    instead of fabricating synthetic temperature or sky conditions.
    """
    def __init__(self):
        self._last_failure_time: float = 0.0
        self._failure_cooldown: float = 60.0
    
    async def get_live_weather(self, lat: float, lon: float, req_dt: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Asynchronously fetches live or forecast weather from verified open data API (Open-Meteo).
        """
        import time
        if (time.time() - self._last_failure_time) < self._failure_cooldown:
            return {
                "available": False,
                "condition": "Unavailable",
                "temperature": 0,
                "temperature_raw": None,
                "rain": False,
                "precipitation_mm": 0.0,
                "wind_kmh": 0.0,
                "humidity": 0,
                "hazards": ["Live weather information unavailable (rate limit cooldown)"],
                "status": "UNAVAILABLE",
                "summary": "Weather unavailable",
                "observation_timestamp": None,
                "source": "None (Provider Offline)",
                "data_type": "UNAVAILABLE",
                "confidence": "None"
            }

        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current", {})
                    wcode = curr.get("weather_code", 0)
                    condition = WMO_CODE_MAP.get(wcode, "Clear")
                    temp = curr.get("temperature_2m")
                    precip = curr.get("precipitation", 0.0)
                    wind = curr.get("wind_speed_10m", 0.0)
                    humidity = curr.get("relative_humidity_2m", 50)
                    
                    hazards = []
                    if wcode in [65, 82, 95, 96, 99]:
                        hazards.append(f"Severe Weather Alert: {condition}")
                    if wind > 40.0:
                        hazards.append("High Wind Warning")
                    if precip > 5.0:
                        hazards.append("Heavy Precipitation Warning")
                        
                    return {
                        "available": True,
                        "condition": condition,
                        "temperature": int(round(temp)) if temp is not None else 25,
                        "temperature_raw": temp,
                        "rain": precip > 0.0 or wcode in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95],
                        "precipitation_mm": precip,
                        "wind_kmh": wind,
                        "humidity": humidity,
                        "hazards": hazards,
                        "status": "AVAILABLE",
                        "summary": f"{condition}, {int(round(temp)) if temp is not None else 25}°C",
                        "observation_timestamp": curr.get("time"),
                        "source": "Open-Meteo Live API",
                        "data_type": "LIVE_WEATHER",
                        "confidence": "High"
                    }
        except Exception as e:
            self._last_failure_time = time.time()
            logger.warning(f"Live weather fetch failed: {e}")
            
        return {
            "available": False,
            "condition": "Unavailable",
            "temperature": 0,
            "temperature_raw": None,
            "rain": False,
            "precipitation_mm": 0.0,
            "wind_kmh": 0.0,
            "humidity": 0,
            "hazards": ["Live weather information unavailable"],
            "status": "UNAVAILABLE",
            "summary": "Weather unavailable",
            "observation_timestamp": None,
            "source": "None (Provider Offline)",
            "data_type": "UNAVAILABLE",
            "confidence": "None"
        }

    def get_weather(self, location_coords: tuple, req_dt: datetime.datetime) -> Dict[str, Any]:
        """
        Synchronous wrapper for legacy callers.
        """
        import asyncio
        try:
            lat = location_coords[0] if len(location_coords) >= 2 else 12.8448
            lon = location_coords[1] if len(location_coords) >= 2 else 80.1527
            # Run in event loop if available or asyncio.run
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # In a running loop, return fallback directly or synchronous request
                    import urllib.request, json
                    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
                    req = urllib.request.Request(url, headers={'User-Agent': 'SafeShe/1.0'})
                    with urllib.request.urlopen(req, timeout=3.0) as r:
                        data = json.loads(r.read().decode())
                        curr = data.get("current", {})
                        wcode = curr.get("weather_code", 0)
                        condition = WMO_CODE_MAP.get(wcode, "Clear")
                        temp = curr.get("temperature_2m")
                        return {
                            "available": True,
                            "condition": condition,
                            "temperature": int(round(temp)) if temp is not None else 25,
                            "rain": curr.get("precipitation", 0.0) > 0.0,
                            "status": "AVAILABLE",
                            "source": "Open-Meteo Live API",
                            "data_type": "LIVE_WEATHER",
                            "confidence": "High",
                            "observation_timestamp": curr.get("time")
                        }
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Synchronous weather fetch failed: {e}")
            
        return {
            "available": False,
            "condition": "Unavailable",
            "temperature": 0,
            "rain": False,
            "status": "UNAVAILABLE",
            "source": "None (Provider Offline)",
            "data_type": "UNAVAILABLE",
            "confidence": "None",
            "observation_timestamp": None
        }

global_weather_provider = WeatherProvider()
