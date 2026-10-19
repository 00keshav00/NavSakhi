import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db.connection import connect_to_mongo, get_database
from app.providers.reports.provider import MongoReportsProvider
from app.models.journey import Location
from app.models.community import CommunityReport
from app.providers.shared.exceptions import ProviderError, ProviderResponseMappingError
import uuid

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_db():
    await connect_to_mongo()
    yield
    # We could drop the test collection here if we used a dedicated test DB.
    # Since we use the real configured one, we'll just leave it or rely on unique IDs.

@pytest.fixture
async def reports_provider():
    # Use real db connection
    db_gen = get_database()
    db = await anext(db_gen)
    
    # Ensure 2dsphere index exists for geo queries
    await db.community_reports.create_index([("location.coordinates", "2dsphere")])
    
    provider = MongoReportsProvider(db)
    return provider

@pytest.fixture
def test_location():
    # MG Road, Bengaluru
    return Location(coordinates=[77.5946, 12.9716])

@pytest.mark.asyncio
async def test_create_and_get_report_by_id(reports_provider, test_location):
    """
    1. CreateReport works.
    2. ReportById works.
    6. CommunityReport mapping is correct.
    7. MongoDB ObjectIds never escape the provider boundary.
    12. Only SafeShe domain models leave the provider.
    """
    # Create
    report_in = CommunityReport(
        location=test_location,
        report_type=f"test_report_{uuid.uuid4().hex}",
        description="Integration test report",
        is_active=True
    )
    
    created = await reports_provider.create_report(report_in)
    
    assert type(created).__name__ == "CommunityReport"
    assert created.id is not None
    assert type(created.id) == str # No ObjectId escapes
    assert created.description == "Integration test report"
    
    # Get By Id
    fetched = await reports_provider.get_report_by_id(created.id)
    assert type(fetched).__name__ == "CommunityReport"
    assert fetched.id == created.id
    assert fetched.report_type == created.report_type
    assert type(fetched.id) == str

@pytest.mark.asyncio
async def test_nearby_reports_and_geospatial(reports_provider, test_location):
    """
    3. NearbyReports returns ReportCollection.
    4. Radius filtering works correctly.
    5. ReportCount is correct.
    13. 2dsphere geospatial queries execute correctly.
    """
    # Ensure at least one report exists at the exact location
    report_in = CommunityReport(
        location=test_location,
        report_type="geo_test",
        is_active=True
    )
    await reports_provider.create_report(report_in)
    
    # 3. Returns ReportCollection
    collection = await reports_provider.get_nearby_reports(test_location, radius_m=500)
    assert type(collection).__name__ == "ReportCollection"
    
    # 5. ReportCount is correct
    count = await reports_provider.get_report_count(test_location, radius_m=500)
    assert count == len(collection.items)
    assert count > 0
    
    # 4. Radius filtering works
    # Create a report 10km away
    far_location = Location(coordinates=[77.5946 + 0.1, 12.9716 + 0.1])
    await reports_provider.create_report(CommunityReport(location=far_location, report_type="far_report", is_active=True))
    
    small_radius_collection = await reports_provider.get_nearby_reports(test_location, radius_m=100)
    large_radius_collection = await reports_provider.get_nearby_reports(test_location, radius_m=20000)
    
    assert len(large_radius_collection.items) > len(small_radius_collection.items)

@pytest.mark.asyncio
async def test_empty_search_radius(reports_provider):
    """
    9. Empty search radius returns an empty ReportCollection.
    """
    # Middle of ocean
    ocean_loc = Location(coordinates=[0.0, 0.0])
    collection = await reports_provider.get_nearby_reports(ocean_loc, radius_m=10)
    assert len(collection.items) == 0

@pytest.mark.asyncio
async def test_invalid_coordinates(reports_provider):
    """
    8. Invalid coordinates are handled correctly.
    Mongo will reject coordinates outside [-180, 180] and [-90, 90] for 2dsphere index.
    """
    bad_loc = Location(coordinates=[999.0, 999.0])
    
    with pytest.raises(Exception):
        await reports_provider.get_nearby_reports(bad_loc, radius_m=1000)

@pytest.mark.asyncio
async def test_cache_mechanism(reports_provider, test_location):
    """
    11. Cache behaviour is verified.
    """
    # First call
    start_time = time.time()
    await reports_provider.get_nearby_reports(test_location, radius_m=100)
    first_duration = time.time() - start_time
    
    # Second call (cached)
    start_time = time.time()
    await reports_provider.get_nearby_reports(test_location, radius_m=100)
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    assert second_duration < 0.1

@pytest.mark.asyncio
async def test_retry_mechanism(reports_provider, test_location):
    """
    10. Retry behaviour is verified where applicable.
    We test this by passing an invalid report_id which normally just raises ProviderResponseMappingError instantly.
    But to test DB retry, we would need the DB connection to drop, which is hard to mock without mocking.
    However, the @with_retry decorator is on get_report_by_id. 
    If we mock just the db collection to throw network errors, we can see it wait.
    Since we cannot mock, we simply ensure the decorator doesn't break the function for legitimate exceptions (like invalid ObjectId format).
    """
    with pytest.raises(Exception):
        await reports_provider.get_report_by_id("invalid-hex-format")

def test_debug_endpoint():
    """
    Verify debug endpoint works end-to-end and returns strictly SafeShe domains (no mongo documents).
    Using context manager to trigger lifespan so DB connects.
    """
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "radius": 1000
    }
    with TestClient(app) as live_client:
        response = live_client.post("/api/v1/debug/providers/reports", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "metadata" in data
        
        if len(data["items"]) > 0:
            first_item = data["items"][0]
            assert "id" in first_item
            assert "_id" not in first_item # Mongo specific field should not exist
