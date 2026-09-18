from pydantic import BaseModel

class SettingsAppearance(BaseModel):
    theme: str
    accent_color: str

class SettingsNotifications(BaseModel):
    journey_alerts: bool
    community_alerts: bool
    weather_alerts: bool
    emergency_alerts: bool
    ai_notifications: bool
    email_notifications: bool
    push_notifications: bool

class SettingsPrivacy(BaseModel):
    share_live_location: bool
    anonymous_community_reports: bool
    location_history: bool
    analytics: bool
    crash_reports: bool

class SettingsEmergency(BaseModel):
    default_sos_contacts: bool
    auto_location_sharing: bool
    emergency_countdown: bool
    auto_call_emergency_contact: bool
    share_journey_automatically: bool

class SettingsAiPreferences(BaseModel):
    assistant_personality: str
    explanation_detail: str
    safety_sensitivity: str
    preferred_route_type: str
    risk_tolerance: str
    agent_notifications: bool
    enable_ai_recommendations: bool

class SettingsLocation(BaseModel):
    default_transport_mode: str
    preferred_walking_speed: str
    avoid_highways: bool
    avoid_dark_areas: bool
    avoid_crowds: bool
    avoid_construction: bool

class SettingsLanguage(BaseModel):
    language: str
    region: str
    time_format: str
    distance_unit: str

class SettingsVoice(BaseModel):
    voice_enabled: bool
    preferred_voice: str
    speech_speed: float

class SettingsDeveloper(BaseModel):
    developer_mode: bool
    show_debug_info: bool
    provider_status: bool
    api_version: str
    app_version: str
    build_version: str

class SettingsResponse(BaseModel):
    appearance: SettingsAppearance
    notifications: SettingsNotifications
    privacy: SettingsPrivacy
    emergency: SettingsEmergency
    ai_preferences: SettingsAiPreferences
    location: SettingsLocation
    language: SettingsLanguage
    voice: SettingsVoice
    developer: SettingsDeveloper
