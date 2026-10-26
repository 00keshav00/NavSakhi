import { apiClient, StandardResponse } from "../client";
import { CommunityReportCreate, CommunityReportResponse, CommunityIntelligenceResponse } from "../../types/community";

export const communityService = {
  createReport: async (data: CommunityReportCreate): Promise<StandardResponse<CommunityReportResponse>> => {
    // Exact URL defined in API Contract
    const response = await apiClient.post<StandardResponse<CommunityReportResponse>>("/api/v1/community/", data);
    return response.data;
  },

  getIntelligence: async (filters: { type: string; verification: string; }): Promise<CommunityIntelligenceResponse> => {
    try {
      const response = await apiClient.get<StandardResponse<CommunityIntelligenceResponse>>("/api/v1/community/intelligence", {
        params: filters
      });
      return response.data.data;
    } catch (error: any) {
      const errMsg = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to load community intelligence.";
      throw new Error(errMsg);
    }
  }
};

