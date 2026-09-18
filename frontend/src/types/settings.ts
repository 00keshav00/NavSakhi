export interface SettingsAppearance {
  theme: 'Light' | 'Dark' | 'System';
  accent_color: string;
}

export interface SettingsNotifications {
  journey_alerts: boolean;
  community_alerts: boolean;
  weather_alerts: boolean;
  emergency_alerts: boolean;
  ai_notifications: boolean;
  email_notifications: boolean;
  push_notifications: boolean;
}

export interface SettingsPrivacy {
  share_live_location: boolean;
  anonymous_community_reports: boolean;
  location_history: boolean;
  analytics: boolean;
  crash_reports: boolean;
}

export interface SettingsEmergency {
  default_sos_contacts: boolean;
  auto_location_sharing: boolean;
  emergency_countdown: boolean;
  auto_call_emergency_contact: boolean;
  share_journey_automatically: boolean;
}

export interface SettingsAiPreferences {
  assistant_personality: string;
  explanation_detail: 'Brief' | 'Detailed' | 'Comprehensive';
  safety_sensitivity: 'Low' | 'Medium' | 'High';
  preferred_route_type: 'Fastest' | 'Safest' | 'Balanced';
  risk_tolerance: 'Low' | 'Medium' | 'High';
  agent_notifications: boolean;
  enable_ai_recommendations: boolean;
}

export interface SettingsLocation {
  default_transport_mode: 'Walking' | 'Transit' | 'Driving';
  preferred_walking_speed: 'Slow' | 'Average' | 'Fast';
  avoid_highways: boolean;
  avoid_dark_areas: boolean;
  avoid_crowds: boolean;
  avoid_construction: boolean;
}

export interface SettingsLanguage {
  language: string;
  region: string;
  time_format: '12h' | '24h';
  distance_unit: 'Metric' | 'Imperial';
}

export interface SettingsVoice {
  voice_enabled: boolean;
  preferred_voice: string;
  speech_speed: number;
}

export interface SettingsDeveloper {
  developer_mode: boolean;
  show_debug_info: boolean;
  provider_status: boolean;
  api_version: string;
  app_version: string;
  build_version: string;
}

export interface SettingsResponse {
  appearance: SettingsAppearance;
  notifications: SettingsNotifications;
  privacy: SettingsPrivacy;
  emergency: SettingsEmergency;
  ai_preferences: SettingsAiPreferences;
  location: SettingsLocation;
  language: SettingsLanguage;
  voice: SettingsVoice;
  developer: SettingsDeveloper;
}
