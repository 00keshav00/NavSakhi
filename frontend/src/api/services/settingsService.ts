import { apiClient, StandardResponse } from "../client";
import { SettingsResponse } from "../../types/settings";

export const settingsService = {
  getSettings: async (): Promise<SettingsResponse> => {
    const response = await apiClient.get<StandardResponse<SettingsResponse>>("/api/v1/settings");
    return response.data.data;
  },

  updateSettings: async (settings: SettingsResponse): Promise<void> => {
    await apiClient.patch("/api/v1/settings", settings);
  }
};
