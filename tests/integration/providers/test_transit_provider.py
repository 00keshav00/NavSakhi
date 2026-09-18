import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_transit_provider
from app.models.journey import Location, TransitCollection, TransitSegment
from app.intelligence.journey.providers import TransitProvider

client = TestClient(app)

@pytest.fixture
def transit_provider():
    return get_transit_provider()

@pytest.fixture
def test_source():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.fixture
def test_destination():
    # Koramangala, Bengaluru
    return Location(coordinates=[77.6245, 12.9352])

@pytest.mark.asyncio
async def test_transit_contract(transit_provider, test_source, test_destination):
    """
    1. TransitCollection is returned.
    2. TransitSegment mapping is correct.
    4. Provider interface contract is respected.
    6. No provider-specific implementation details escape the provider.
    """
    # 4. Interface contract respected
    assert isinstance(transit_provider, TransitProvider)
    
    collection = await transit_provider.get_transit_segments(test_source, test_destination)
    
    # 1. Collection returned
    assert type(collection).__name__ == "TransitCollection"
    assert isinstance(collection.items, list)
    
    # 2. TransitSegment mapping
    if len(collection.items) > 0:
        segment = collection.items[0]
        assert type(segment).__name__ == "TransitSegment"
        assert segment.mode is not None
        assert segment.start_station is not None
        assert segment.end_station is not None
        
        # 6. No provider details escape (e.g., shouldn't be a generic dict)
        assert not isinstance(segment, dict)

@pytest.mark.asyncio
async def test_empty_transit_responses(transit_provider):
    """
    5. Empty transit responses are handled correctly.
    To test this on a placeholder, we might not have dynamic logic for empty responses.
    But we can verify that sending identically equal locations doesn't crash, 
    even if it returns a mocked direct segment, it obeys the contract.
    If the placeholder gets upgraded to OTP, this would naturally return empty or raise.
    """
    same_location = Location(coordinates=[77.5, 12.9])
    
    # Just verify it resolves without internal server error
    collection = await transit_provider.get_transit_segments(same_location, same_location)
    assert type(collection).__name__ == "TransitCollection"

def test_dependency_injection():
    """
    3. Dependency Injection resolves correctly.
    """
    provider = get_transit_provider()
    assert provider is not None
    assert isinstance(provider, TransitProvider)

def test_debug_endpoint():
    """
    Verify the comprehensive debug endpoint works.
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
    response = client.post("/api/v1/debug/providers/transit", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "metadata" in data
    assert isinstance(data["items"], list)
    
    if len(data["items"]) > 0:
        assert "mode" in data["items"][0]
        assert "start_station" in data["items"][0]
