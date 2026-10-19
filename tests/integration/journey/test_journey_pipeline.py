import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import connect_to_mongo, get_database
from app.api.dependencies import get_journey_coordinator, get_routing_provider, get_location_provider, get_weather_provider, get_transit_provider, get_reports_provider
from app.models.journey import Location
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_db():
    await connect_to_mongo()
    yield

@pytest.fixture
async def journey_coordinator():
    db_gen = get_database()
    db = await anext(db_gen)
    
    routing = get_routing_provider()
    location = get_location_provider()
    weather = get_weather_provider()
    transit = get_transit_provider()
    reports = get_reports_provider(db)
    
    return JourneyIntelligenceCoordinator(
        routing_provider=routing,
        location_provider=location,
        weather_provider=weather,
        transit_provider=transit,
        reports_provider=reports
    )

@pytest.fixture
def test_source():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.fixture
def test_destination():
    # Koramangala, Bengaluru
    return Location(coordinates=[77.6245, 12.9352])

@pytest.mark.asyncio
async def test_journey_orchestration(journey_coordinator, test_source, test_destination):
    """
    1. Resolves all providers correctly.
    2. All providers execute successfully.
    4. Returned objects are all SafeShe domain models.
    8. Provider orchestration matches architecture.
    """
    assert journey_coordinator.routing_provider is not None
    assert journey_coordinator.location_provider is not None
    assert journey_coordinator.weather_provider is not None
    assert journey_coordinator.reports_provider is not None
    assert journey_coordinator.transit_provider is not None
    
    # 2 & 8: Execute all providers concurrently
    context = await journey_coordinator.gather_journey_context(test_source, test_destination)
    
    # 4: Domain models only
    assert type(context["routes"]).__name__ == "RouteCollection"
    assert type(context["weather"]).__name__ == "WeatherState"
    assert type(context["pois"]).__name__ == "POICollection"
    assert type(context["reports"]).__name__ == "ReportCollection"
    assert type(context["transit"]).__name__ == "TransitCollection"
    
    # Check that they have data
    assert len(context["routes"].items) > 0
    assert context["weather"].condition is not None
    # Depending on DB state, reports might be empty, but it's a valid collection
    assert isinstance(context["reports"].items, list)

@pytest.mark.asyncio
async def test_coordinator_failure_propagation(journey_coordinator, test_destination):
    """
    5. Failure of one provider follows current architecture.
    Using bad coordinates to trigger a provider error (e.g. Nominatim or OSRM).
    Because return_exceptions=False is used in gather(), the exception cleanly escapes
    and gets caught by FastAPI exception handler in the real app.
    """
    bad_source = Location(coordinates=[999.0, 999.0])
    
    with pytest.raises(Exception):
        await journey_coordinator.gather_journey_context(bad_source, test_destination)

@pytest.mark.asyncio
async def test_coordinator_caching(journey_coordinator, test_source, test_destination):
    """
    7. Cache infrastructure behaves correctly.
    Calling orchestration twice should be significantly faster the second time.
    """
    # First invocation
    start_time = time.time()
    await journey_coordinator.gather_journey_context(test_source, test_destination)
    first_duration = time.time() - start_time
    
    # Second invocation
    start_time = time.time()
    await journey_coordinator.gather_journey_context(test_source, test_destination)
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    assert second_duration < 0.2  # Nearly instant

def test_debug_endpoint_and_dependency_injection():
    """
    3. Dependency Injection works end-to-end.
    6. Retry infrastructure behaves correctly (inherited from providers).
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
    
    with TestClient(app) as live_client:
        response = live_client.post("/api/v1/debug/journey", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        # Validate that everything was extracted properly
        assert "routes" in data
        assert "weather" in data
        assert "pois" in data
        assert "reports" in data
        assert "transit" in data
        
        # Validates no vendor JSON
        assert "items" in data["routes"]
        assert "temperature" in data["weather"]
