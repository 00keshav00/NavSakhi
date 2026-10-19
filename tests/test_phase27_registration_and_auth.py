import pytest
import re
from bson import ObjectId
from pydantic import ValidationError
from app.schemas.user_schemas import UserCreate, UserLogin
from app.services.user_service import UserService
from app.models.user import User, EmergencyContact
from app.api.exceptions import ConflictException, DatabaseUnavailableException
from app.services.auth_service import AuthService


class MockTestUserRepository:
    """Isolated test double for verifying UserService persistence logic."""
    def __init__(self):
        self.users = {}
        self.is_test_double = True

    async def get_by_email(self, email: str):
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_id(self, user_id: str):
        return self.users.get(str(user_id))

    async def create(self, user: User) -> User:
        user_id = str(ObjectId())
        user.id = ObjectId(user_id)
        self.users[user_id] = user
        return user


def test_registration_schema_valid_input():
    data = UserCreate(
        full_name="Priya Raman",
        email="priya@example.com",
        password="ValidPassword123!",
        confirm_password="ValidPassword123!",
        emergency_contact_name="Ananya Raman",
        emergency_contact_relationship="Family",
        emergency_contact_phone="+919876543210",
        acknowledged_limitations=True,
    )
    assert data.full_name == "Priya Raman"
    assert data.username == "Priya Raman"
    assert data.email == "priya@example.com"
    assert data.emergency_contact_phone == "+919876543210"


def test_registration_schema_rejects_short_password():
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            full_name="Priya Raman",
            email="priya@example.com",
            password="short",
            confirm_password="short",
            acknowledged_limitations=True,
        )
    assert "at least 8 characters" in str(exc.value)


def test_registration_schema_rejects_mismatched_password():
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            full_name="Priya Raman",
            email="priya@example.com",
            password="ValidPassword123!",
            confirm_password="DifferentPassword456!",
            acknowledged_limitations=True,
        )
    assert "Passwords do not match" in str(exc.value)


def test_registration_schema_rejects_malformed_phone():
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            full_name="Priya Raman",
            email="priya@example.com",
            password="ValidPassword123!",
            confirm_password="ValidPassword123!",
            emergency_contact_name="Ananya Raman",
            emergency_contact_phone="123",  # Too short
            acknowledged_limitations=True,
        )
    assert "valid phone number" in str(exc.value)


def test_registration_schema_requires_prototype_acknowledgement():
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            full_name="Priya Raman",
            email="priya@example.com",
            password="ValidPassword123!",
            confirm_password="ValidPassword123!",
            acknowledged_limitations=False,
        )
    assert "acknowledge the prototype limitations" in str(exc.value)


@pytest.mark.asyncio
async def test_registration_fails_safely_when_database_unconfigured():
    """
    Verifies that when MongoDB is unconfigured or unavailable,
    registration does NOT silently succeed with in-memory persistence.
    It must fail closed with DatabaseUnavailableException (503).
    """
    class UnconnectedUserRepository:
        def __init__(self):
            self.collection = None

    service = UserService(UnconnectedUserRepository())
    payload = UserCreate(
        full_name="Priya Raman",
        email="priya@example.com",
        password="ValidPassword123!",
        confirm_password="ValidPassword123!",
        acknowledged_limitations=True,
    )

    with pytest.raises(DatabaseUnavailableException) as exc:
        await service.register_user(payload)
    
    assert "Database configuration unavailable" in str(exc.value.message)
    assert exc.value.status_code == 503
    assert exc.value.error_code == "DATABASE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_registration_succeeds_with_test_double():
    """Verifies that an isolated test double allows registration testing."""
    repo = MockTestUserRepository()
    service = UserService(repo)
    payload = UserCreate(
        full_name="Deepa Sundaram",
        email="deepa@example.com",
        password="SecurePassword999!",
        confirm_password="SecurePassword999!",
        emergency_contact_name="Kavitha Sundaram",
        emergency_contact_relationship="Sister",
        emergency_contact_phone="+919840123456",
        acknowledged_limitations=True,
    )

    user = await service.register_user(payload)
    assert user.email == "deepa@example.com"
    assert user.username == "Deepa Sundaram"
    assert len(user.emergency_contacts) == 1
    assert user.emergency_contacts[0].name == "Kavitha Sundaram"
    assert user.emergency_contacts[0].phone_number == "+919840123456"
    assert user.emergency_contacts[0].relationship == "Sister"
    assert AuthService.verify_password("SecurePassword999!", user.password_hash) is True
    assert user.password_hash != "SecurePassword999!"  # bcrypt hashed


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_email():
    """Verifies that duplicate registration returns a ConflictException (409)."""
    repo = MockTestUserRepository()
    service = UserService(repo)
    payload = UserCreate(
        full_name="User One",
        email="duplicate@example.com",
        password="SecurePassword123!",
        confirm_password="SecurePassword123!",
        acknowledged_limitations=True,
    )
    await service.register_user(payload)

    # Attempt second registration with same email
    with pytest.raises(ConflictException) as exc:
        await service.register_user(payload)
    assert "already exists" in str(exc.value.message)
