import { apiClient, StandardResponse } from "../client";
import { EmergencyResponse } from "../../types/emergency";

let mockStatusCycle = 0;

export const emergencyService = {
  triggerSOS: async (data: { current_location: string }): Promise<StandardResponse<{ session_id: string }>> => {
    const response = await apiClient.post<StandardResponse<{ session_id: string }>>("/api/v1/emergency/sos", data);
    return response.data;
  },

  getEmergencyStatus: async (sessionId: string): Promise<EmergencyResponse> => {
    const response = await apiClient.get<StandardResponse<EmergencyResponse>>(`/api/v1/emergency/${sessionId}/status`);
    return response.data.data;
  },

  connectWebSocket: (sessionId: string, onMessage: (data: any) => void) => {
    // Placeholder for future implementation
    console.log(`[WS] Preparing WebSocket architecture for session ${sessionId}`);
    const ws = { close: () => console.log("Mock WS closed.") } as unknown as WebSocket;
    return ws;
  }
};
