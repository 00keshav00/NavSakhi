"""
SafeShe Weather API Router
Serves genuine Open-Meteo observations, forecasts, and reverse geocoding endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from app.schemas.responses import StandardResponse
from app.schemas.weather_schemas import LiveWeatherResponse, ReverseGeocodeResponse
from app.services.weather_service import global_weather_service

router = APIRouter()


@router.get("/live", response_model=StandardResponse[LiveWeatherResponse])
async def get_live_weather(
    lat: float = Query(..., description="Latitude (-90 to 90)"),
    lon: float = Query(..., description="Longitude (-180 to 180)"),
    location_name: Optional[str] = Query(None, description="Optional custom place label")
):
    """
    Returns authentic, real-time weather observations, UV index,
    and hourly/daily forecasts directly from Open-Meteo.
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates.")

    weather = await global_weather_service.get_live_weather(
        lat=lat,
        lon=lon,
        location_name=location_name
    )
    return StandardResponse(success=True, data=weather)


@router.get("/reverse-geocode", response_model=StandardResponse[ReverseGeocodeResponse])
async def reverse_geocode_location(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    """
    Resolves geographic coordinates into a human-readable city and locality name.
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Invalid coordinates.")

    res = await global_weather_service.reverse_geocode(lat=lat, lon=lon)
    return StandardResponse(success=True, data=res)
