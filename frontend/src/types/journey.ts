export type TransportMode = "CAB" | "OWN_VEHICLE" | "WALK" | "BUS" | "METRO" | "TRAIN" | "BICYCLE" | "RIDE_SHARE" | "SUBURBAN" | "MRTS";

export type ValidationStatus = "VALID" | "PARTIAL" | "REJECTED" | "UNAVAILABLE" | "FALLBACK" | "MISSING_GEOMETRY";

export interface RouteSegment {
  leg_id?: string;
  segment_id?: string;
  sequence?: number;
  segment_name: string;
  transport_mode: string;
  polyline: GeoJSON.Feature;
  color: string;
  distance: string;
  eta: string;
  environmental_risk: number;
  adjusted_safety_score?: number | null;
  reason: string;
  safety_score?: number | null;
  score_status?: string | null;
  scoreable_coverage_ratio?: number | null;
  score_source?: string | null;
  score_disclosure?: string | null;
  distance_m?: number;
  duration_s?: number;
  geometry_complete?: boolean;
  origin?: string;
  destination?: string;
}

export interface RoutePOI {
  poi_id: string;
  osm_id?: number | null;
  name: string;
  category: "police" | "hospital" | "clinic" | "pharmacy" | "fire_station" | "retail_shop" | "restaurant" | "cafe" | "supermarket" | "convenience" | "food_retail" | "fast_food" | "hotel" | "fuel" | string;
  category_label: string;
  latitude: number;
  longitude: number;
  distance_to_route_m: number;
  nearest_route_leg_id?: string | null;
  proximity_tier: "IMMEDIATELY_BESIDE" | "ALONG_CORRIDOR" | string;
  is_emergency?: boolean;
  is_shop?: boolean;
  provenance_type?: "mapped_public_facility" | "independently_verified_facility" | "mapped_commercial_business" | "public_surveillance" | string;
  verification_status?: "MAPPED_PUBLIC_FACILITY" | "INDEPENDENTLY_VERIFIED" | "MAPPED_COMMERCIAL_CONTEXT" | "MAPPED_SURVEILLANCE" | string;
  safety_role?: "emergency_safe_haven" | "public_police_station" | "medical_emergency_facility" | "public_health_support" | "fire_and_rescue_service" | "commercial_activity" | "surveillance_infrastructure" | string;
  is_verified_safety_facility?: boolean;
  is_safe_haven_eligible?: boolean;
  opening_status?: "OPEN" | "CLOSED" | "UNKNOWN" | string;
  opening_hours?: string | null;
  estimated_pass_through_time?: string | null;
  address?: string | null;
  phone?: string | null;
  website?: string | null;
  operator?: string | null;
  source: string;
  last_verified_at?: string | null;
}

export interface FeatureContributionItem {
  feature: string;
  raw_feature?: string | null;
  attribution: number;
  direction: "SAFETY_ENHANCING" | "RISK_INCREASING" | string;
}

export interface RouteModelAttribution {
  method: string;
  base_value: number;
  safety_score?: number | null;
  reconstructed_score?: number | null;
  reconstruction_error?: number | null;
  is_mathematically_reconstructed: boolean;
  target: string;
  top_positive_factors: FeatureContributionItem[];
  top_negative_factors: FeatureContributionItem[];
  status: string;
}

export interface RouteFare {
  fare_type: "OFFICIAL_FARE" | "ESTIMATED_FARE" | "FARE_UNAVAILABLE" | "NOT_APPLICABLE" | "METERED_VARIABLE" | string;
  currency?: string | null;
  amount?: number | null;
  display_text: string;
  source_label: string;
  is_official: boolean;
}

export interface ActivityZone {
  zone_id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_m: number;
  activity_level: "HIGH" | "MODERATE" | string;
  shop_count: number;
  source: string;
  disclosure: string;
}

export interface MultimodalRoute {
  id: string;
  rank: number;
  route_name: string;
  travel_mode_chain: string;
  mode: string;
  eta: string;
  cost: string;
  fare?: RouteFare | null;
  distance: string;
  environmental_risk: number;
  safety_score: number | null;
  overall_safety_score?: number | null;
  model_explainability: Record<string, string>;
  model_attribution?: RouteModelAttribution | null;
  nearby_pois?: RoutePOI[];
  activity_zones?: ActivityZone[];
  night_activity_score?: NightActivityScore;
  recommendation_reason: string[];
  ranking_labels?: string[];
  strengths: string[];
  segments: RouteSegment[];
  is_recommended: boolean;
  score_status?: string | null;
  scoreable_coverage_ratio?: number | null;
  score_basis?: string | null;
  model_version?: string | null;
  target_disclosure?: string | null;
  tradeoffs?: string[];
  user_preference_match?: string | null;
}

export interface NightActivityScore {
  overall_score: number;
  coverage_score: number;
  isolation_penalty: number;
  density_score: number;
  corridor_continuity_score?: number;
  open_volume_score?: number;
  emergency_score: number;
  transit_access_score?: number;
  confidence_score: number;
  data_confidence_score?: number;
  normalized_score?: number;
  concern_level?: "HIGH_CONCERN" | "LIMITED_INDICATORS" | "SUPPORTED_INDICATORS";
  surveillance_cameras_count?: number;
  corridor_open_places_count?: number;
  total_corridor_places_count?: number;
  corridor_unknown_hours_count?: number;
  longest_dark_gap_meters?: number;
  formula_version?: string;
  is_out_of_bounds?: boolean;
  status?: string;
}

export interface SessionInfo {
  created_at: string;
  status: string;
}

export interface JourneyInformation {
  source: string;
  destination: string;
  distance: number;
  estimated_duration: number;
}

export interface WeatherSummary {
  condition: string;
  temperature: number;
  hazards: string[];
}

export interface CommunitySummary {
  reports_along_route: number;
  severity_level: string;
}

export interface AIRecommendation {
  title: string;
  summary: string;
  confidence: number;
  reasoning: string;
  warnings: string[];
  suggested_actions: string[];
}

export interface JourneyPlanData {
  journey_id: string;
  source_name?: string;
  dest_name?: string;
  source_loc?: [number, number];
  dest_loc?: [number, number];
  session_info?: SessionInfo;
  journey_information?: JourneyInformation;
  recommended_routes: MultimodalRoute[];
  weather_summary?: WeatherSummary;
  community_summary?: CommunitySummary;
  alerts?: string[];
  ai_recommendation?: AIRecommendation;
  warnings?: string[];
  zero_distance?: boolean;
  safety_score?: number | string;
}

export interface JourneyResponse {
  status: string;
  data: JourneyPlanData;
}

export interface JourneyCreateRequest {
  source: string;
  destination: string;
  preferences?: string[];
  travel_time?: string;
}

export interface LocationSuggestion {
  id: string;
  name: string;
  secondary_text: string;
  place_type: string;
  place_type_label: string;
  latitude: number;
  longitude: number;
  formatted_coords: string;
  source: string;
}

export type JourneyPlanResponse = JourneyResponse["data"];