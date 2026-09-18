export interface EmergencyContact {
  id: string;
  name: string;
  relationship: string;
  notification_status: 'Notified' | 'Pending' | 'Failed';
}

export interface EmergencyTimelineEvent {
  id: string;
  timestamp: string;
  status: 'completed' | 'active' | 'pending';
  description: string;
}

export interface EmergencySafeZone {
  id: string;
  type: 'Police' | 'Hospital' | 'Public';
  name: string;
  distance: string;
  eta: string;
  coordinates: [number, number];
}

export interface EmergencyResponse {
  session_id: string;
  status: 'idle' | 'active' | 'resolved';
  live_location: {
    coordinates: [number, number];
    address: string;
    accuracy: number;
    last_updated: string;
  };
  agent_status: {
    action: string;
    recommendation: string;
    context: string;
    confidence: number;
    reason: string;
  };
  timeline: EmergencyTimelineEvent[];
  contacts: EmergencyContact[];
  safe_zones: EmergencySafeZone[];
  journey_status: {
    active_journey: boolean;
    destination: string;
    distance_remaining: string;
    safety_score: number;
  };
}
