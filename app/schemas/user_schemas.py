from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.models.user import EmergencyContact, UserPreferences

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    preferences: UserPreferences
    emergency_contacts: List[EmergencyContact]

class UserUpdate(BaseModel):
    preferences: Optional[UserPreferences] = None
