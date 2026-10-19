import { apiClient } from "../client";

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export const healthService = {
  checkHealth: async (): Promise<HealthResponse> => {
    // The health endpoint is at /health at the root of the backend
    const response = await apiClient.get<HealthResponse>("/health");
    return response.data;
  }
};
