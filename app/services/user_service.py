from app.repositories.user_repository import UserRepository
from app.models.user import User, EmergencyContact, UserPreferences
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.api.exceptions import ResourceNotFoundException

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_user_profile(self, user_id: str) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundException("User")
        return user

    async def register_user(self, data: UserCreate) -> User:
        user = User(
            username=data.username,
            email=data.email,
            password_hash=data.password # In real app, hash this
        )
        return await self.user_repo.create(user)

    async def update_preferences(self, user_id: str, data: UserUpdate) -> User:
        user = await self.get_user_profile(user_id)
        if data.preferences:
            user = await self.user_repo.update_preferences(user_id, data.preferences)
        return user

    async def add_emergency_contact(self, user_id: str, contact: EmergencyContact) -> User:
        # Business logic can go here (e.g. check max contacts)
        user = await self.user_repo.add_emergency_contact(user_id, contact)
        if not user:
            raise ResourceNotFoundException("User")
        return user
