"""
SafeShe Real Weather Service
Integrates Open-Meteo open API (https://open-meteo.com) and OSM Nominatim reverse geocoding
to provide authentic, data-driven observations, hourly forecasts, and UV indicators.
"""

import time
import datetime
import logging
from typing import Dict, Any, Optional, Tuple, List
import httpx

from app.schemas.weather_schemas import (
    LiveWeatherResponse,
    HourlyForecastItem,
    DailyForecastItem,
    ReverseGeocodeResponse
)

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes (WW) to condition text and icon key
WMO_INTERPRETATION = {
    0: ("Clear sky", "sun"),
    1: ("Mainly clear", "sun"),
    2: ("Partly cloudy", "partly-cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Foggy", "fog"),
    48: ("Depositing rime fog", "fog"),
    51: ("Light drizzle", "drizzle"),
    53: ("Moderate drizzle", "drizzle"),
    55: ("Dense drizzle", "drizzle"),
    61: ("Slight rain", "rain"),
    63: ("Moderate rain", "rain"),
    65: ("Heavy rain", "heavy-rain"),
    71: ("Slight snow", "snow"),
    73: ("Moderate snow", "snow"),
    75: ("Heavy snow", "snow"),
    80: ("Slight rain showers", "rain"),
    81: ("Moderate rain showers", "rain"),
    82: ("Violent rain showers", "heavy-rain"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with hail", "thunderstorm"),
    99: ("Severe thunderstorm with heavy hail", "thunderstorm"),
}


class WeatherService:
    """Provides verified weather observations and reverse geocoding."""

    def __init__(self, time_func=None):
        self._weather_cache: Dict[Tuple[float, float], Tuple[float, LiveWeatherResponse]] = {}
        self._geocode_cache: Dict[Tuple[float, float], Tuple[float, ReverseGeocodeResponse]] = {}
        self._weather_cache_ttl = 900  # 15 minutes (positive cache)
        self._negative_cache_ttl = 30  # 30 seconds (negative cache / transient failure cooldown)
        self._rate_limit_cooldown = 30  # 30 seconds (provider-wide rate-limit cooldown)
        self._geocode_cache_ttl = 86400  # 24 hours
        self._last_rate_limit_time: float = 0.0
        self._time_func = time_func or time.time

    def _interpret_wmo(self, code: int) -> Tuple[str, str]:
        return WMO_INTERPRETATION.get(code, ("Fair", "partly-cloudy"))

    async def reverse_geocode(self, lat: float, lon: float) -> ReverseGeocodeResponse:
        """Resolves GPS coordinates to clean city and locality name via Nominatim."""
        cache_key = (round(lat, 3), round(lon, 3))
        now = self._time_func()
        if cache_key in self._geocode_cache:
            cached_time, cached_res = self._geocode_cache[cache_key]
            if now - cached_time < self._geocode_cache_ttl:
                return cached_res

        try:
            from app.providers.shared.nominatim_coordinator import get_nominatim_coordinator
            coordinator = get_nominatim_coordinator()
            params = {
                "lat": f"{lat:.5f}",
                "lon": f"{lon:.5f}",
                "format": "json"
            }
            d = await coordinator.execute_request("reverse", params=params)
            if isinstance(d, dict):
                    addr = d.get("address", {})
                    city = (
                        addr.get("city")
                        or addr.get("town")
                        or addr.get("suburb")
                        or addr.get("state_district")
                        or "Chennai"
                    )
                    locality = (
                        addr.get("neighbourhood")
                        or addr.get("suburb")
                        or addr.get("road")
                        or city
                    )
                    state = addr.get("state", "Tamil Nadu")
                    country = addr.get("country", "India")
                    display_name = f"{locality}, {city}" if locality != city else f"{city}, {state}"

                    result = ReverseGeocodeResponse(
                        latitude=lat,
                        longitude=lon,
                        display_name=display_name,
                        city=city,
                        locality=locality,
                        state=state,
                        country=country
                    )
                    self._geocode_cache[cache_key] = (now, result)
                    return result
        except Exception as e:
            logger.warning(f"Reverse geocode lookup failed for ({lat}, {lon}): {e}")

        # Fallback to coordinate-based label
        fallback = ReverseGeocodeResponse(
            latitude=lat,
            longitude=lon,
            display_name=f"Location ({lat:.4f}, {lon:.4f})",
            city="Chennai Region",
            state="Tamil Nadu",
            country="India"
        )
        return fallback

    async def get_live_weather(
        self,
        lat: float,
        lon: float,
        location_name: Optional[str] = None
    ) -> LiveWeatherResponse:
        """
        Fetches genuine current observations and forecasts from Open-Meteo.
        """
        cache_key = (round(lat, 2), round(lon, 2))
        now = self._time_func()
        if cache_key in self._weather_cache:
            cached_time, cached_res = self._weather_cache[cache_key]
            ttl = self._weather_cache_ttl if cached_res.available else self._negative_cache_ttl
            elapsed = now - cached_time
            if elapsed < ttl:
                # Return cached with updated cached flag and remaining TTL
                res = cached_res.model_copy()
                res.cached = True
                res.cache_expires_in_seconds = max(0, int(ttl - elapsed))
                if location_name:
                    res.location_name = location_name
                return res

        # Resolve location name if omitted
        resolved_name = location_name
        if not resolved_name or resolved_name == "Selected Location":
            geo = await self.reverse_geocode(lat, lon)
            resolved_name = geo.display_name

        # Provider-wide rate-limit cooldown: avoid retrying shared provider during active 429 cooldown
        rate_limit_elapsed = now - self._last_rate_limit_time
        if rate_limit_elapsed < self._rate_limit_cooldown:
            remaining_cooldown = max(0, int(self._rate_limit_cooldown - rate_limit_elapsed))
            unavail = self._build_unavailable_response(
                lat, lon, resolved_name, status="RATE_LIMITED",
                warning="Open-Meteo API rate limit reached. Please retry in a few moments.",
                cached=True,
                cache_expires_in_seconds=remaining_cooldown
            )
            self._weather_cache[cache_key] = (now, unavail)
            return unavail

        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat:.4f}&longitude={lon:.4f}"
                f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,uv_index"
                f"&hourly=temperature_2m,precipitation_probability,weather_code"
                f"&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max"
                f"&timezone=auto"
            )

            async with httpx.AsyncClient(timeout=4.5) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current", {})
                    daily = data.get("daily", {})
                    hourly = data.get("hourly", {})
                    tz = data.get("timezone", "Asia/Kolkata")

                    wcode = curr.get("weather_code", 0)
                    condition, icon_key = self._interpret_wmo(wcode)
                    temp = float(curr.get("temperature_2m", 25.0))
                    apparent_temp = float(curr.get("apparent_temperature", temp))
                    humidity = int(curr.get("relative_humidity_2m", 60))
                    wind_speed = float(curr.get("wind_speed_10m", 0.0))
                    wind_dir = int(curr.get("wind_direction_10m", 0))
                    precip = float(curr.get("precipitation", 0.0))
                    rain = float(curr.get("rain", 0.0))
                    cloud_cover = int(curr.get("cloud_cover", 0))

                    # Current real-time UV index (0.0 at night)
                    curr_uv = curr.get("uv_index")
                    uv_index = float(curr_uv) if curr_uv is not None else 0.0

                    # Peak forecast UV index from daily max
                    uv_list = daily.get("uv_index_max", [])
                    uv_index_max = float(uv_list[0]) if uv_list and uv_list[0] is not None else None

                    # Sunrise / Sunset from daily
                    sunrises = daily.get("sunrise", [])
                    sunsets = daily.get("sunset", [])
                    sunrise = sunrises[0] if sunrises else None
                    sunset = sunsets[0] if sunsets else None

                    # Parse next 24 hourly points
                    hourly_items: List[HourlyForecastItem] = []
                    h_times = hourly.get("time", [])
                    h_temps = hourly.get("temperature_2m", [])
                    h_probs = hourly.get("precipitation_probability", [])
                    h_codes = hourly.get("weather_code", [])

                    for i in range(min(24, len(h_times))):
                        hc = h_codes[i] if i < len(h_codes) else 0
                        h_cond, _ = self._interpret_wmo(hc)
                        hourly_items.append(HourlyForecastItem(
                            time=h_times[i],
                            temperature_2m=float(h_temps[i]) if i < len(h_temps) else temp,
                            precipitation_probability=int(h_probs[i]) if i < len(h_probs) and h_probs[i] is not None else 0,
                            weather_code=hc,
                            condition=h_cond
                        ))

                    # Parse next 7 daily points
                    daily_items: List[DailyForecastItem] = []
                    d_dates = daily.get("time", [])
                    d_codes = daily.get("weather_code", [])
                    d_maxs = daily.get("temperature_2m_max", [])
                    d_mins = daily.get("temperature_2m_min", [])
                    d_uvs = daily.get("uv_index_max", [])

                    for i in range(min(7, len(d_dates))):
                        dc = d_codes[i] if i < len(d_codes) else 0
                        d_cond, _ = self._interpret_wmo(dc)
                        daily_items.append(DailyForecastItem(
                            date=d_dates[i],
                            weather_code=dc,
                            condition=d_cond,
                            temperature_max=float(d_maxs[i]) if i < len(d_maxs) else temp,
                            temperature_min=float(d_mins[i]) if i < len(d_mins) else temp,
                            sunrise=sunrises[i] if i < len(sunrises) else None,
                            sunset=sunsets[i] if i < len(sunsets) else None,
                            uv_index_max=float(d_uvs[i]) if i < len(d_uvs) and d_uvs[i] is not None else None
                        ))

                    warnings = []
                    if wcode in [65, 82, 95, 96, 99]:
                        warnings.append(f"Severe Weather Condition: {condition}")
                    if wind_speed > 35.0:
                        warnings.append("High Wind Alert")
                    if precip > 5.0:
                        warnings.append("Heavy Rain Alert")

                    response = LiveWeatherResponse(
                        available=True,
                        status="AVAILABLE",
                        provider="Open-Meteo",
                        provider_url="https://open-meteo.com",
                        attribution="Weather data by Open-Meteo.com",
                        latitude=lat,
                        longitude=lon,
                        location_name=resolved_name,
                        timezone=tz,
                        temperature=temp,
                        apparent_temperature=apparent_temp,
                        weather_code=wcode,
                        condition=condition,
                        condition_icon=icon_key,
                        humidity=humidity,
                        wind_speed=wind_speed,
                        wind_direction=wind_dir,
                        precipitation=precip,
                        rain=rain,
                        cloud_cover=cloud_cover,
                        uv_index=uv_index,
                        uv_index_max=uv_index_max,
                        sunrise=sunrise,
                        sunset=sunset,
                        hourly_forecast=hourly_items,
                        daily_forecast=daily_items,
                        observation_timestamp=curr.get("time", datetime.datetime.utcnow().isoformat()),
                        cached=False,
                        cache_expires_in_seconds=self._weather_cache_ttl,
                        warnings=warnings
                    )

                    self._weather_cache[cache_key] = (now, response)
                    return response
                elif resp.status_code == 429:
                    logger.warning("Open-Meteo API rate limit reached.")
                    self._last_rate_limit_time = now
                    unavail = self._build_unavailable_response(
                        lat, lon, resolved_name, status="RATE_LIMITED",
                        warning="Open-Meteo API rate limit reached. Please retry in a few moments.",
                        cached=False,
                        cache_expires_in_seconds=self._negative_cache_ttl
                    )
                    self._weather_cache[cache_key] = (now, unavail)
                    return unavail
        except Exception as e:
            logger.warning(f"Failed to fetch live weather from Open-Meteo for ({lat}, {lon}): {e}")

        unavail = self._build_unavailable_response(
            lat, lon, resolved_name, status="UNAVAILABLE",
            warning="Live weather provider is temporarily unreachable.",
            cached=False,
            cache_expires_in_seconds=self._negative_cache_ttl
        )
        self._weather_cache[cache_key] = (now, unavail)
        return unavail

    def _build_unavailable_response(
        self,
        lat: float,
        lon: float,
        location_name: str,
        status: str = "UNAVAILABLE",
        warning: str = "Live weather data currently unavailable",
        cached: bool = False,
        cache_expires_in_seconds: Optional[int] = None
    ) -> LiveWeatherResponse:
        return LiveWeatherResponse(
            available=False,
            status=status,
            provider="Open-Meteo",
            provider_url="https://open-meteo.com",
            attribution="Weather data by Open-Meteo.com",
            latitude=lat,
            longitude=lon,
            location_name=location_name,
            timezone="Asia/Kolkata",
            temperature=0.0,
            apparent_temperature=0.0,
            weather_code=-1,
            condition="Weather unavailable",
            condition_icon="cloudy",
            humidity=0,
            wind_speed=0.0,
            wind_direction=0,
            precipitation=0.0,
            rain=0.0,
            cloud_cover=0,
            uv_index=None,
            uv_index_max=None,
            sunrise=None,
            sunset=None,
            hourly_forecast=[],
            daily_forecast=[],
            observation_timestamp=datetime.datetime.utcnow().isoformat(),
            cached=cached,
            cache_expires_in_seconds=cache_expires_in_seconds,
            warnings=[warning]
        )


# Global singleton instance
global_weather_service = WeatherService()
