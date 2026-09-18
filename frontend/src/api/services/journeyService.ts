import { apiClient, StandardResponse } from "../client";
import { JourneyCreateRequest, JourneyPlanResponse } from "../../types/journey";

export const journeyService = {
  planJourney: async (request: JourneyCreateRequest): Promise<JourneyPlanResponse> => {
    // API Contract defined: POST /api/v1/journeys/
    const response = await apiClient.post<StandardResponse<JourneyPlanResponse>>("/api/v1/journeys/", request);
    return response.data.data;
  },

  startJourney: async (journeyId: string) => {
    // API Contract defined: POST /api/v1/journeys/{journey_id}/start
    await apiClient.post(`/api/v1/journeys/${journeyId}/start`);
  },

  cancelJourney: async (journeyId: string) => {
    // API Contract defined: POST /api/v1/journeys/{journey_id}/cancel
    await apiClient.post(`/api/v1/journeys/${journeyId}/cancel`);
  },
  
  connectToJourneyWebSocket: (journeyId: string, onAlert: (data: any) => void) => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/api/v1/ws/journey/${journeyId}`);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onAlert(data);
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    return ws;
  }
};
