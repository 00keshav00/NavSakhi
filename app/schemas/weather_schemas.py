"""
SafeShe Weather Pydantic Schemas
Strictly typed data contracts for live Open-Meteo observations, hourly forecasts,
and reverse-geocoded location data.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HourlyForecastItem(BaseModel):
    time: str = Field(..., description="ISO 8601 or local timestamp")
    temperature_2m: float = Field(..., description="Air temperature in Celsius")
    precipitation_probability: Optional[int] = Field(0, description="Precipitation probability 0-100%")
    weather_code: int = Field(0, description="WMO weather interpretation code")
    condition: str = Field("Clear", description="Human-readable condition label")


class DailyForecastItem(BaseModel):
    date: str = Field(..., description="Date YYYY-MM-DD")
    weather_code: int = Field(0, description="WMO weather code")
    condition: str = Field("Clear", description="Condition label")
    temperature_max: float = Field(..., description="Daily maximum temperature in Celsius")
    temperature_min: float = Field(..., description="Daily minimum temperature in Celsius")
    sunrise: Optional[str] = Field(None, description="Sunrise ISO timestamp")
    sunset: Optional[str] = Field(None, description="Sunset ISO timestamp")
    uv_index_max: Optional[float] = Field(None, description="Maximum UV index")


class LiveWeatherResponse(BaseModel):
    available: bool = Field(True, description="True if weather successfully retrieved from verified provider")
    status: str = Field("AVAILABLE", description="AVAILABLE | UNAVAILABLE | RATE_LIMITED | ERROR")
    provider: str = Field("Open-Meteo", description="Authoritative data provider name")
    provider_url: str = Field("https://open-meteo.com", description="Provider documentation reference")
    attribution: str = Field("Weather data by Open-Meteo.com", description="Official attribution notice")
    
    # Location
    latitude: float = Field(..., description="Resolved latitude")
    longitude: float = Field(..., description="Resolved longitude")
    location_name: str = Field("Selected Location", description="Human-readable city or locality name")
    timezone: str = Field("Asia/Kolkata", description="Resolved local timezone")
    
    # Current Observations
    temperature: float = Field(..., description="Current 2m temperature in Celsius")
    apparent_temperature: float = Field(..., description="Apparent 'feels like' temperature in Celsius")
    weather_code: int = Field(0, description="WMO weather code (0-99)")
    condition: str = Field("Clear", description="Interpreted weather condition text")
    condition_icon: str = Field("sun", description="Suggested icon key (sun, partly-cloudy, cloudy, rain, thunderstorm, etc.)")
    humidity: int = Field(..., description="Relative humidity percentage (0-100%)")
    wind_speed: float = Field(..., description="Wind speed in km/h")
    wind_direction: int = Field(0, description="Wind direction in degrees (0-360)")
    precipitation: float = Field(0.0, description="Current precipitation amount in mm")
    rain: float = Field(0.0, description="Current rain in mm")
    cloud_cover: int = Field(0, description="Cloud cover percentage (0-100%)")
    uv_index: Optional[float] = Field(None, description="Current real-time UV index (0.0 at night)")
    uv_index_max: Optional[float] = Field(None, description="Today's maximum forecast UV index")
    
    # Forecast & Solar
    sunrise: Optional[str] = Field(None, description="Today's sunrise")
    sunset: Optional[str] = Field(None, description="Today's sunset")
    hourly_forecast: List[HourlyForecastItem] = Field(default_factory=list, description="Next 24 hours forecast")
    daily_forecast: List[DailyForecastItem] = Field(default_factory=list, description="Next 7 days forecast")
    
    # Provenance
    observation_timestamp: str = Field(..., description="Provider observation timestamp")
    cached: bool = Field(False, description="True if served from memory cache")
    cache_expires_in_seconds: Optional[int] = Field(None, description="Seconds until cache invalidation")
    warnings: List[str] = Field(default_factory=list, description="Weather hazards (heavy rain, severe storm, etc.)")


class ReverseGeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    display_name: str
    city: Optional[str] = None
    locality: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
