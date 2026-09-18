import { useState, useEffect, useCallback } from "react";
import { assistantService } from "../api/services/assistantService";
import { AssistantResponse } from "../types/assistant";
import { toast } from "sonner";

export interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp: string;
}

export const useAssistant = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [latestContext, setLatestContext] = useState<AssistantResponse | null>(null);
  const [isTyping, setIsTyping] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load initial greeting and context
  useEffect(() => {
    const init = async () => {
      try {
        const response = await assistantService.getInitialContext();
        setLatestContext(response);
        setMessages([{
          id: response.message_id,
          role: response.role,
          content: response.content,
          timestamp: response.timestamp
        }]);
      } catch (err: any) {
        setError(err.message || "Failed to connect to Intelligence Coordinator.");
      } finally {
        setIsTyping(false);
      }
    };
    init();
  }, []);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim()) return;

    // Optimistically add user message
    const userMsg: ChatMessage = {
      id: "usr_" + Math.random().toString(36).substr(2, 9),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await assistantService.sendMessage(query);
      setLatestContext(response); // Update the right/left sidebars with new DTO context
      
      setMessages(prev => [...prev, {
        id: response.message_id,
        role: response.role,
        content: response.content,
        timestamp: response.timestamp
      }]);
    } catch (err: any) {
      toast.error("Coordinator Unavailable", { description: err.message });
      setMessages(prev => [...prev, {
        id: "err_" + Math.random(),
        role: 'assistant',
        content: "Error communicating with the Intelligence Coordinator. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsTyping(false);
    }
  }, []);

  return { messages, latestContext, isTyping, error, sendMessage };
};
