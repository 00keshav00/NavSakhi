import { apiClient, StandardResponse } from "../client";
import { LiveMonitorResponse } from "../../types/liveMonitor";

export const liveMonitorService = {
  /**
   * Fetches the authentic live monitor snapshot for the given journey.
   * Throws on 404/403/500 errors so the UI can honestly report that no
   * active journey exists or that telemetry is unavailable.
   * Never falls back to mock coordinates or fabricated safety scores.
   */
  getMonitorStatus: async (journeyId: string): Promise<LiveMonitorResponse> => {
    if (!journeyId || journeyId.trim() === "") {
      throw new Error("A valid journey ID is required to fetch monitoring status.");
    }

    const response = await apiClient.get<StandardResponse<LiveMonitorResponse>>(
      `/api/v1/journeys/${encodeURIComponent(journeyId)}/monitor`
    );

    if (!response.data || !response.data.data) {
      throw new Error("No monitoring data received from server.");
    }

    return response.data.data;
  },
};
