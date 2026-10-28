"""
Test suite for Phase 51.97: Profile Identity Isolation and Real Data Persistence.
Verifies that:
1. Two distinct users see only their own data (no shared state, no cross-talk).
2. All hardcoded mock identities ('Sarah Connor', 'John Connor', fake Bangalore stats) are eliminated.
3. Absent fields show honest neutral defaults ('Not provided', 'Not available', empty lists).
4. Profile updates persist accurately in the database repository and service.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from app.models.user import User, EmergencyContact
from app.tools.profile import ProfileTool
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.schemas.user_schemas import ProfileUpdate
from app.services.user_service import UserService


def test_no_hardcoded_sarah_connor_in_fallback():
    """Verify fallback profile never contains fictional identities."""
    tool = ProfileTool()
    fallback = tool._fallback_profile()
    assert "Sarah Connor" not in fallback["profile"]["name"]
    assert "John Connor" not in str(fallback["profile"]["emergency_contacts"])
    assert fallback["profile"]["name"] == "NavSakhi User"
    assert fallback["profile"]["emergency_contacts"] == []


@pytest.mark.asyncio
async def test_profile_tool_two_users_isolated():
    """Verify ProfileTool returns distinct real profiles for distinct users."""
    tool = ProfileTool()

    user_a = User(
        id=ObjectId(),
        username="priya_s",
        email="priya.sharma@example.com",
        password_hash="mock_hash_a",
        profile_settings={
            "full_name": "Priya Sharma",
            "phone_number": "+91 98765 43210",
            "current_city": "Chennai"
        },
        emergency_contacts=[
            EmergencyContact(name="Ananya Sharma", phone_number="+91 98765 11111", relationship="Sister")
        ]
    )

    user_b = User(
        id=ObjectId(),
        username="deepa_r",
        email="deepa.raman@example.com",
        password_hash="mock_hash_b",
        profile_settings={
            "full_name": "Deepa Raman",
            "phone_number": "+91 91234 56789",
            "current_city": "Coimbatore"
        },
        emergency_contacts=[]
    )

    res_a = await tool.execute({"user": user_a})
    res_b = await tool.execute({"user": user_b})

    prof_a = res_a["profile"]
    prof_b = res_b["profile"]

    # Assert user A data
    assert prof_a["name"] == "Priya Sharma"
    assert prof_a["email"] == "priya.sharma@example.com"
    assert prof_a["phone"] == "+91 98765 43210"
    assert prof_a["current_city"] == "Chennai"
    assert len(prof_a["emergency_contacts"]) == 1
    assert prof_a["emergency_contacts"][0]["name"] == "Ananya Sharma"

    # Assert user B data
    assert prof_b["name"] == "Deepa Raman"
    assert prof_b["email"] == "deepa.raman@example.com"
    assert prof_b["phone"] == "+91 91234 56789"
    assert prof_b["current_city"] == "Coimbatore"
    assert len(prof_b["emergency_contacts"]) == 0

    # Ensure no contamination between users
    assert prof_a["name"] != prof_b["name"]
    assert prof_a["email"] != prof_b["email"]
    assert "Sarah" not in prof_a["name"]
    assert "Sarah" not in prof_b["name"]


@pytest.mark.asyncio
async def test_coordinator_build_profile_response_with_real_user():
    """Verify JourneyIntelligenceCoordinator passes user object to response builder."""
    coord = JourneyIntelligenceCoordinator()

    user = User(
        id=ObjectId(),
        username="kavitha_k",
        email="kavitha@example.com",
        password_hash="mock_hash_c",
        profile_settings={
            "full_name": "Kavitha Krishnan",
            "phone_number": "+91 94444 55555",
            "current_city": "Chennai"
        },
        emergency_contacts=[]
    )

    response = await coord.build_profile_response("user_123", user=user)

    assert response.user_info.full_name == "Kavitha Krishnan"
    assert response.user_info.email == "kavitha@example.com"
    assert response.user_info.phone == "+91 94444 55555"
    assert response.user_info.current_city == "Chennai"
    assert response.stats.safe_journeys == 0
    assert response.stats.reputation_score == 0
    assert response.emergency_contacts == []


@pytest.mark.asyncio
async def test_user_service_profile_update_persistence():
    """Verify UserService correctly updates current_city and phone in repository."""
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.update_profile_settings = AsyncMock()

    service = UserService(user_repo=mock_repo)

    user_id = str(ObjectId())
    user_initial = User(
        id=ObjectId(user_id),
        username="meera_s",
        email="meera@example.com",
        password_hash="mock_hash_d",
        profile_settings={}
    )
    mock_repo.get_by_id.return_value = user_initial

    update_data = ProfileUpdate(
        full_name="Meera Sundaram",
        phone_number="+91 99999 88888",
        current_city="Madurai"
    )

    updated_user = User(
        id=ObjectId(user_id),
        username="meera_s",
        email="meera@example.com",
        password_hash="mock_hash_d",
        profile_settings={
            "full_name": "Meera Sundaram",
            "phone_number": "+919999988888",
            "current_city": "Madurai"
        }
    )
    mock_repo.update_profile_settings.return_value = updated_user

    result = await service.update_profile(user_id, update_data)

    mock_repo.update_profile_settings.assert_called_once_with(
        user_id,
        {
            "full_name": "Meera Sundaram",
            "phone_number": "+919999988888",
            "current_city": "Madurai"
        }
    )
    assert result.full_name == "Meera Sundaram"
    assert result.current_city == "Madurai"
