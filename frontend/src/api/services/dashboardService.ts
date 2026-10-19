import { apiClient, StandardResponse } from "../client";
import { DashboardOverviewResponse } from "../../types/dashboard";

export const dashboardService = {
  getOverview: async (): Promise<DashboardOverviewResponse> => {
    // API Contract defined: GET /api/v1/dashboard/overview
    const response = await apiClient.get<StandardResponse<DashboardOverviewResponse>>("/api/v1/dashboard/overview");
    return response.data.data;
  },
};
