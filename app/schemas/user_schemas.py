import re
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List
from app.models.user import EmergencyContact, UserPreferences

class UserCreate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = "Family"
    emergency_contact_phone: Optional[str] = None
    emergency_contact: Optional[EmergencyContact] = None
    acknowledged_limitations: bool = True

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (maximum 72 bytes).")
        # Check for at least one digit or symbol
        if not re.search(r"[0-9!@#$%^&*()_+\-=\[\]{};':\",.<>/?]", v):
            raise ValueError("Password must include at least one number or symbol.")
        return v

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            cleaned = re.sub(r"[\s\-\(\)]", "", v)
            if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
                raise ValueError("Emergency contact phone number must be a valid phone number (10 to 15 digits, optional + country code).")
            return cleaned
        return v

    @field_validator("acknowledged_limitations")
    @classmethod
    def validate_acknowledgement(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must acknowledge the prototype limitations to create an account.")
        return v

    @model_validator(mode="after")
    def validate_user_fields(self):
        # Default username to full_name or email prefix if not supplied
        if not self.username:
            self.username = self.full_name or self.email.split("@")[0]
        if not self.full_name:
            self.full_name = self.username

        # Check confirm password if supplied
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")

        # Ensure emergency contact details are consistent
        if self.emergency_contact_name and not self.emergency_contact_phone:
            raise ValueError("Phone number is required for the emergency contact.")
        if self.emergency_contact_phone and not self.emergency_contact_name:
            raise ValueError("Name is required for the emergency contact.")

        return self

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    preferences: Optional[UserPreferences] = None
    emergency_contacts: List[EmergencyContact] = []
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    current_city: Optional[str] = None
    age: Optional[int] = None
    is_active: bool = True
    role: str = "user"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    current_city: Optional[str] = None
    age: Optional[int] = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if len(v_stripped) < 2:
                raise ValueError("Full name must be at least 2 characters long.")
            return v_stripped
        return v

    @field_validator("phone_number", "phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            cleaned = re.sub(r"[\s\-\(\)]", "", v)
            if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
                raise ValueError("Phone number must be a valid number (10 to 15 digits, optional + country code).")
            return cleaned
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 13 or v > 120:
                raise ValueError("Age must be between 13 and 120.")
        return v


class EmergencyContactCreate(BaseModel):
    name: str
    phone_number: str
    relationship: Optional[str] = "Family"
    email: Optional[EmailStr] = None
    is_primary: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_stripped = v.strip()
        if len(v_stripped) < 2:
            raise ValueError("Contact name must be at least 2 characters long.")
        return v_stripped

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
            raise ValueError("Phone number must be a valid number (10 to 15 digits, optional + country code).")
        return cleaned

class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    relationship: Optional[str] = None
    email: Optional[EmailStr] = None
    is_primary: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if len(v_stripped) < 2:
                raise ValueError("Contact name must be at least 2 characters long.")
            return v_stripped
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            cleaned = re.sub(r"[\s\-\(\)]", "", v)
            if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
                raise ValueError("Phone number must be a valid number (10 to 15 digits, optional + country code).")
            return cleaned
        return v

class UserUpdate(BaseModel):
    preferences: Optional[UserPreferences] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone: Optional[str] = None
    current_city: Optional[str] = None
    age: Optional[int] = None


