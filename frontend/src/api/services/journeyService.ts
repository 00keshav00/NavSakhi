import { apiClient, StandardResponse } from "../client";
import { JourneyCreateRequest, JourneyPlanResponse, LocationSuggestion } from "../../types/journey";

export const journeyService = {
  autocomplete: async (query: string, limit: number = 8, signal?: AbortSignal): Promise<LocationSuggestion[]> => {
    if (!query || query.trim().length === 0) return [];
    const response = await apiClient.get<StandardResponse<LocationSuggestion[]>>(
      `/api/v1/journeys/autocomplete?q=${encodeURIComponent(query.trim())}&limit=${limit}`,
      { signal }
    );
    return response.data?.data || [];
  },

  planJourney: async (request: JourneyCreateRequest): Promise<JourneyPlanResponse> => {
    const response = await apiClient.post<StandardResponse<JourneyPlanResponse>>("/api/v1/journeys/", request);
    return response.data.data;
  },

  getActiveJourney: async (): Promise<Record<string, unknown> | null> => {
    const response = await apiClient.get<StandardResponse<Record<string, unknown> | null>>("/api/v1/journeys/active");
    return response.data.data;
  },

  startJourney: async (journeyId: string, selectedRouteId?: string) => {
    const payload = selectedRouteId ? { selected_route_id: selectedRouteId } : {};
    const response = await apiClient.post<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/start`, payload);
    return response.data.data;
  },

  pauseJourney: async (journeyId: string) => {
    const response = await apiClient.post<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/pause`);
    return response.data.data;
  },

  resumeJourney: async (journeyId: string) => {
    const response = await apiClient.post<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/resume`);
    return response.data.data;
  },

  cancelJourney: async (journeyId: string) => {
    const response = await apiClient.post<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/cancel`);
    return response.data.data;
  },

  completeJourney: async (journeyId: string) => {
    const response = await apiClient.post<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/complete`);
    return response.data.data;
  },

  getJourneyProgress: async (journeyId: string) => {
    const response = await apiClient.get<StandardResponse<Record<string, unknown>>>(`/api/v1/journeys/${journeyId}/progress`);
    return response.data.data;
  },
  
  connectToJourneyWebSocket: async <T = Record<string, unknown>>(
    journeyId: string,
    onMessage: (data: T) => void,
    onClose?: () => void,
    onError?: (err: unknown) => void
  ): Promise<WebSocket> => {
    // Obtain short-lived single-use ticket via authenticated REST call
    const ticketRes = await apiClient.post<StandardResponse<{ ticket: string }>>("/api/v1/auth/ws-ticket");
    const ticket = ticketRes.data?.data?.ticket;
    if (!ticket) {
      throw new Error("Unable to obtain single-use WebSocket ticket for journey connection.");
    }

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/api/v1/ws/journey/${journeyId}?ticket=${encodeURIComponent(ticket)}`);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    if (onClose) {
      ws.onclose = () => onClose();
    }

    if (onError) {
      ws.onerror = (err) => onError(err);
    }

    return ws;
  }
};
