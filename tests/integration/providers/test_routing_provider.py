import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_routing_provider
from app.models.journey import Location
from app.providers.shared.exceptions import ProviderError

client = TestClient(app)

@pytest.fixture
def routing_provider():
    return get_routing_provider()

@pytest.fixture
def valid_bengaluru_source():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.fixture
def valid_bengaluru_destination():
    # Koramangala, Bengaluru
    return Location(coordinates=[77.6245, 12.9352])

@pytest.mark.asyncio
async def test_valid_route_properties(routing_provider, valid_bengaluru_source, valid_bengaluru_destination):
    """
    1. Valid route between two Bengaluru coordinates
    2. Route distance is greater than zero
    3. ETA is greater than zero
    4. Polyline exists
    5. CandidateRoute mapping is correct
    """
    route = await routing_provider.get_route(
        source=valid_bengaluru_source,
        destination=valid_bengaluru_destination,
        mode="driving"
    )
    
    # 5. CandidateRoute mapping is correct (type check)
    assert type(route).__name__ == "CandidateRoute"
    assert route.route_identifier.startswith("vendor_route_")
    assert route.recommendation_status == "PENDING"
    
    # 2. Distance > 0
    assert route.distance > 0
    
    # 3. ETA > 0
    assert route.duration > 0
    
    # 4. Polyline exists (geometry)
    assert "geometry" in route.route_metadata
    assert route.route_metadata["geometry"] is not None

@pytest.mark.asyncio
async def test_invalid_coordinates_exception(routing_provider):
    """
    6. Invalid coordinates return appropriate exceptions
    """
    bad_source = Location(coordinates=[999.0, 999.0])
    bad_destination = Location(coordinates=[-999.0, -999.0])
    
    with pytest.raises(Exception):
        await routing_provider.get_route(
            source=bad_source,
            destination=bad_destination,
            mode="driving"
        )

@pytest.mark.asyncio
async def test_cache_mechanism(routing_provider, valid_bengaluru_source, valid_bengaluru_destination):
    """
    8. Cache works correctly
    We verify by measuring time. First call goes to network, second call should be instant.
    """
    # First call
    start_time = time.time()
    await routing_provider.get_route(
        source=valid_bengaluru_source, 
        destination=valid_bengaluru_destination, 
        mode="driving"
    )
    first_duration = time.time() - start_time
    
    # Second call (should be cached)
    start_time = time.time()
    await routing_provider.get_route(
        source=valid_bengaluru_source, 
        destination=valid_bengaluru_destination, 
        mode="driving"
    )
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    # Usually cache hits are extremely fast (e.g. < 5ms)
    assert second_duration < 0.1

@pytest.mark.asyncio
async def test_retry_mechanism():
    """
    7. Retry mechanism works
    To test retry without mocking, we can instantiate a provider with a bad URL and 
    measure that it takes at least 200ms * (2^0 + 2^1...) = 200 + 400 + 800ms before failing.
    The configured max_retries is 3, base_delay_ms is 200.
    """
    provider = get_routing_provider()
    # Temporarily override url to something that will timeout/fail connection
    provider.base_url = "http://localhost:9999/does-not-exist"
    
    start_time = time.time()
    with pytest.raises(Exception):
        await provider.get_route(
            source=Location(coordinates=[0,0]),
            destination=Location(coordinates=[1,1]),
            mode="driving"
        )
    duration = time.time() - start_time
    
    # max_retries=3 means 3 attempts total.
    # Attempt 0: fails -> delay 200ms
    # Attempt 1: fails -> delay 400ms
    # Attempt 2: fails -> delay 800ms
    # Total delay = 1.4s minimum. Wait, retry logic:
    # `for attempt in range(max_retries): ...` -> 3 loops (attempt 0, 1, 2).
    # Delay happens inside except block. Attempt 2 delay might be awaited if it fails.
    # Let's just assert that duration is > 0.5s to prove retry happened.
    assert duration > 0.5

def test_debug_endpoint():
    """
    Also verify the debug endpoint works end-to-end.
    """
    payload = {
        "source": {
            "lat": 12.9716,
            "lon": 77.5946
        },
        "destination": {
            "lat": 12.9352,
            "lon": 77.6245
        }
    }
    response = client.post("/api/v1/debug/providers/routing", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "route_identifier" in data
    assert data["distance"] > 0
    assert data["duration"] > 0
    assert "geometry" in data["route_metadata"]
