import { apiClient, StandardResponse } from "../client";
import { LiveWeatherData, ReverseGeocodeData } from "@/types/weather";

export const weatherService = {
  getLiveWeather: async (
    lat: number,
    lon: number,
    locationName?: string
  ): Promise<LiveWeatherData> => {
    const params: Record<string, any> = { lat, lon };
    if (locationName) params.location_name = locationName;
    const response = await apiClient.get<StandardResponse<LiveWeatherData>>("/api/v1/weather/live", { params });
    return response.data.data;
  },

  reverseGeocode: async (lat: number, lon: number): Promise<ReverseGeocodeData> => {
    const response = await apiClient.get<StandardResponse<ReverseGeocodeData>>("/api/v1/weather/reverse-geocode", {
      params: { lat, lon },
    });
    return response.data.data;
  },
};
