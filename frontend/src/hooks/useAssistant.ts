import { useState, useEffect, useCallback, useRef } from "react";
import { assistantService } from "../api/services/assistantService";
import { AssistantResponse } from "../types/assistant";
import { useAuthStore } from "../store/authStore";
import { toast } from "sonner";

export interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp: string;
  response_source?: 'gemini' | 'fallback' | 'rule_based';
  model_identifier?: string | null;
}

export const useAssistant = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [latestContext, setLatestContext] = useState<AssistantResponse | null>(null);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const requestSeqRef = useRef<number>(0);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const accessToken = useAuthStore((state) => state.accessToken);

  // Load initial greeting and context without freezing user input
  useEffect(() => {
    let isCancelled = false;

    const init = async () => {
      setError(null);
      try {
        const response = await assistantService.getInitialContext();
        if (!isCancelled) {
          setLatestContext(response);
          setMessages([{
            id: response.message_id,
            role: response.role,
            content: response.content,
            timestamp: response.timestamp,
            response_source: response.response_source || response.reasoning?.response_source,
            model_identifier: response.reasoning?.model_identifier,
          }]);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setMessages([{
            id: "msg_guest",
            role: "assistant",
            content: "Welcome to NavSakhi Intelligence Assistant! Ask any transit or safety questions about Chennai.",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
        }
      }
    };

    init();
    return () => {
      isCancelled = true;
      requestSeqRef.current++;
      setIsTyping(false);
    };
  }, [isAuthenticated, accessToken]);

  const messagesRef = useRef<ChatMessage[]>([]);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const cancelRequest = useCallback(() => {
    requestSeqRef.current++;
    setIsTyping(false);
  }, []);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim()) return;

    const currentSeq = ++requestSeqRef.current;

    // Snapshot conversation history for multi-turn companion empathy
    const history = messagesRef.current.slice(-6).map(m => ({ role: m.role, content: m.content }));

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
      const response = await assistantService.sendMessage(query, history);
      if (currentSeq !== requestSeqRef.current) {
        // Discard stale response from older request to prevent overwriting newer state
        return;
      }
      setLatestContext(response); // Update the right/left sidebars with new DTO context
      
      const respSource = response.response_source || response.reasoning?.response_source;
      const modelId = response.reasoning?.model_identifier;

      setMessages(prev => [...prev, {
        id: response.message_id,
        role: response.role,
        content: response.content,
        timestamp: response.timestamp,
        response_source: respSource,
        model_identifier: modelId,
      }]);
    } catch (err: unknown) {
      if (currentSeq !== requestSeqRef.current) {
        return;
      }
      toast.error("Coordinator Unavailable", { description: (err as Error).message });
      setMessages(prev => [...prev, {
        id: "err_" + Math.random(),
        role: 'assistant',
        content: "Error communicating with the Intelligence Coordinator. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        response_source: 'fallback',
      }]);
    } finally {
      if (currentSeq === requestSeqRef.current) {
        setIsTyping(false);
      }
    }
  }, []);

  return { messages, latestContext, isTyping, error, sendMessage, cancelRequest };
};
