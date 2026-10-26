from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.base import BaseRepository
from app.models.user import User, EmergencyContact, UserPreferences
from typing import Optional, List
from bson import ObjectId

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "users", User)

    async def get_by_email(self, email: str) -> Optional[User]:
        for doc in self._store.values():
            if doc.get("email", "").lower() == email.lower():
                return self.model(**doc)
        try:
            doc = await self.collection.find_one({"email": email})
            if doc:
                return self.model(**doc)
        except Exception:
            pass
        return None
        
    async def get_emergency_contacts(self, user_id: str) -> List[EmergencyContact]:
        user = await self.get_by_id(user_id)
        if user:
            return user.emergency_contacts
        return []

    async def add_emergency_contact(self, user_id: str, contact: EmergencyContact) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        current_contacts = list(user.emergency_contacts)
        if contact.is_primary:
            for c in current_contacts:
                c.is_primary = False

        current_contacts.append(contact)
        contacts_dump = [c.model_dump() for c in current_contacts]

        if str(user_id) in self._store:
            self._store[str(user_id)]["emergency_contacts"] = contacts_dump

        if self.collection is not None and ObjectId.is_valid(user_id):
            try:
                await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"emergency_contacts": contacts_dump}}
                )
            except Exception:
                pass

        return await self.get_by_id(user_id)

    async def update_emergency_contact(self, user_id: str, contact_id: str, updated_contact: EmergencyContact) -> Optional[User]:
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
        contacts_dump = [c.model_dump() for c in current_contacts]

        if str(user_id) in self._store:
            self._store[str(user_id)]["emergency_contacts"] = contacts_dump

        if self.collection is not None and ObjectId.is_valid(user_id):
            try:
                await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"emergency_contacts": contacts_dump}}
                )
            except Exception:
                pass

        return await self.get_by_id(user_id)

    async def delete_emergency_contact(self, user_id: str, contact_id: str) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        current_contacts = [c for c in user.emergency_contacts if c.id != contact_id]
        if len(current_contacts) == len(user.emergency_contacts):
            return None

        contacts_dump = [c.model_dump() for c in current_contacts]

        if str(user_id) in self._store:
            self._store[str(user_id)]["emergency_contacts"] = contacts_dump

        if self.collection is not None and ObjectId.is_valid(user_id):
            try:
                await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"emergency_contacts": contacts_dump}}
                )
            except Exception:
                pass

        return await self.get_by_id(user_id)

    async def update_profile_settings(self, user_id: str, profile_data: dict) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        current_settings = dict(user.profile_settings or {})
        for field in ("full_name", "phone_number", "current_city", "age"):
            if field in profile_data and profile_data[field] is not None:
                current_settings[field] = profile_data[field]


        if str(user_id) in self._store:
            self._store[str(user_id)]["profile_settings"] = current_settings

        if self.collection is not None and ObjectId.is_valid(user_id):
            try:
                await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"profile_settings": current_settings}}
                )
            except Exception:
                pass

        return await self.get_by_id(user_id)

    async def update_preferences(self, user_id: str, preferences: UserPreferences) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        pref_dict = preferences.model_dump()
        if str(user_id) in self._store:
            self._store[str(user_id)]["preferences"] = pref_dict

        if self.collection is not None and ObjectId.is_valid(user_id):
            try:
                await self.collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"preferences": pref_dict}}
                )
            except Exception:
                pass

        return await self.get_by_id(user_id)
