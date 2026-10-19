import { apiClient, StandardResponse } from "../client";
import { AssistantResponse } from "../../types/assistant";

export const assistantService = {
  getInitialContext: async (): Promise<AssistantResponse> => {
    const response = await apiClient.get<StandardResponse<AssistantResponse>>("/api/v1/assistant/context");
    return response.data.data;
  },

  sendMessage: async (query: string): Promise<AssistantResponse> => {
    const response = await apiClient.post<StandardResponse<AssistantResponse>>("/api/v1/assistant/chat", { query });
    return response.data.data;
  }
};
