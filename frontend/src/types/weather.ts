export interface HourlyForecastItem {
  time: string;
  temperature_2m: number;
  precipitation_probability: number;
  weather_code: number;
  condition: string;
}

export interface DailyForecastItem {
  date: string;
  weather_code: number;
  condition: string;
  temperature_max: number;
  temperature_min: number;
  sunrise?: string | null;
  sunset?: string | null;
  uv_index_max?: number | null;
}

export interface LiveWeatherData {
  available: boolean;
  status: "AVAILABLE" | "UNAVAILABLE" | "RATE_LIMITED" | "ERROR";
  provider: string;
  provider_url: string;
  attribution: string;
  latitude: number;
  longitude: number;
  location_name: string;
  timezone: string;
  temperature: number;
  apparent_temperature: number;
  weather_code: number;
  condition: string;
  condition_icon: string;
  humidity: number;
  wind_speed: number;
  wind_direction: number;
  precipitation: number;
  rain: number;
  cloud_cover: number;
  uv_index?: number | null;
  uv_index_max?: number | null;
  sunrise?: string | null;
  sunset?: string | null;
  hourly_forecast: HourlyForecastItem[];
  daily_forecast: DailyForecastItem[];
  observation_timestamp: string;
  cached: boolean;
  cache_expires_in_seconds?: number | null;
  warnings: string[];
}

export type LiveWeatherResponse = LiveWeatherData;

export interface ReverseGeocodeData {
  latitude: number;
  longitude: number;
  display_name: string;
  city?: string | null;
  locality?: string | null;
  state?: string | null;
  country: string;
}
