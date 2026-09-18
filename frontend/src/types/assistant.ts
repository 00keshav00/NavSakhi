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
    confidence: number;
    decision_source: string;
    provider_summary: string;
  };
  context: {
    active_journey: boolean;
    source?: string;
    destination?: string;
    safety_score?: number;
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
}
