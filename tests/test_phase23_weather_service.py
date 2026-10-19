import pytest
from app.services.weather_service import WeatherService, WMO_INTERPRETATION
from app.schemas.weather_schemas import LiveWeatherResponse

@pytest.mark.asyncio
async def test_weather_service_wmo_interpretation():
    """Verify WMO codes map to honest human descriptions."""
    service = WeatherService()
    assert service._interpret_wmo(0)[0] == "Clear sky"
    assert service._interpret_wmo(2)[0] == "Partly cloudy"
    assert service._interpret_wmo(3)[0] == "Overcast"
    assert service._interpret_wmo(61)[0] == "Slight rain"
    assert service._interpret_wmo(95)[0] == "Thunderstorm"

@pytest.mark.asyncio
async def test_weather_service_caching_and_schema():
    """Test live weather fetching from Open-Meteo and verify schema conformance."""
    service = WeatherService()
    # Test Chennai Central coordinates
    weather = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
    
    assert weather.provider == "Open-Meteo"
    assert weather.latitude == 13.0827
    assert weather.longitude == 80.2707
    assert weather.location_name == "Chennai Central"
    assert isinstance(weather.temperature, (int, float))
    assert isinstance(weather.humidity, (int, float))
    assert isinstance(weather.condition, str)
    assert len(weather.hourly_forecast) > 0
    assert len(weather.daily_forecast) > 0

    # Second call within TTL should return cached response
    cached = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
    assert cached.cached is True
    assert cached.temperature == weather.temperature
