import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_weather_provider
from app.models.journey import Location, WeatherState
from app.providers.shared.exceptions import ProviderError, ProviderResponseMappingError

client = TestClient(app)

@pytest.fixture
def weather_provider():
    return get_weather_provider()

@pytest.fixture
def valid_bengaluru_location():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.mark.asyncio
async def test_weather_state_mapping(weather_provider, valid_bengaluru_location):
    """
    1. WeatherState is returned successfully.
    2. Temperature is populated.
    3. Humidity is populated.
    4. Visibility is populated.
    5. Weather condition is populated.
    6. Wind speed is mapped correctly.
    11. No raw vendor JSON escapes the provider boundary.
    12. The returned object is strictly the WeatherState domain model.
    """
    weather = await weather_provider.get_weather(valid_bengaluru_location)
    
    # 1, 11, 12: Strictly WeatherState domain model
    assert type(weather).__name__ == "WeatherState"
    assert isinstance(weather, WeatherState)
    assert not isinstance(weather, dict) # No raw JSON escapes
    
    # 2. Temperature
    assert weather.temperature is not None
    assert isinstance(weather.temperature, (int, float))
    
    # 3. Humidity
    assert weather.humidity is not None
    assert isinstance(weather.humidity, (int, float))
    
    # 4. Visibility
    assert weather.visibility is not None
    assert isinstance(weather.visibility, (int, float))
    
    # 5. Condition
    assert weather.condition is not None
    assert weather.condition != "UNKNOWN"
    assert isinstance(weather.condition, str)
    
    # 6. Wind Speed
    assert weather.wind_speed is not None
    assert isinstance(weather.wind_speed, (int, float))

@pytest.mark.asyncio
async def test_invalid_coordinates_exception(weather_provider):
    """
    7. Invalid coordinates are handled correctly.
    8. External API failures are handled gracefully.
    OpenWeather API returns 400 for out-of-bounds lat/lon.
    """
    bad_location = Location(coordinates=[999.0, 999.0])
    
    with pytest.raises(Exception) as exc_info:
        await weather_provider.get_weather(bad_location)
    
    # Ensures it's caught and re-raised cleanly rather than crashing silently
    assert "error" in str(exc_info.value).lower() or "fail" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_retry_mechanism():
    """
    9. Retry mechanism functions correctly.
    Instantiate a provider with a bad URL and measure execution time.
    """
    provider = get_weather_provider()
    provider.base_url = "http://localhost:9999/does-not-exist"
    
    start_time = time.time()
    with pytest.raises(Exception):
        await provider.get_weather(Location(coordinates=[0,0]))
    duration = time.time() - start_time
    
    # max_retries=2, base_delay_ms=200 -> Expect duration > 0.3s
    assert duration > 0.3

@pytest.mark.asyncio
async def test_cache_mechanism(weather_provider, valid_bengaluru_location):
    """
    10. Cache mechanism functions correctly.
    """
    # First call
    start_time = time.time()
    await weather_provider.get_weather(valid_bengaluru_location)
    first_duration = time.time() - start_time
    
    # Second call
    start_time = time.time()
    await weather_provider.get_weather(valid_bengaluru_location)
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    # Cache hits take practically 0 time
    assert second_duration < 0.1

def test_debug_endpoint():
    """
    Verify the comprehensive debug endpoint works.
    """
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946
    }
    response = client.post("/api/v1/debug/providers/weather", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "temperature" in data
    assert "humidity" in data
    assert "visibility" in data
    assert "condition" in data
    assert "wind_speed" in data
