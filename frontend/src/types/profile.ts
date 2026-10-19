export interface ProfileStats {
  safe_journeys: number;
  total_distance_km: number;
  avg_safety_score: number;
  sos_triggered: number;
  dangerous_routes_avoided: number;
  ai_recommendations_followed: number;
  community_reports_submitted: number;
  verified_reports: number;
  helpful_votes: number;
  reputation_score: number;
  trust_level: string;
}

export interface ProfileJourneyHistory {
  id: string;
  source: string;
  destination: string;
  date: string;
  transport: string;
  safety_score: number;
  duration: string;
  status: 'Completed' | 'Cancelled' | 'Emergency';
}

export interface ProfileEmergencyContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  status: 'Active' | 'Pending' | 'Inactive';
  is_primary: boolean;
}

export interface ProfileAchievement {
  id: string;
  title: string;
  icon: string; // e.g. "Shield", "Star", "Map"
  unlocked: boolean;
  date?: string;
}

export interface ProfileResponse {
  user_info: {
    avatar_url: string;
    full_name: string;
    email: string;
    phone: string;
    current_city: string;
    member_since: string;
    is_premium: boolean;
    is_online: boolean;
    last_active: string;
  };
  stats: ProfileStats;
  journey_history: ProfileJourneyHistory[];
  emergency_contacts: ProfileEmergencyContact[];
  achievements: ProfileAchievement[];
}
