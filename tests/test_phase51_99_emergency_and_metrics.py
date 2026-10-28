import pytest
from bson import ObjectId
from unittest.mock import MagicMock, AsyncMock

from app.models.user import User, EmergencyContact as ModelEmergencyContact
from app.models.journey import (
    Journey, JourneyState, JourneyStateEnum, Location, 
    JourneyPlan, SelectedRoute, TransportMode
)
from app.repositories.base import BaseRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.community_repository import CommunityRepository
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator
from app.intelligence.response.builder import ResponseBuilder
from app.services.emergency_session_service import emergency_session_registry


@pytest.fixture(autouse=True)
def clean_stores():
    """Ensure in-memory repository stores and session registry are clean for each test."""
    BaseRepository._global_store.clear()
    BaseRepository._global_store["users"] = {}
    BaseRepository._global_store["journeys"] = {}
    BaseRepository._global_store["community_reports"] = {}
    emergency_session_registry.clear()
    yield
    BaseRepository._global_store.clear()
    emergency_session_registry.clear()


# ============================================================================
# PART 1: Emergency Data Integrity Tests
# ============================================================================

@pytest.mark.asyncio
async def test_emergency_status_with_real_saved_contact():
    """User with a real saved contact receives genuine contact data without Sarah Connor."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="priya_s",
        email="priya@example.com",
        password_hash="mock_hash",
        emergency_contacts=[
            ModelEmergencyContact(
                id="c_priya_1",
                name="Priya Sharma",
                phone_number="+91 98765 43210",
                relationship="Sister",
                is_primary=True
            )
        ]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    session_id = "test_sess_01"
    emergency_session_registry.register_session(
        session_id=session_id,
        user_id=uid,
        current_location="13.0850, 80.2100"
    )

    coord = JourneyIntelligenceCoordinator()
    response = await coord.build_emergency_status(session_id, uid)

    # Assert genuine contact present
    assert len(response.contacts) == 1
    assert response.contacts[0].name == "Priya Sharma"
    assert response.contacts[0].relationship == "Sister"
    assert response.contacts[0].notification_status == "Pending"

    # Assert NO fabricated demo data
    assert "Sarah Connor" not in [c.name for c in response.contacts]
    assert response.contacts[0].id != "c1"

    # Assert location parsed from actual session
    assert response.live_location.coordinates is not None
    assert response.live_location.coordinates == (80.2100, 13.0850)
    assert "Poonamallee" not in response.live_location.address


@pytest.mark.asyncio
async def test_emergency_status_with_no_contacts():
    """User with no emergency contacts clearly reports that no contact is configured."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="solo_traveler",
        email="solo@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    session_id = "test_sess_02"
    emergency_session_registry.register_session(
        session_id=session_id,
        user_id=uid
    )

    coord = JourneyIntelligenceCoordinator()
    response = await coord.build_emergency_status(session_id, uid)

    assert response.contacts == []
    assert "Sarah" not in str(response.contacts)
    assert response.agent_status.action == "No Emergency Contacts Configured"
    assert "112" in response.agent_status.recommendation


@pytest.mark.asyncio
async def test_emergency_status_with_unavailable_location():
    """Missing or unprovided location clearly reports unavailable state without demo coordinates."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="no_gps_user",
        email="nogps@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    session_id = "test_sess_03"
    emergency_session_registry.register_session(
        session_id=session_id,
        user_id=uid,
        current_location=None  # Explicitly no location
    )

    coord = JourneyIntelligenceCoordinator()
    response = await coord.build_emergency_status(session_id, uid)

    assert response.live_location.coordinates is None
    assert "Location unavailable" in response.live_location.address
    assert response.live_location.accuracy == 0
    assert response.live_location.last_updated == "Unavailable"

    # Assert no fabricated demo coordinates
    assert response.live_location.coordinates != (80.2707, 13.0827)
    assert "Poonamallee" not in response.live_location.address

    # Assert no fabricated safe zone police station at demo coordinates
    assert response.safe_zones == []


@pytest.mark.asyncio
async def test_emergency_status_two_user_isolation():
    """Emergency contacts cannot leak between different accounts."""
    uid_a = str(ObjectId())
    uid_b = str(ObjectId())

    user_a = User(
        id=ObjectId(uid_a),
        username="user_a",
        email="a@example.com",
        password_hash="mock_hash",
        emergency_contacts=[
            ModelEmergencyContact(name="Ananya (Contact A)", phone_number="+91 91111 11111", relationship="Friend")
        ]
    )
    user_b = User(
        id=ObjectId(uid_b),
        username="user_b",
        email="b@example.com",
        password_hash="mock_hash",
        emergency_contacts=[
            ModelEmergencyContact(name="Deepa (Contact B)", phone_number="+91 92222 22222", relationship="Mother")
        ]
    )
    BaseRepository._global_store["users"][uid_a] = user_a.model_dump()
    BaseRepository._global_store["users"][uid_b] = user_b.model_dump()

    sess_a = "sess_a"
    sess_b = "sess_b"
    emergency_session_registry.register_session(session_id=sess_a, user_id=uid_a)
    emergency_session_registry.register_session(session_id=sess_b, user_id=uid_b)

    coord = JourneyIntelligenceCoordinator()
    resp_a = await coord.build_emergency_status(sess_a, uid_a)
    resp_b = await coord.build_emergency_status(sess_b, uid_b)

    assert len(resp_a.contacts) == 1
    assert resp_a.contacts[0].name == "Ananya (Contact A)"
    assert "Deepa" not in str(resp_a.contacts)
    assert "Sarah" not in str(resp_a.contacts)

    assert len(resp_b.contacts) == 1
    assert resp_b.contacts[0].name == "Deepa (Contact B)"
    assert "Ananya" not in str(resp_b.contacts)
    assert "Sarah" not in str(resp_b.contacts)


# ============================================================================
# PART 2: Real Profile Metrics & History Aggregation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_profile_metrics_new_user():
    """A new user with zero records has honest 0 counts and 'New Member' trust level."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="brand_new_user",
        email="new@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user)

    assert profile.stats.safe_journeys == 0
    assert profile.stats.total_distance_km == 0.0
    assert profile.stats.avg_safety_score == 0.0
    assert profile.stats.reputation_score == 0
    assert profile.stats.trust_level == "New Member"
    assert profile.journey_history == []
    assert all(not a.unlocked for a in profile.achievements)


@pytest.mark.asyncio
async def test_profile_metrics_multiple_completed_journeys():
    """User with multiple completed journeys calculates real aggregates accurately."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="frequent_traveler",
        email="traveler@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    journey_repo = JourneyRepository(None)

    # Create 3 completed journeys
    j1 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2000, 13.0000]),
        destination=Location(coordinates=[80.2500, 13.0500]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r1",
                distance=5200.0,  # 5.2 km
                duration=3600.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=88.0
            )
        )
    )
    j2 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2100, 13.0100]),
        destination=Location(coordinates=[80.2600, 13.0600]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.METRO,
            selected_route=SelectedRoute(
                route_identifier="r2",
                distance=3800.0,  # 3.8 km
                duration=1200.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=92.0
            )
        )
    )
    j3 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2200, 13.0200]),
        destination=Location(coordinates=[80.2700, 13.0700]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.BUS,
            selected_route=SelectedRoute(
                route_identifier="r3",
                distance=4000.0,  # 4.0 km
                duration=1800.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=90.0
            )
        )
    )

    await journey_repo.create(j1)
    await journey_repo.create(j2)
    await journey_repo.create(j3)

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user, journey_repo=journey_repo)

    assert profile.stats.safe_journeys == 3
    assert profile.stats.total_distance_km == 13.0  # 5.2 + 3.8 + 4.0
    assert profile.stats.avg_safety_score == 90.0   # (88 + 92 + 90) / 3
    assert profile.stats.reputation_score == 30     # 3 * 10
    assert profile.stats.trust_level == "Active Member"

    # Journey history contains genuine completed journeys
    assert len(profile.journey_history) == 3
    assert all(jh.status == "Completed" for jh in profile.journey_history)

    # First Step achievement unlocked
    first_step = next(a for a in profile.achievements if a.id == "a1")
    assert first_step.unlocked is True


@pytest.mark.asyncio
async def test_profile_metrics_ignores_cancelled_and_incomplete_journeys():
    """Incomplete, cancelled, or active journeys are NOT counted as completed safe journeys."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="mixed_user",
        email="mixed@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    journey_repo = JourneyRepository(None)

    # 1 Completed
    j_done = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2000, 13.0000]),
        destination=Location(coordinates=[80.2500, 13.0500]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r1",
                distance=2500.0,
                duration=1800.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=85.0
            )
        )
    )
    # 1 Cancelled
    j_cancelled = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2100, 13.0100]),
        destination=Location(coordinates=[80.2600, 13.0600]),
        state=JourneyState(current_state=JourneyStateEnum.CANCELLED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r2",
                distance=5000.0,
                duration=3600.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=60.0
            )
        )
    )
    # 1 Active
    j_active = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2200, 13.0200]),
        destination=Location(coordinates=[80.2700, 13.0700]),
        state=JourneyState(current_state=JourneyStateEnum.ACTIVE),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r3",
                distance=4000.0,
                duration=2000.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=75.0
            )
        )
    )

    await journey_repo.create(j_done)
    await journey_repo.create(j_cancelled)
    await journey_repo.create(j_active)

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user, journey_repo=journey_repo)

    # Only 1 completed safe journey counted
    assert profile.stats.safe_journeys == 1
    assert profile.stats.total_distance_km == 2.5
    assert profile.stats.avg_safety_score == 85.0
    assert profile.stats.trust_level == "Verified Traveler"


@pytest.mark.asyncio
async def test_profile_metrics_handles_malformed_values_safely():
    """Malformed distances and missing safety scores are handled safely without crash."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="edge_case_user",
        email="edge@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()

    journey_repo = JourneyRepository(None)

    # Journey 1: valid distance, missing safety score
    j1 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2000, 13.0000]),
        destination=Location(coordinates=[80.2500, 13.0500]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r1",
                distance=3000.0,
                duration=1800.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=None  # Missing
            )
        )
    )
    # Journey 2: negative/malformed distance, valid safety score
    j2 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2100, 13.0100]),
        destination=Location(coordinates=[80.2600, 13.0600]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r2",
                distance=-50.0,  # Invalid negative distance
                duration=1200.0,
                geometry_reference="geom",
                status="SELECTED",
                safety_score=82.0
            )
        )
    )

    await journey_repo.create(j1)
    await journey_repo.create(j2)

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user, journey_repo=journey_repo)

    assert profile.stats.safe_journeys == 2
    # Only valid distance (3.0 km) summed; negative distance ignored
    assert profile.stats.total_distance_km == 3.0
    # Only valid safety score (82.0) used; None ignored
    assert profile.stats.avg_safety_score == 82.0


@pytest.mark.asyncio
async def test_profile_metrics_two_user_isolation():
    """Metrics strictly isolate each user's records with zero cross-user pollution."""
    uid_a = str(ObjectId())
    uid_b = str(ObjectId())

    user_a = User(id=ObjectId(uid_a), username="user_a", email="a@ex.com", password_hash="h", emergency_contacts=[])
    user_b = User(id=ObjectId(uid_b), username="user_b", email="b@ex.com", password_hash="h", emergency_contacts=[])

    BaseRepository._global_store["users"][uid_a] = user_a.model_dump()
    BaseRepository._global_store["users"][uid_b] = user_b.model_dump()

    journey_repo = JourneyRepository(None)

    # 2 Completed journeys for User A
    j_a1 = Journey(
        user_id=ObjectId(uid_a),
        source=Location(coordinates=[80.2000, 13.0000]),
        destination=Location(coordinates=[80.2500, 13.0500]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(route_identifier="r_a1", distance=6000.0, duration=2400.0, geometry_reference="g", status="S", safety_score=95.0)
        )
    )
    j_a2 = Journey(
        user_id=ObjectId(uid_a),
        source=Location(coordinates=[80.2100, 13.0100]),
        destination=Location(coordinates=[80.2600, 13.0600]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(route_identifier="r_a2", distance=4000.0, duration=1600.0, geometry_reference="g", status="S", safety_score=85.0)
        )
    )

    await journey_repo.create(j_a1)
    await journey_repo.create(j_a2)

    coord = JourneyIntelligenceCoordinator()
    prof_a = await coord.build_profile_response(uid_a, user=user_a, journey_repo=journey_repo)
    prof_b = await coord.build_profile_response(uid_b, user=user_b, journey_repo=journey_repo)

    # User A has 2 journeys, 10.0 km, avg score 90.0
    assert prof_a.stats.safe_journeys == 2
    assert prof_a.stats.total_distance_km == 10.0
    assert prof_a.stats.avg_safety_score == 90.0

    # User B has 0 journeys, 0.0 km, avg score 0.0
    assert prof_b.stats.safe_journeys == 0
    assert prof_b.stats.total_distance_km == 0.0
    assert prof_b.stats.avg_safety_score == 0.0
