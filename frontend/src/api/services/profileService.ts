import { apiClient, StandardResponse } from "../client";
import { ProfileResponse } from "../../types/profile";

export const profileService = {
  getProfile: async (): Promise<ProfileResponse> => {
    const response = await apiClient.get<StandardResponse<ProfileResponse>>("/api/v1/profile");
    return response.data.data;
  },
  updateProfile: async (data: any): Promise<ProfileResponse> => {
    const response = await apiClient.put<StandardResponse<ProfileResponse>>("/api/v1/profile", data);
    return response.data.data;
  }
};
