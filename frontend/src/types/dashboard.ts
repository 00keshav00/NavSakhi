export interface Alert {
  id: string;
  message: string;
  severity: 'info' | 'warning' | 'danger';
  time: string;
}

export interface AITimelineEvent {
  id: string;
  event: string;
  time: string;
  icon: string;
}

export interface DashboardOverviewResponse {
  ai_status: {
    mode: string;
    health: string;
    last_analysis: string;
    recommendation: string;
  };
  safety_score: {
    overall: number;
    risk_level: string;
    confidence: number;
    trend: 'improving' | 'stable' | 'degrading';
  };
  weather: {
    temperature: number;
    condition: string;
    visibility: number; // km
    humidity: number; // %
    rain_probability: number; // %
  };
  community: {
    nearby_reports: number;
    safe_zones: number;
    danger_zones: number;
    recent_activity: string;
  };
  recent_alerts: Alert[];
  ai_timeline: AITimelineEvent[];
  recent_journeys: Array<{
    id: string;
    destination: string;
    status: string;
    score: number;
    time: string;
  }>;
  system_health: {
    backend: string;
    ai_agent: string;
    latency: number;
    connected_providers: string[];
    last_sync: string;
  };
}
