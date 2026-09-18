from pydantic import BaseModel
from typing import List, Optional

class ProfileStats(BaseModel):
    safe_journeys: int
    total_distance_km: float
    avg_safety_score: float
    sos_triggered: int
    dangerous_routes_avoided: int
    ai_recommendations_followed: int
    community_reports_submitted: int
    verified_reports: int
    helpful_votes: int
    reputation_score: int
    trust_level: str

class ProfileJourneyHistory(BaseModel):
    id: str
    source: str
    destination: str
    date: str
    transport: str
    safety_score: int
    duration: str
    status: str

class ProfileEmergencyContact(BaseModel):
    id: str
    name: str
    relationship: str
    phone: str
    status: str
    is_primary: bool

class ProfileAchievement(BaseModel):
    id: str
    title: str
    icon: str
    unlocked: bool
    date: Optional[str] = None

class UserInfo(BaseModel):
    avatar_url: str
    full_name: str
    email: str
    phone: str
    current_city: str
    member_since: str
    is_premium: bool
    is_online: bool
    last_active: str

class ProfileResponse(BaseModel):
    user_info: UserInfo
    stats: ProfileStats
    journey_history: List[ProfileJourneyHistory]
    emergency_contacts: List[ProfileEmergencyContact]
    achievements: List[ProfileAchievement]
