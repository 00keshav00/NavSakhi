from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.base import MongoBaseModel

class EmergencyContact(BaseModel):
    name: str
    phone_number: str
    relationship: Optional[str] = None

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
