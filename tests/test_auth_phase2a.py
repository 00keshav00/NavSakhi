import pytest
from datetime import timedelta
import jwt
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import settings
from app.services.auth_service import AuthService
from app.models.user import User, UserPreferences
from app.models.journey import Journey, Location, JourneyState, JourneyStateEnum
from app.api.dependencies import get_user_repository, get_journey_repository
from app.api.exceptions import ResourceNotFoundException

class InMemoryUserRepository:
    def __init__(self):
        self.users = {}

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

    async def update_preferences(self, user_id: str, preferences: UserPreferences):
        user = self.users.get(str(user_id))
        if user:
            user.preferences = preferences
            return user
        return None

    async def add_emergency_contact(self, user_id: str, contact):
        user = self.users.get(str(user_id))
        if user:
            user.emergency_contacts.append(contact)
            return user
        return None


class InMemoryJourneyRepository:
    def __init__(self):
        self.journeys = {}

    async def get_by_id(self, journey_id: str):
        return self.journeys.get(str(journey_id))

    async def create(self, journey: Journey) -> Journey:
        j_id = str(ObjectId())
        journey.id = ObjectId(j_id)
        self.journeys[j_id] = journey
        return journey

    async def update_state(self, journey_id: str, new_state: JourneyStateEnum):
        j = self.journeys.get(str(journey_id))
        if j:
            j.state.current_state = new_state
            return j
        return None


@pytest.fixture
def mock_repos():
    user_repo = InMemoryUserRepository()
    journey_repo = InMemoryJourneyRepository()

    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_journey_repository] = lambda: journey_repo

    client = TestClient(app, raise_server_exceptions=False)
    yield client, user_repo, journey_repo

    app.dependency_overrides.clear()


# 1. Registration succeeds with valid input
def test_registration_succeeds_with_valid_input(mock_repos):
    client, user_repo, _ = mock_repos
    payload = {
        "username": "safety_advocate",
        "email": "advocate@safeshe.org",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "advocate@safeshe.org"
    assert data["data"]["username"] == "safety_advocate"
    assert "id" in data["data"]


# 2. A registered password is stored as a hash, not plaintext
def test_password_is_hashed_not_plaintext(mock_repos):
    client, user_repo, _ = mock_repos
    raw_password = "MySecretPassword2026!"
    payload = {
        "username": "hash_test_user",
        "email": "hash_test@safeshe.org",
        "password": raw_password
    }
    response = client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201

    # Inspect stored user object in repo
    user_id = response.json()["data"]["id"]
    stored_user = user_repo.users[user_id]
    assert stored_user.password_hash != raw_password
    assert stored_user.password_hash.startswith("$2b$")
    assert AuthService.verify_password(raw_password, stored_user.password_hash) is True


# 3. Valid credentials can log in
def test_valid_credentials_can_login(mock_repos):
    client, _, _ = mock_repos
    reg_payload = {
        "username": "login_user",
        "email": "login_test@safeshe.org",
        "password": "LoginSecret456!"
    }
    client.post("/api/v1/users/", json=reg_payload)

    # Test login endpoint
    login_payload = {
        "email": "login_test@safeshe.org",
        "password": "LoginSecret456!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "access_token" in res_data["data"]
    assert res_data["data"]["token_type"] == "bearer"
    assert res_data["data"]["user"]["email"] == "login_test@safeshe.org"


# 4. Invalid credentials are rejected with generic failure message
def test_invalid_credentials_rejected(mock_repos):
    client, _, _ = mock_repos
    reg_payload = {
        "username": "cred_user",
        "email": "cred_test@safeshe.org",
        "password": "CorrectPassword123!"
    }
    client.post("/api/v1/users/", json=reg_payload)

    # Wrong password
    bad_pw_response = client.post("/api/v1/auth/login", json={
        "email": "cred_test@safeshe.org",
        "password": "WrongPassword999!"
    })
    assert bad_pw_response.status_code == 401
    assert bad_pw_response.json()["success"] is False
    assert "Invalid email or password" in bad_pw_response.json()["error"]["message"]

    # Non-existent user (generic message must be identical)
    bad_user_response = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@safeshe.org",
        "password": "AnyPassword123!"
    })
    assert bad_user_response.status_code == 401
    assert bad_user_response.json()["success"] is False
    assert bad_user_response.json()["error"]["message"] == bad_pw_response.json()["error"]["message"]


# 5. Issued JWTs contain the expected identity and expiration
def test_issued_jwt_contains_identity_and_expiration(mock_repos):
    client, user_repo, _ = mock_repos
    email = "jwt_identity@safeshe.org"
    client.post("/api/v1/users/", json={
        "username": "jwt_user",
        "email": email,
        "password": "ValidPassword123!"
    })

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "ValidPassword123!"
    })
    token = login_res.json()["data"]["access_token"]

    payload = AuthService.decode_access_token(token)
    assert "sub" in payload
    assert payload["email"] == email
    assert payload["exp"] > payload["iat"]


# 6. Invalid signatures are rejected
def test_invalid_signature_rejected(mock_repos):
    client, _, _ = mock_repos
    # Generate token with fraudulent key
    fake_secret = "fraudulent_secret_key_that_does_not_match"
    payload = {
        "sub": "650c1f1e1c9d440000000000",
        "email": "hacker@safeshe.org",
        "iat": 1000000000,
        "exp": 2000000000
    }
    bad_token = jwt.encode(payload, fake_secret, algorithm="HS256")

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert "Invalid" in response.json()["error"]["message"]


# 7. Expired tokens are rejected
def test_expired_token_rejected(mock_repos):
    client, _, _ = mock_repos
    expired_token = AuthService.create_access_token(
        user_id="650c1f1e1c9d440000000000",
        email="expired@safeshe.org",
        expires_delta=timedelta(seconds=-10)
    )

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert "expired" in response.json()["error"]["message"].lower()


# 8. Protected endpoints reject missing credentials
def test_protected_endpoints_reject_missing_credentials(mock_repos):
    client, _, _ = mock_repos
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert "missing" in response.json()["error"]["message"].lower()


# 9. Protected endpoints reject invalid credentials
def test_protected_endpoints_reject_invalid_credentials(mock_repos):
    client, _, _ = mock_repos
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401
    assert response.json()["success"] is False


# 10. User A cannot access User B's protected resources (403 Forbidden)
def test_user_cannot_access_other_users_resources(mock_repos):
    client, user_repo, journey_repo = mock_repos

    # Create User A
    user_a = User(
        username="user_a",
        email="usera@safeshe.org",
        password_hash=AuthService.hash_password("PasswordA123!")
    )
    user_a = client.app.dependency_overrides[get_user_repository]().users.setdefault("650c1f1e1c9d440000000001", user_a)
    user_a.id = ObjectId("650c1f1e1c9d440000000001")
    user_repo.users["650c1f1e1c9d440000000001"] = user_a

    # Create User B
    user_b = User(
        username="user_b",
        email="userb@safeshe.org",
        password_hash=AuthService.hash_password("PasswordB123!")
    )
    user_b.id = ObjectId("650c1f1e1c9d440000000002")
    user_repo.users["650c1f1e1c9d440000000002"] = user_b

    # Create Journey belonging to User B
    journey_b = Journey(
        user_id=ObjectId("650c1f1e1c9d440000000002"),
        source=Location(coordinates=[77.5946, 12.9716]),
        destination=Location(coordinates=[77.6020, 12.9780]),
        state=JourneyState(current_state=JourneyStateEnum.CREATED)
    )
    journey_b.id = ObjectId("650c1f1e1c9d440000000099")
    journey_repo.journeys["650c1f1e1c9d440000000099"] = journey_b

    # Authenticate as User A
    token_a = AuthService.create_access_token(user_id="650c1f1e1c9d440000000001", email="usera@safeshe.org")

    # User A attempts to view User B's journey -> 403 Forbidden
    get_res = client.get(
        "/api/v1/journeys/650c1f1e1c9d440000000099",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert get_res.status_code == 403
    assert get_res.json()["success"] is False
    assert "permission" in get_res.json()["error"]["message"].lower()

    # User A attempts to cancel User B's journey -> 403 Forbidden
    cancel_res = client.post(
        "/api/v1/journeys/650c1f1e1c9d440000000099/cancel",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert cancel_res.status_code == 403
    assert cancel_res.json()["success"] is False

    # Authenticate as User B (the actual owner) -> 200 OK
    token_b = AuthService.create_access_token(user_id="650c1f1e1c9d440000000002", email="userb@safeshe.org")
    owner_res = client.get(
        "/api/v1/journeys/650c1f1e1c9d440000000099",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert owner_res.status_code == 200
    assert owner_res.json()["success"] is True


# 11. Password hashes are never included in returned user data
def test_password_hash_never_returned(mock_repos):
    client, _, _ = mock_repos
    reg_payload = {
        "username": "no_hash_leak",
        "email": "leaktst@safeshe.org",
        "password": "StrongSecretPassword99!"
    }
    reg_res = client.post("/api/v1/users/", json=reg_payload)
    assert "password" not in reg_res.json()["data"]
    assert "password_hash" not in reg_res.json()["data"]

    login_res = client.post("/api/v1/auth/login", json={
        "email": "leaktst@safeshe.org",
        "password": "StrongSecretPassword99!"
    })
    login_user = login_res.json()["data"]["user"]
    assert "password" not in login_user
    assert "password_hash" not in login_user

    # Profile me
    token = login_res.json()["data"]["access_token"]
    me_res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert "password" not in me_res.json()["data"]
    assert "password_hash" not in me_res.json()["data"]


# 12. Password input validation rejects weak passwords (<8 chars)
def test_password_validation_enforces_length(mock_repos):
    client, _, _ = mock_repos
    short_pw_payload = {
        "username": "short_pw_user",
        "email": "short@safeshe.org",
        "password": "short"
    }
    response = client.post("/api/v1/users/", json=short_pw_payload)
    assert response.status_code == 422
    assert response.json()["success"] is False
