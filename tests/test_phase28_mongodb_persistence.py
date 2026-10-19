import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.repositories.user_repository import UserRepository
from app.repositories.base import BaseRepository
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.schemas.user_schemas import UserCreate
from app.models.user import User, EmergencyContact
from app.api.exceptions import ConflictException, DatabaseUnavailableException, UnauthorizedException

class MockCollection:
    def __init__(self):
        self.docs = {}
        self.database = MagicMock()
        self.database.client.admin.command = AsyncMock(return_value={"ok": 1})

    async def insert_one(self, doc):
        self.docs[str(doc["_id"])] = doc.copy()
        mock_res = MagicMock()
        mock_res.inserted_id = doc["_id"]
        return mock_res

    async def find_one(self, query):
        for doc in self.docs.values():
            if "email" in query and doc.get("email") == query["email"]:
                return doc.copy()
            if "_id" in query and doc.get("_id") == query["_id"]:
                return doc.copy()
        return None

    async def update_one(self, query, update):
        for doc_id, doc in self.docs.items():
            if "_id" in query and doc.get("_id") == query["_id"]:
                if "$push" in update:
                    for k, v in update["$push"].items():
                        doc.setdefault(k, []).append(v)
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = v
                res = MagicMock()
                res.modified_count = 1
                return res
        res = MagicMock()
        res.modified_count = 0
        return res

    async def delete_one(self, query):
        to_del = None
        for doc_id, doc in self.docs.items():
            if "_id" in query and doc.get("_id") == query["_id"]:
                to_del = doc_id
                break
            if "email" in query and doc.get("email") == query["email"]:
                to_del = doc_id
                break
        if to_del:
            del self.docs[to_del]
            res = MagicMock()
            res.deleted_count = 1
            return res
        res = MagicMock()
        res.deleted_count = 0
        return res

@pytest.mark.asyncio
async def test_base_repository_mongodb_persistence():
    mock_coll = MockCollection()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    repo = UserRepository(mock_db)
    user = User(
        username="persist_user",
        email="persist@navsakhi.test",
        password_hash="$2b$12$fakepasswordhashforexampleonly",
        emergency_contacts=[EmergencyContact(name="Kavya", phone_number="+919876543210")]
    )
    
    created = await repo.create(user)
    assert created.id is not None
    assert str(created.id) in mock_coll.docs
    
    # Verify retrieval directly from mock collection
    retrieved = await repo.get_by_email("persist@navsakhi.test")
    assert retrieved is not None
    assert retrieved.email == "persist@navsakhi.test"
    assert len(retrieved.emergency_contacts) == 1
    assert retrieved.emergency_contacts[0].name == "Kavya"

@pytest.mark.asyncio
async def test_user_service_registration_persists_to_collection():
    mock_coll = MockCollection()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    repo = UserRepository(mock_db)
    service = UserService(repo)

    dto = UserCreate(
        full_name="Aishwarya Mohan",
        email="aishwarya@example.org",
        password="ValidPassword123!",
        confirm_password="ValidPassword123!",
        emergency_contact_name="Deepa Mohan",
        emergency_contact_relationship="Family",
        emergency_contact_phone="9876543210",
        acknowledged_limitations=True
    )

    registered = await service.register_user(dto)
    assert registered.email == "aishwarya@example.org"
    
    # Must be in mock_coll
    assert str(registered.id) in mock_coll.docs
    doc = mock_coll.docs[str(registered.id)]
    assert doc["password_hash"] != "ValidPassword123!"
    assert AuthService.verify_password("ValidPassword123!", doc["password_hash"])
    assert "confirm_password" not in doc
    assert "acknowledged_limitations" not in doc

@pytest.mark.asyncio
async def test_auth_service_authenticates_persisted_user():
    mock_coll = MockCollection()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    repo = UserRepository(mock_db)
    service = UserService(repo)

    dto = UserCreate(
        full_name="Geetha Ramesh",
        email="geetha@example.org",
        password="SecurePass987!",
        confirm_password="SecurePass987!",
        acknowledged_limitations=True
    )
    await service.register_user(dto)

    # Clear in-memory repo store to force collection read
    BaseRepository._global_store["users"] = {}

    auth_user = await AuthService.authenticate_user(repo, "geetha@example.org", "SecurePass987!")
    assert auth_user.email == "geetha@example.org"

    with pytest.raises(UnauthorizedException):
        await AuthService.authenticate_user(repo, "geetha@example.org", "WrongPassword!")
