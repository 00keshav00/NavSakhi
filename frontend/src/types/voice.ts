/**
 * NavSakhi Voice Assistant Types and State Definitions
 * Phase 11: Free Voice Assistant Integration
 */

export type RecognitionState = 
  | "idle"
  | "listening"
  | "processing"
  | "error"
  | "unsupported";

export type SynthesisState = 
  | "idle"
  | "speaking"
  | "paused"
  | "unsupported";

export type SpeechErrorCode = 
  | "not-allowed"
  | "no-speech"
  | "audio-capture"
  | "network"
  | "aborted"
  | "service-not-allowed"
  | "bad-grammar"
  | "language-not-supported"
  | "unknown";

export interface VoiceLanguage {
  code: string;
  label: string;
  nativeLabel: string;
}

export interface VoiceCapabilities {
  isRecognitionSupported: boolean;
  isSynthesisSupported: boolean;
  isRecognitionOnDevice: boolean; // Note: standard browser Web Speech API generally delegates to platform/vendor
  availableVoices: SpeechSynthesisVoice[];
}

export interface VoiceAssistantState {
  recognitionState: RecognitionState;
  synthesisState: SynthesisState;
  error: string | null;
  interimTranscript: string;
  hasConsent: boolean;
  needsConsentModal: boolean;
  autoReadAloud: boolean;
  speakingMessageId: string | null;
  selectedLanguage: string;
}

export interface VoiceSafetyCheckResult {
  hasEmergencyKeywords: boolean;
  keywordMatched?: string;
  safetyNotice?: string;
}
