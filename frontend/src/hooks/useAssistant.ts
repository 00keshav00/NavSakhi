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

export function sanitizeAssistantResponse(raw: unknown): AssistantResponse {
  if (!raw || typeof raw !== 'object') {
    return {
      message_id: "msg_" + Math.random().toString(36).substr(2, 9),
      role: 'assistant',
      content: "I am your NavSakhi travel companion. How can I help you navigate Chennai safely today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent_status: { status: 'Idle', current_task: 'Awaiting next input' },
      reasoning: {
        summary: ["Local fallback activated due to malformed payload"],
        decision_source: "contextual_fallback",
        provider_summary: "Operating within local verified boundaries",
        response_source: "fallback",
        model_identifier: null
      },
      context: { active_journey: false },
      provider_health: [],
      memory: { recent_journeys: [], pinned_info: [] },
      quick_suggestions: ["Plan a new route", "Check emergency contacts"],
      response_source: 'fallback'
    };
  }

  const obj = raw as Record<string, any>;
  const content = typeof obj.content === 'string' && obj.content.trim() ? obj.content : "No message content received.";
  const rawSource = obj.response_source || obj.reasoning?.response_source;
  const validSource: 'gemini' | 'fallback' | 'rule_based' = (rawSource === 'gemini' || rawSource === 'rule_based') ? rawSource : 'fallback';

  const rawReasoning = (obj.reasoning && typeof obj.reasoning === 'object') ? obj.reasoning : {};
  // TRUTHFUL PROVENANCE: If not strictly 'gemini', model_identifier MUST be null!
  const truthfulModelId = (validSource === 'gemini' && typeof rawReasoning.model_identifier === 'string')
    ? rawReasoning.model_identifier
    : null;

  return {
    message_id: typeof obj.message_id === 'string' ? obj.message_id : "msg_" + Math.random().toString(36).substr(2, 9),
    role: obj.role === 'user' ? 'user' : 'assistant',
    content,
    timestamp: typeof obj.timestamp === 'string' ? obj.timestamp : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    agent_status: {
      status: obj.agent_status?.status || 'Idle',
      current_task: obj.agent_status?.current_task || 'Awaiting next input'
    },
    reasoning: {
      summary: Array.isArray(rawReasoning.summary) ? rawReasoning.summary : ["Query processed"],
      confidence: typeof rawReasoning.confidence === 'number' ? rawReasoning.confidence : null,
      decision_source: typeof rawReasoning.decision_source === 'string' ? rawReasoning.decision_source : (validSource === 'gemini' ? 'gemini_direct' : 'contextual_fallback'),
      provider_summary: typeof rawReasoning.provider_summary === 'string' ? rawReasoning.provider_summary : "Operating within local verified boundaries",
      response_source: validSource,
      intent_category: rawReasoning.intent_category,
      gemini_attempted: Boolean(rawReasoning.gemini_attempted),
      model_identifier: truthfulModelId,
      attempt_count: typeof rawReasoning.attempt_count === 'number' ? rawReasoning.attempt_count : (validSource === 'gemini' ? 1 : 0),
      provider_latency_ms: typeof rawReasoning.provider_latency_ms === 'number' ? rawReasoning.provider_latency_ms : null,
      outcome_category: rawReasoning.outcome_category || (validSource === 'gemini' ? 'success' : 'unavailable'),
      correlation_id: rawReasoning.correlation_id,
      last_failed_model: rawReasoning.last_failed_model || null,
      failed_model_candidates: Array.isArray(rawReasoning.failed_model_candidates) ? rawReasoning.failed_model_candidates : [],
      safety_blocked_candidate: rawReasoning.safety_blocked_candidate || null
    },
    context: {
      active_journey: Boolean(obj.context?.active_journey),
      source: obj.context?.source,
      destination: obj.context?.destination,
      safety_score: typeof obj.context?.safety_score === 'number' ? obj.context.safety_score : null,
      eta: obj.context?.eta,
      weather: obj.context?.weather,
      community_alerts: obj.context?.community_alerts,
      emergency_status: obj.context?.emergency_status
    },
    provider_health: Array.isArray(obj.provider_health) ? obj.provider_health : [],
    memory: {
      recent_journeys: Array.isArray(obj.memory?.recent_journeys) ? obj.memory.recent_journeys : [],
      pinned_info: Array.isArray(obj.memory?.pinned_info) ? obj.memory.pinned_info : []
    },
    quick_suggestions: Array.isArray(obj.quick_suggestions) ? obj.quick_suggestions : [],
    response_source: validSource
  };
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
        const rawResponse = await assistantService.getInitialContext();
        if (!isCancelled) {
          const response = sanitizeAssistantResponse(rawResponse);
          setLatestContext(response);
          setMessages([{
            id: response.message_id,
            role: response.role,
            content: response.content,
            timestamp: response.timestamp,
            response_source: response.response_source,
            model_identifier: response.reasoning?.model_identifier,
          }]);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setMessages([{
            id: "msg_guest",
            role: "assistant",
            content: "Welcome to NavSakhi Intelligence Assistant! Ask any transit or safety questions about Chennai.",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            response_source: 'fallback',
            model_identifier: null
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
      const rawResponse = await assistantService.sendMessage(query, history);
      if (currentSeq !== requestSeqRef.current) {
        // Discard stale response from older request to prevent overwriting newer state
        return;
      }
      const response = sanitizeAssistantResponse(rawResponse);
      setLatestContext(response); // Update the right/left sidebars with new DTO context

      setMessages(prev => [...prev, {
        id: response.message_id,
        role: response.role,
        content: response.content,
        timestamp: response.timestamp,
        response_source: response.response_source,
        model_identifier: response.reasoning?.model_identifier,
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
        model_identifier: null
      }]);
    } finally {
      if (currentSeq === requestSeqRef.current) {
        setIsTyping(false);
      }
    }
  }, []);

  return { messages, latestContext, isTyping, error, sendMessage, cancelRequest };
};
