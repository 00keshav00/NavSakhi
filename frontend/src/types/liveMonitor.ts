export interface LiveMonitorResponse {
  journey_id: string;
  is_active: boolean;
  status_summary: {
    distance_remaining: number; // meters
    eta: number; // seconds
    transport_mode: string;
    progress_percentage: number;
    current_segment: string;
  };
  safety_score: {
    current: number;
    trend: 'improving' | 'stable' | 'degrading';
    confidence: number;
    risk_level: string;
  };
  ai_recommendation: {
    recommendation: string;
    reason: string;
    confidence: number;
    warnings: string[];
    suggested_action: string;
  };
  environment_summary: {
    weather_condition: string;
    visibility: string;
    lighting: string;
    crowd_density: string;
    police_presence: string;
    road_condition: string;
  };
  realtime_alerts: Array<{ id: string; severity: 'info' | 'warning' | 'danger'; time: string; description: string; }>;
  agent_timeline: Array<{ id: string; action: string; time: string; icon: string; }>;
  current_route: {
    distance: number;
    duration: number;
    safety_score: number;
    weather_impact: string;
    community_impact: string;
    risk_factors: string[];
    geometry: any; // GeoJSON
  };
  current_location: { lat: number; lng: number };
}
