import { apiClient, StandardResponse } from "../client";
import { EmergencyResponse } from "../../types/emergency";

export const emergencyService = {
  triggerSOS: async (data: { current_location: string }): Promise<StandardResponse<{ session_id: string }>> => {
    const response = await apiClient.post<StandardResponse<{ session_id: string }>>("/api/v1/emergency/sos", data);
    return response.data;
  },

  getEmergencyStatus: async (sessionId: string): Promise<EmergencyResponse> => {
    const response = await apiClient.get<StandardResponse<EmergencyResponse>>(`/api/v1/emergency/${sessionId}/status`);
    return response.data.data;
  },

  connectWebSocket: async (sessionId: string, onMessage: (data: any) => void): Promise<WebSocket> => {
    // Obtain short-lived single-use ticket via authenticated REST call
    const ticketRes = await apiClient.post<StandardResponse<{ ticket: string }>>("/api/v1/auth/ws-ticket");
    const ticket = ticketRes.data?.data?.ticket;
    if (!ticket) {
      throw new Error("Unable to obtain single-use WebSocket ticket for emergency connection.");
    }

    let wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (!wsUrl) {
      const apiBase = apiClient.defaults.baseURL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");
      if (apiBase.startsWith("https://")) {
        wsUrl = apiBase.replace(/^https:\/\//, "wss://");
      } else if (apiBase.startsWith("http://")) {
        wsUrl = apiBase.replace(/^http:\/\//, "ws://");
      } else {
        wsUrl = "ws://localhost:8000";
      }
    }
    wsUrl = wsUrl.replace(/\/+$/, "");
    if (wsUrl === "wss://navsakhi-api.onrender.com" || wsUrl === "ws://navsakhi-api.onrender.com") {
      wsUrl = "wss://navsakhi-api-staging.onrender.com";
    }
    const ws = new WebSocket(`${wsUrl}/api/v1/ws/emergency/${sessionId}?ticket=${encodeURIComponent(ticket)}`);

    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("Failed to parse emergency websocket message", e);
      }
    };

    return ws;
  }
};
