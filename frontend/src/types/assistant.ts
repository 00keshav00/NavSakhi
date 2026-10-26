export interface AssistantResponse {
  message_id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp: string;
  agent_status: {
    status: 'Idle' | 'Thinking' | 'Analyzing' | 'Monitoring' | 'Emergency Mode' | 'Waiting';
    current_task: string;
  };
  reasoning: {
    summary: string[];
    confidence?: number | null;
    decision_source: string;
    provider_summary: string;
    response_source?: 'gemini' | 'fallback' | 'rule_based';
    intent_category?: string;
    gemini_attempted?: boolean;
    model_identifier?: string | null;
    attempt_count?: number;
    provider_latency_ms?: number | null;
    outcome_category?: string;
    correlation_id?: string;
  };
  context: {
    active_journey: boolean;
    source?: string;
    destination?: string;
    safety_score?: number | null;
    eta?: string;
    weather?: string;
    community_alerts?: number;
    emergency_status?: string;
  };
  provider_health: Array<{
    name: string;
    status: 'Connected' | 'Processing' | 'Disconnected' | 'Unavailable';
  }>;
  memory: {
    recent_journeys: string[];
    pinned_info: string[];
  };
  quick_suggestions: string[];
  response_source?: 'gemini' | 'fallback' | 'rule_based';
}
