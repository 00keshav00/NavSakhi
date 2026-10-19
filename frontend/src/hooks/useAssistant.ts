import { useState, useEffect, useCallback } from "react";
import { assistantService } from "../api/services/assistantService";
import { AssistantResponse } from "../types/assistant";
import { useAuthStore } from "../store/authStore";
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
  
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const accessToken = useAuthStore((state) => state.accessToken);

  // Load initial greeting and context
  useEffect(() => {
    let isCancelled = false;

    const init = async () => {
      // If not authenticated, inform the user cleanly without firing API requests
      if (!isAuthenticated && !accessToken) {
        setMessages([{
          id: "msg_unauth",
          role: "assistant",
          content: "Please sign in to connect with your NavSakhi Intelligence Coordinator and view active journey telemetry.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        return;
      }

      setIsTyping(true);
      setError(null);
      try {
        const response = await assistantService.getInitialContext();
        if (!isCancelled) {
          setLatestContext(response);
          setMessages([{
            id: response.message_id,
            role: response.role,
            content: response.content,
            timestamp: response.timestamp
          }]);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setError((err as Error).message || "Failed to connect to Intelligence Coordinator.");
        }
      } finally {
        if (!isCancelled) {
          setIsTyping(false);
        }
      }
    };

    init();
    return () => {
      isCancelled = true;
    };
  }, [isAuthenticated, accessToken]);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim()) return;

    if (!isAuthenticated && !accessToken) {
      toast.error("Authentication Required", {
        description: "Please sign in to interact with the Assistant.",
      });
      return;
    }

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
    } catch (err: unknown) {
      toast.error("Coordinator Unavailable", { description: (err as Error).message });
      setMessages(prev => [...prev, {
        id: "err_" + Math.random(),
        role: 'assistant',
        content: "Error communicating with the Intelligence Coordinator. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsTyping(false);
    }
  }, [isAuthenticated, accessToken]);

  return { messages, latestContext, isTyping, error, sendMessage };
};
