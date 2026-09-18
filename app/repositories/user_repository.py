from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.user import User, EmergencyContact, UserPreferences
from typing import Optional, List
from bson import ObjectId

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users", User)

    async def get_by_email(self, email: str) -> Optional[User]:
        doc = await self.collection.find_one({"email": email})
        if doc:
            return self.model(**doc)
        return None
        
    async def get_emergency_contacts(self, user_id: str) -> List[EmergencyContact]:
        user = await self.get_by_id(user_id)
        if user:
            return user.emergency_contacts
        return []

    async def add_emergency_contact(self, user_id: str, contact: EmergencyContact) -> Optional[User]:
        if not ObjectId.is_valid(user_id):
            return None
        contact_dict = contact.model_dump()
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"emergency_contacts": contact_dict}}
        )
        if result.modified_count > 0:
            return await self.get_by_id(user_id)
        return None

    async def update_preferences(self, user_id: str, preferences: UserPreferences) -> Optional[User]:
        if not ObjectId.is_valid(user_id):
            return None
        pref_dict = preferences.model_dump()
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"preferences": pref_dict}}
        )
        if result.modified_count > 0:
            return await self.get_by_id(user_id)
        return None
