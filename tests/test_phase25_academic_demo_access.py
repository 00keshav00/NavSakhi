import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas.journey_schemas import JourneyCreate
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.fixture
def auth_headers():
    token = AuthService.create_access_token("user_demo_123", "testuser@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_guest_route_planning_via_standard_endpoint():
    """
    Stage 1 Test: Unauthenticated guests can plan multimodal routes
    via POST /api/v1/journeys/ without an account.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "source": "Chennai Central",
            "destination": "Guindy",
            "preferences": ["transit", "walk"]
        }
        response = await client.post("/api/v1/journeys/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "recommended_routes" in data["data"]
        routes = data["data"]["recommended_routes"]
        assert len(routes) > 0
        primary_route = routes[0]
        assert "segments" in primary_route
        assert len(primary_route["segments"]) > 0


@pytest.mark.asyncio
async def test_guest_route_planning_via_dedicated_endpoint():
    """
    Stage 1 Test: Unauthenticated guests can plan routes via dedicated POST /api/v1/journeys/guest/plan.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "source": "Guindy",
            "destination": "Tambaram",
            "preferences": ["transit"]
        }
        response = await client.post("/api/v1/journeys/guest/plan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["recommended_routes"]) > 0


@pytest.mark.asyncio
async def test_guest_cannot_access_protected_journey_lifecycle():
    """
    Stage 2 Test: Actions involving personal journey records or live tracking
    strictly require authentication.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start journey requires authentication
        res_start = await client.post("/api/v1/journeys/j_12345/start", json={})
        assert res_start.status_code == 401

        # Pause journey requires authentication
        res_pause = await client.post("/api/v1/journeys/j_12345/pause")
        assert res_pause.status_code == 401

        # Get active journey requires authentication
        res_active = await client.get("/api/v1/journeys/active")
        assert res_active.status_code == 401


@pytest.mark.asyncio
async def test_guest_cannot_trigger_emergency_sos():
    """
    Stage 2 Test: Triggering SOS requires an authenticated user account.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"current_location": "13.0827° N, 80.2707° E"}
        response = await client.post("/api/v1/emergency/sos", json=payload)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_user_can_trigger_sos_simulation(auth_headers):
    """
    Stage 3 Test: Authenticated users can trigger the demonstration SOS session.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"current_location": "13.0827° N, 80.2707° E"}
        response = await client.post("/api/v1/emergency/sos", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data["data"]


@pytest.mark.asyncio
async def test_guest_can_access_public_dashboard_overview():
    """
    Stage 1 Test: Unauthenticated guests can fetch public dashboard overview.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_guest_can_access_assistant_context():
    """
    Stage 1 Test: Unauthenticated guests can access general safety assistant context.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/assistant/context")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
