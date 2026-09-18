from pydantic import BaseModel
from typing import List, Optional

class AIStatus(BaseModel):
    mode: str
    health: str
    last_analysis: str
    recommendation: str

class SafetyScoreStatus(BaseModel):
    overall: int
    risk_level: str
    confidence: int
    trend: str

class WeatherStatus(BaseModel):
    temperature: int
    condition: str
    visibility: int
    humidity: int
    rain_probability: int

class CommunityStatus(BaseModel):
    nearby_reports: int
    safe_zones: int
    danger_zones: int
    recent_activity: str

class AlertItem(BaseModel):
    id: str
    message: str
    severity: str
    time: str

class AITimelineEventItem(BaseModel):
    id: str
    event: str
    time: str
    icon: str

class RecentJourneyItem(BaseModel):
    id: str
    destination: str
    status: str
    score: int
    time: str

class SystemHealthStatus(BaseModel):
    backend: str
    ai_agent: str
    latency: int
    connected_providers: List[str]
    last_sync: str

class DashboardOverviewResponse(BaseModel):
    ai_status: AIStatus
    safety_score: SafetyScoreStatus
    weather: WeatherStatus
    community: CommunityStatus
    recent_alerts: List[AlertItem]
    ai_timeline: List[AITimelineEventItem]
    recent_journeys: List[RecentJourneyItem]
    system_health: SystemHealthStatus
