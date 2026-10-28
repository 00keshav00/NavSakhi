import pytest
from bson import ObjectId

from app.models.user import User
from app.models.journey import (
    Journey, JourneyState, JourneyStateEnum, Location, 
    JourneyPlan, SelectedRoute, TransportMode
)
from app.repositories.base import BaseRepository
from app.repositories.journey_repository import JourneyRepository
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator


@pytest.fixture(autouse=True)
def clean_stores():
    """Ensure in-memory repository stores are clean for each test."""
    BaseRepository._global_store.clear()
    BaseRepository._global_store["users"] = {}
    BaseRepository._global_store["journeys"] = {}
    BaseRepository._global_store["community_reports"] = {}
    yield
    BaseRepository._global_store.clear()


@pytest.mark.asyncio
async def test_completed_journeys_semantics_and_backward_compatibility():
    """Verify that completed journeys populate completed_journeys and maintain safe_journeys alias."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="semantic_tester",
        email="semantic@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()
    journey_repo = JourneyRepository(None)

    # Create 2 completed journeys
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
                geometry_reference="g",
                status="SELECTED",
                safety_score=85.0
            )
        )
    )
    j2 = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2100, 13.0100]),
        destination=Location(coordinates=[80.2600, 13.0600]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.BUS,
            selected_route=SelectedRoute(
                route_identifier="r2",
                distance=4500.0,
                duration=1200.0,
                geometry_reference="g",
                status="SELECTED",
                safety_score=90.0
            )
        )
    )
    await journey_repo.create(j1)
    await journey_repo.create(j2)

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user, journey_repo=journey_repo)

    # Truthful metric: completed_journeys
    assert profile.stats.completed_journeys == 2
    # Preserved backward compatibility: safe_journeys
    assert profile.stats.safe_journeys == 2
    assert profile.stats.total_distance_km == 7.5
    assert profile.stats.avg_safety_score == 87.5


@pytest.mark.asyncio
async def test_non_completed_states_not_counted_as_completed():
    """Verify that only COMPLETED journeys increment completed_journeys and safe_journeys."""
    uid = str(ObjectId())
    user = User(
        id=ObjectId(uid),
        username="states_tester",
        email="states@example.com",
        password_hash="mock_hash",
        emergency_contacts=[]
    )
    BaseRepository._global_store["users"][uid] = user.model_dump()
    journey_repo = JourneyRepository(None)

    non_completed_states = [
        JourneyStateEnum.CREATED,
        JourneyStateEnum.PLANNING,
        JourneyStateEnum.PLANNED,
        JourneyStateEnum.ACTIVE,
        JourneyStateEnum.MONITORING,
        JourneyStateEnum.REROUTING,
        JourneyStateEnum.FAILED,
        JourneyStateEnum.CANCELLED,
        JourneyStateEnum.PAUSED
    ]

    for idx, state_enum in enumerate(non_completed_states):
        j = Journey(
            user_id=ObjectId(uid),
            source=Location(coordinates=[80.2000, 13.0000]),
            destination=Location(coordinates=[80.2500, 13.0500]),
            state=JourneyState(current_state=state_enum),
            plan=JourneyPlan(
                transport_mode=TransportMode.WALK,
                selected_route=SelectedRoute(
                    route_identifier=f"r_{idx}",
                    distance=2000.0,
                    duration=1000.0,
                    geometry_reference="g",
                    status="SELECTED",
                    safety_score=80.0
                )
            )
        )
        await journey_repo.create(j)

    coord = JourneyIntelligenceCoordinator()
    profile = await coord.build_profile_response(uid, user=user, journey_repo=journey_repo)

    # None of the non-completed states must be counted
    assert profile.stats.completed_journeys == 0
    assert profile.stats.safe_journeys == 0
    assert profile.stats.total_distance_km == 0.0
    assert profile.stats.avg_safety_score == 0.0


@pytest.mark.asyncio
async def test_repository_calculate_user_metrics_contract():
    """Verify calculate_user_metrics returns both completed_journeys and safe_journeys."""
    uid = str(ObjectId())
    journey_repo = JourneyRepository(None)

    metrics_empty = await journey_repo.calculate_user_metrics(uid)
    assert metrics_empty["completed_journeys"] == 0
    assert metrics_empty["safe_journeys"] == 0
    assert metrics_empty["total_distance_km"] == 0.0
    assert metrics_empty["avg_safety_score"] == 0.0
    assert metrics_empty["has_records"] is False

    j = Journey(
        user_id=ObjectId(uid),
        source=Location(coordinates=[80.2000, 13.0000]),
        destination=Location(coordinates=[80.2500, 13.0500]),
        state=JourneyState(current_state=JourneyStateEnum.COMPLETED),
        plan=JourneyPlan(
            transport_mode=TransportMode.WALK,
            selected_route=SelectedRoute(
                route_identifier="r_single",
                distance=1500.0,
                duration=900.0,
                geometry_reference="g",
                status="SELECTED",
                safety_score=95.0
            )
        )
    )
    await journey_repo.create(j)

    metrics_one = await journey_repo.calculate_user_metrics(uid)
    assert metrics_one["completed_journeys"] == 1
    assert metrics_one["safe_journeys"] == 1
    assert metrics_one["total_distance_km"] == 1.5
    assert metrics_one["avg_safety_score"] == 95.0
    assert metrics_one["has_records"] is True
