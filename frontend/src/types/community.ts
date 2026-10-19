export type VerificationStatus = 'Verified' | 'Pending' | 'Unverified';

export interface Location {
  type: string;
  coordinates: [number, number]; // [lng, lat]
}

export interface CommunityReportCreate {
  location: Location;
  report_type: string;
  description?: string;
  severity: 'High' | 'Medium' | 'Low';
  is_anonymous: boolean;
}

export interface CommunityReportResponse {
  id: string;
  _id?: string;
  user_id?: string;
  location: Location;
  report_type: string;
  description?: string;
  verification_status: VerificationStatus;
  verification_timestamp?: string;
  severity: 'High' | 'Medium' | 'Low';
  distance?: number;
  time: string;
  upvotes: number;
  downvotes: number;
}

export interface CommunityIntelligenceResponse {
  reports: CommunityReportResponse[];
  statistics: {
    total: number;
    verified: number;
    pending: number;
    unverified: number;
    high_risk_areas: number;
    safe_zones: number;
  };
  trending: {
    most_reported_areas: string[];
    most_common_incidents: string[];
    recent_activity: string[];
  };
  insights: string[];
  heatmap_data: {
    verified_only: Array<{ lat: number, lng: number, weight: number }>;
    all_reports: Array<{ lat: number, lng: number, weight: number }>;
  };
}
