import uuid
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.base import MongoBaseModel

class EmergencyContact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone_number: str
    relationship: Optional[str] = "Family"
    email: Optional[str] = None
    is_primary: bool = False

class UserPreferences(BaseModel):
    default_transport_mode: str = "walking"
    receive_notifications: bool = True
    share_location_during_sos: bool = True

class User(MongoBaseModel):
    username: str
    email: str
    password_hash: str
    profile_settings: dict = {}
    preferences: UserPreferences = UserPreferences()
    emergency_contacts: List[EmergencyContact] = []
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    is_active: bool = True

    @property
    def full_name(self) -> str:
        return self.profile_settings.get("full_name") or self.username

    @property
    def phone_number(self) -> str:
        return self.profile_settings.get("phone_number") or ""

    @property
    def current_city(self) -> str:
        return self.profile_settings.get("current_city") or "Not provided"

