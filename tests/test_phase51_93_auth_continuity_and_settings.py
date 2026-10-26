import pytest
from bson import ObjectId
from pydantic import ValidationError
from app.models.user import User, EmergencyContact, UserPreferences
from app.schemas.user_schemas import (
    UserCreate, ProfileUpdate, EmergencyContactCreate, EmergencyContactUpdate
)
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.api.exceptions import ResourceNotFoundException, ConflictException


class InMemoryTestUserRepository:
    """Isolated repository double for Phase 51.93 unit and regression testing."""
    def __init__(self):
        self.users = {}
        self.is_test_double = True
        self.collection = None

    async def get_by_id(self, user_id: str):
        return self.users.get(str(user_id))

    async def get_by_email(self, email: str):
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def create(self, user: User) -> User:
        user_id = str(ObjectId())
        user.id = ObjectId(user_id)
        self.users[user_id] = user
        return user

    async def get_emergency_contacts(self, user_id: str):
        user = await self.get_by_id(user_id)
        if user:
            return user.emergency_contacts
        return []

    async def add_emergency_contact(self, user_id: str, contact: EmergencyContact):
        user = await self.get_by_id(user_id)
        if not user:
            return None
        current_contacts = list(user.emergency_contacts)
        if contact.is_primary:
            for c in current_contacts:
                c.is_primary = False
        current_contacts.append(contact)
        user.emergency_contacts = current_contacts
        self.users[str(user_id)] = user
        return user

    async def update_emergency_contact(self, user_id: str, contact_id: str, updated_contact: EmergencyContact):
        user = await self.get_by_id(user_id)
        if not user:
            return None
        target_idx = None
        for idx, c in enumerate(user.emergency_contacts):
            if c.id == contact_id:
                target_idx = idx
                break
        if target_idx is None:
            return None

        current_contacts = list(user.emergency_contacts)
        if updated_contact.is_primary:
            for c in current_contacts:
                c.is_primary = False
        updated_contact.id = contact_id
        current_contacts[target_idx] = updated_contact
        user.emergency_contacts = current_contacts
        self.users[str(user_id)] = user
        return user

    async def delete_emergency_contact(self, user_id: str, contact_id: str):
        user = await self.get_by_id(user_id)
        if not user:
            return None
        current_contacts = [c for c in user.emergency_contacts if c.id != contact_id]
        if len(current_contacts) == len(user.emergency_contacts):
            return None
        user.emergency_contacts = current_contacts
        self.users[str(user_id)] = user
        return user

    async def update_profile_settings(self, user_id: str, profile_data: dict):
        user = await self.get_by_id(user_id)
        if not user:
            return None
        current_settings = dict(user.profile_settings or {})
        for field in ("full_name", "phone_number", "age"):
            if field in profile_data and profile_data[field] is not None:
                current_settings[field] = profile_data[field]
        user.profile_settings = current_settings
        self.users[str(user_id)] = user
        return user


@pytest.fixture
def test_repo():
    return InMemoryTestUserRepository()


@pytest.fixture
def user_service(test_repo):
    return UserService(test_repo)


# =========================================================================
# 1. Profile Field Validation and Immutability Tests
# =========================================================================

def test_profile_update_schema_accepts_valid_inputs():
    update = ProfileUpdate(
        full_name="Ananya Raman",
        phone_number="+919876543210",
        age=24
    )
    assert update.full_name == "Ananya Raman"
    assert update.phone_number == "+919876543210"
    assert update.age == 24


def test_profile_update_schema_rejects_invalid_age():
    with pytest.raises(ValidationError) as exc:
        ProfileUpdate(age=8)  # Too young
    assert "Age must be between 13 and 120" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        ProfileUpdate(age=130)  # Too old
    assert "Age must be between 13 and 120" in str(exc2.value)


def test_profile_update_schema_rejects_malformed_phone():
    with pytest.raises(ValidationError) as exc:
        ProfileUpdate(phone_number="12345")  # Too short
    assert "Phone number must be a valid number" in str(exc.value)


@pytest.mark.asyncio
async def test_profile_update_persists_editable_fields_only(user_service):
    # Register user
    reg = UserCreate(
        full_name="Deepa S",
        email="deepa@example.com",
        password="SecurePassword123!",
        confirm_password="SecurePassword123!",
        acknowledged_limitations=True,
    )
    user = await user_service.register_user(reg)
    user_id = str(user.id)

    # Perform profile update
    update_data = ProfileUpdate(
        full_name="Deepa Sundaram",
        phone_number="+919876500000",
        age=28,
    )
    updated_user = await user_service.update_profile(user_id, update_data)

    assert updated_user.profile_settings["full_name"] == "Deepa Sundaram"
    assert updated_user.profile_settings["phone_number"] == "+919876500000"
    assert updated_user.profile_settings["age"] == 28

    # Immutable fields MUST remain untouched
    assert updated_user.username == "Deepa S"
    assert updated_user.email == "deepa@example.com"


# =========================================================================
# 2. Emergency Contacts Management & Primary Exclusivity Tests
# =========================================================================

def test_emergency_contact_create_validation():
    # Valid
    c = EmergencyContactCreate(
        name="Kavitha Sundaram",
        phone_number="+919876543211",
        relationship="Sister",
        email="kavitha@example.com",
        is_primary=True
    )
    assert c.name == "Kavitha Sundaram"
    assert c.phone_number == "+919876543211"
    assert c.is_primary is True

    # Invalid phone
    with pytest.raises(ValidationError):
        EmergencyContactCreate(name="Kavitha", phone_number="987")

    # Name too short
    with pytest.raises(ValidationError):
        EmergencyContactCreate(name="K", phone_number="+919876543211")


@pytest.mark.asyncio
async def test_add_multiple_emergency_contacts_with_primary_exclusivity(user_service):
    reg = UserCreate(
        full_name="Maya Krishnan",
        email="maya@example.com",
        password="SecurePassword123!",
        confirm_password="SecurePassword123!",
        emergency_contact_name="Initial Contact",
        emergency_contact_phone="+919876543210",
        acknowledged_limitations=True,
    )
    user = await user_service.register_user(reg)
    user_id = str(user.id)

    # Initial contact from registration is set as primary
    assert len(user.emergency_contacts) == 1
    assert user.emergency_contacts[0].is_primary is True
    first_id = user.emergency_contacts[0].id

    # Add a second contact marked as primary
    second_contact = EmergencyContact(
        name="Sunita Krishnan",
        phone_number="+919876543299",
        relationship="Mother",
        is_primary=True,
    )
    user_after_add = await user_service.add_emergency_contact(user_id, second_contact)
    assert len(user_after_add.emergency_contacts) == 2

    # Second contact is now primary; first contact's primary status was safely unset
    c1 = next(c for c in user_after_add.emergency_contacts if c.id == first_id)
    c2 = next(c for c in user_after_add.emergency_contacts if c.id == second_contact.id)
    assert c1.is_primary is False
    assert c2.is_primary is True


@pytest.mark.asyncio
async def test_update_and_delete_emergency_contact(user_service):
    reg = UserCreate(
        full_name="Radha Nair",
        email="radha@example.com",
        password="SecurePassword123!",
        confirm_password="SecurePassword123!",
        emergency_contact_name="Brother",
        emergency_contact_phone="+919876543210",
        acknowledged_limitations=True,
    )
    user = await user_service.register_user(reg)
    user_id = str(user.id)
    contact_id = user.emergency_contacts[0].id

    # Update contact name and relationship
    updated_contact = EmergencyContact(
        id=contact_id,
        name="Rohan Nair",
        phone_number="+919876543210",
        relationship="Brother",
        email="rohan@example.com",
        is_primary=True,
    )
    user_after_update = await user_service.update_emergency_contact(user_id, contact_id, updated_contact)
    assert user_after_update.emergency_contacts[0].name == "Rohan Nair"
    assert user_after_update.emergency_contacts[0].email == "rohan@example.com"

    # Delete contact
    user_after_delete = await user_service.delete_emergency_contact(user_id, contact_id)
    assert len(user_after_delete.emergency_contacts) == 0

    # Deleting again raises ResourceNotFoundException
    with pytest.raises(ResourceNotFoundException):
        await user_service.delete_emergency_contact(user_id, contact_id)


# =========================================================================
# 3. Security & Cross-User Data Isolation Tests
# =========================================================================

@pytest.mark.asyncio
async def test_user_cannot_access_or_modify_another_users_contacts(user_service):
    # Create User A
    user_a = await user_service.register_user(UserCreate(
        full_name="User Alpha",
        email="alpha@example.com",
        password="PasswordAlpha123!",
        confirm_password="PasswordAlpha123!",
        emergency_contact_name="Alpha Contact",
        emergency_contact_phone="+919876500001",
        acknowledged_limitations=True,
    ))

    # Create User B
    user_b = await user_service.register_user(UserCreate(
        full_name="User Beta",
        email="beta@example.com",
        password="PasswordBeta123!",
        confirm_password="PasswordBeta123!",
        emergency_contact_name="Beta Contact",
        emergency_contact_phone="+919876500002",
        acknowledged_limitations=True,
    ))

    user_a_contact_id = user_a.emergency_contacts[0].id

    # User B attempting to modify User A's contact ID under User B's account must fail
    with pytest.raises(ResourceNotFoundException):
        await user_service.update_emergency_contact(
            str(user_b.id),
            user_a_contact_id,
            EmergencyContact(
                id=user_a_contact_id,
                name="Hacked Name",
                phone_number="+919999999999",
                relationship="Unknown"
            )
        )

    # User A's contact remains unmodified
    refreshed_a = await user_service.get_user_profile(str(user_a.id))
    assert refreshed_a.emergency_contacts[0].name == "Alpha Contact"
    assert refreshed_a.emergency_contacts[0].phone_number == "+919876500001"
