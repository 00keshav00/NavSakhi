import datetime
from typing import Dict, Any, Optional

class WeatherProvider:
    def get_weather(self, location_coords: tuple, req_dt: datetime.datetime) -> Dict[str, Any]:
        """
        Returns weather (observed or forecasted) based on req_dt.
        """
        now = datetime.datetime.now()
        is_future = req_dt > now + datetime.timedelta(hours=1)
        
        # In a real implementation, we would query OpenWeatherMap / IMD API
        # with 'current' or 'forecast' depending on is_future.
        # Since we must NOT use current weather for future trips, we simulate
        # the distinction here as an abstraction.
        
        data = {
            "temperature": 28.5 if not is_future else 26.0,
            "rain": False,
            "wind": 15.0,
            "visibility": 10000,
            "storm_warning": False,
            "observation_timestamp": now.isoformat() if not is_future else None,
            "forecast_timestamp": req_dt.isoformat() if is_future else None,
            "source": "Mocked OpenWeather / IMD Abstraction",
            "freshness_seconds": 0,
            "data_type": "LIVE_WEATHER" if not is_future else "FORECAST_WEATHER",
            "confidence": "High"
        }
        
        return data

global_weather_provider = WeatherProvider()
