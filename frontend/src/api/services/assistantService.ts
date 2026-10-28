import { apiClient, StandardResponse } from "../client";
import { AssistantResponse } from "../../types/assistant";

export const assistantService = {
  getInitialContext: async (): Promise<AssistantResponse> => {
    const response = await apiClient.get<StandardResponse<AssistantResponse>>("/api/v1/assistant/context");
    return response.data.data;
  },

  sendMessage: async (query: string, history?: { role: string; content: string }[]): Promise<AssistantResponse> => {
    const payload = history && history.length > 0 ? { query, history } : { query };
    const response = await apiClient.post<StandardResponse<AssistantResponse>>("/api/v1/assistant/chat", payload);
    return response.data.data;
  }
};
