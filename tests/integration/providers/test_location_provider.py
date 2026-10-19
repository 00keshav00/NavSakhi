import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_location_provider
from app.models.journey import Location
from app.providers.shared.exceptions import ProviderError, ProviderResponseMappingError

client = TestClient(app)

@pytest.fixture
def location_provider():
    return get_location_provider()

@pytest.fixture
def valid_bengaluru_location():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.mark.asyncio
async def test_reverse_geocode(location_provider, valid_bengaluru_location):
    """
    1. Reverse geocoding returns a valid Address domain model.
    """
    address = await location_provider.reverse_geocode(valid_bengaluru_location)
    assert type(address).__name__ == "Address"
    assert address.display_name is not None
    assert len(address.display_name) > 0
    assert "metadata" in address.model_dump()

@pytest.mark.asyncio
async def test_nearby_pois(location_provider, valid_bengaluru_location):
    """
    2-6. Nearby hospitals, police stations, restaurants, bus stops, metro stations return a POICollection.
    """
    poi_types = ["hospital", "police", "restaurant", "bus_stop", "metro"]
    
    for poi_type in poi_types:
        collection = await location_provider.get_nearby_pois(
            location=valid_bengaluru_location, 
            poi_type=poi_type, 
            radius_m=2000
        )
        assert type(collection).__name__ == "POICollection"
        assert isinstance(collection.items, list)
        
        # Verify mapping of individual POIs
        if len(collection.items) > 0:
            first_poi = collection.items[0]
            assert type(first_poi).__name__ == "POI"
            assert first_poi.poi_type == poi_type
            assert first_poi.location is not None
            assert len(first_poi.location.coordinates) == 2

@pytest.mark.asyncio
async def test_road_info(location_provider, valid_bengaluru_location):
    """
    7. RoadInfo mapping is correct.
    """
    road_info = await location_provider.get_road_type(valid_bengaluru_location)
    assert type(road_info).__name__ == "RoadInfo"
    assert road_info.road_type is not None
    assert "metadata" in road_info.model_dump()

@pytest.mark.asyncio
async def test_invalid_coordinates_exception(location_provider):
    """
    8. Invalid coordinates return appropriate exceptions.
    Nominatim usually returns a 400 Bad Request for lat/lon > 90/180.
    """
    bad_location = Location(coordinates=[999.0, 999.0])
    
    with pytest.raises(Exception):
        await location_provider.reverse_geocode(bad_location)

@pytest.mark.asyncio
async def test_retry_mechanism():
    """
    9. Retry behaviour is verified.
    To test retry without mocking, we instantiate a provider with a bad URL and 
    measure that it takes significant time before failing (indicating retries occurred).
    """
    provider = get_location_provider()
    # Temporarily override url to force connection failure
    provider.base_url = "http://localhost:9999/does-not-exist"
    
    start_time = time.time()
    with pytest.raises(Exception):
        await provider.reverse_geocode(Location(coordinates=[0,0]))
    duration = time.time() - start_time
    
    # Provider is configured with @with_retry(max_retries=3, base_delay_ms=200)
    # The exponential backoff will cause attempts to delay minimum > 0.5s total.
    assert duration > 0.5

@pytest.mark.asyncio
async def test_cache_mechanism(location_provider, valid_bengaluru_location):
    """
    10. Cache behaviour is verified.
    """
    # First call
    start_time = time.time()
    await location_provider.reverse_geocode(valid_bengaluru_location)
    first_duration = time.time() - start_time
    
    # Second call (should hit cache and return instantly)
    start_time = time.time()
    await location_provider.reverse_geocode(valid_bengaluru_location)
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    # Usually cache hits take < 0.1s
    assert second_duration < 0.1

def test_debug_endpoint():
    """
    Verify the comprehensive debug endpoint works.
    """
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946
    }
    response = client.post("/api/v1/debug/providers/location", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "address" in data
    assert "road_info" in data
    assert "hospitals" in data
    assert "police_stations" in data
    assert "restaurants" in data
    assert "bus_stops" in data
    assert "metro_stations" in data
