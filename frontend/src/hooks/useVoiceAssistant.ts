"use client";

import { useState, useEffect, useRef, useCallback, useSyncExternalStore } from "react";
import type {
  RecognitionState,
  SynthesisState,
} from "../types/voice.ts";
import {
  checkSpeechRecognitionSupport,
  checkSpeechSynthesisSupport,
  cleanTextForSpeech,
  verifyVoiceSafetyBoundary,
} from "../utils/voiceUtils.ts";

export interface UseVoiceAssistantOptions {
  onTranscriptReceived?: (transcript: string) => void;
  defaultLanguage?: string;
}

interface SpeechRecognitionResultItem {
  transcript: string;
  confidence?: number;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionResultItem;
  isFinal?: boolean;
  length: number;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEventLike {
  error: string;
  message?: string;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

interface WindowWithSpeech {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

const emptySubscribe = () => () => {};

export function useVoiceAssistant(options: UseVoiceAssistantOptions = {}) {
  const { onTranscriptReceived, defaultLanguage = "en-IN" } = options;

  // Evaluate browser capabilities safely across SSR and Client Hydration via useSyncExternalStore
  const isRecognitionSupported = useSyncExternalStore(
    emptySubscribe,
    () => checkSpeechRecognitionSupport(),
    () => false
  );
  const isSynthesisSupported = useSyncExternalStore(
    emptySubscribe,
    () => checkSpeechSynthesisSupport(),
    () => false
  );

  const [internalRecState, setInternalRecState] = useState<RecognitionState>("idle");
  const [internalSynState, setInternalSynState] = useState<SynthesisState>("idle");

  const recognitionState: RecognitionState = !isRecognitionSupported ? "unsupported" : internalRecState;
  const synthesisState: SynthesisState = !isSynthesisSupported ? "unsupported" : internalSynState;

  const [error, setError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState<string>("");

  const [hasConsent, setHasConsent] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem("safeshe_voice_consent") === "true";
    } catch {
      return false;
    }
  });

  const [needsConsentModal, setNeedsConsentModal] = useState<boolean>(false);
  const [autoReadAloud, setAutoReadAloud] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem("safeshe_voice_auto_read") === "true";
    } catch {
      return false;
    }
  });

  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>(defaultLanguage);
  const [safetyNotice, setSafetyNotice] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const lastSpokenMessageIdRef = useRef<string | null>(null);
  const onTranscriptRef = useRef(onTranscriptReceived);

  useEffect(() => {
    onTranscriptRef.current = onTranscriptReceived;
  }, [onTranscriptReceived]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
      if (typeof window !== "undefined" && window.speechSynthesis) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  // Update autoReadAloud preference
  const toggleAutoReadAloud = useCallback((enabled: boolean) => {
    setAutoReadAloud(enabled);
    try {
      localStorage.setItem("safeshe_voice_auto_read", String(enabled));
    } catch {
      // ignore
    }
    if (!enabled && typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setInternalSynState("idle");
      setSpeakingMessageId(null);
    }
  }, []);

  // Stop active recognition
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
    setInternalRecState("idle");
    setInterimTranscript("");
  }, []);

  // Cancel/abort active recognition and discard transcription
  const cancelListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
    }
    setInternalRecState("idle");
    setInterimTranscript("");
  }, []);

  // Initiate recognition with consent checking
  const startListening = useCallback(() => {
    setError(null);
    setSafetyNotice(null);

    if (!isRecognitionSupported) {
      setError("Speech recognition is not supported in this browser. Please use text chat.");
      setInternalRecState("unsupported");
      return;
    }

    // Check explicit user consent
    if (!hasConsent) {
      setNeedsConsentModal(true);
      return;
    }

    try {
      const win = typeof window !== "undefined" ? (window as unknown as WindowWithSpeech) : null;
      const SpeechRecognition = win?.SpeechRecognition || win?.webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setInternalRecState("unsupported");
        return;
      }

      // Cancel any ongoing speech synthesis before listening
      if (typeof window !== "undefined" && window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        setInternalSynState("idle");
        setSpeakingMessageId(null);
      }

      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = selectedLanguage;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setInternalRecState("listening");
        setInterimTranscript("");
        setError(null);
      };

      recognition.onresult = (event: SpeechRecognitionEventLike) => {
        let interim = "";
        let final = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          const text = item[0]?.transcript || "";
          if (item.isFinal) {
            final += text;
          } else {
            interim += text;
          }
        }

        if (interim) {
          setInterimTranscript(interim);
        }

        if (final.trim()) {
          setInterimTranscript("");
          setInternalRecState("processing");

          // Check safety boundaries
          const safetyCheck = verifyVoiceSafetyBoundary(final);
          if (safetyCheck.hasEmergencyKeywords && safetyCheck.safetyNotice) {
            setSafetyNotice(safetyCheck.safetyNotice);
          }

          if (onTranscriptRef.current) {
            onTranscriptRef.current(final.trim());
          }
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEventLike) => {
        const errType = event.error;
        let message = "Speech recognition error occurred.";

        if (errType === "not-allowed" || errType === "service-not-allowed") {
          message = "Microphone access was denied. You can continue typing your question below.";
        } else if (errType === "no-speech") {
          message = "No speech was detected. Please try speaking again.";
        } else if (errType === "audio-capture") {
          message = "No microphone hardware found. Please verify your audio input device.";
        } else if (errType === "network") {
          message = "Browser speech recognition service is unreachable. Please use text chat.";
        } else if (errType === "aborted") {
          // User cancelled; no error display needed
          setInternalRecState("idle");
          setInterimTranscript("");
          return;
        }

        setError(message);
        setInternalRecState("error");
        setInterimTranscript("");
      };

      recognition.onend = () => {
        setInternalRecState("idle");
        setInterimTranscript("");
      };

      recognition.start();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start speech recognition.";
      setError(msg);
      setInternalRecState("error");
    }
  }, [hasConsent, isRecognitionSupported, selectedLanguage]);

  // Grant consent handler
  const grantConsent = useCallback(() => {
    setHasConsent(true);
    setNeedsConsentModal(false);
    try {
      localStorage.setItem("safeshe_voice_consent", "true");
    } catch {
      // ignore
    }
    // Automatically trigger listening upon consent
    setTimeout(() => {
      startListening();
    }, 50);
  }, [startListening]);

  // Deny consent handler
  const denyConsent = useCallback(() => {
    setHasConsent(false);
    setNeedsConsentModal(false);
    setInternalRecState("idle");
  }, []);

  // Stop active speech playback
  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setInternalSynState("idle");
    setSpeakingMessageId(null);
  }, []);

  // Speak a specific message
  const speakMessage = useCallback(
    (messageId: string, rawText: string) => {
      if (!isSynthesisSupported || typeof window === "undefined" || !window.speechSynthesis) {
        return;
      }

      // If already speaking this message, toggle off
      if (synthesisState === "speaking" && speakingMessageId === messageId) {
        stopSpeaking();
        return;
      }

      // Stop any prior speech
      window.speechSynthesis.cancel();

      const cleaned = cleanTextForSpeech(rawText);
      if (!cleaned) return;

      const utterance = new SpeechSynthesisUtterance(cleaned);
      utterance.lang = selectedLanguage;
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      // Select natural voice matching language if available
      try {
        const voices = window.speechSynthesis.getVoices();
        const matchingVoice = voices.find((v) => v.lang.startsWith(selectedLanguage.split("-")[0]));
        if (matchingVoice) {
          utterance.voice = matchingVoice;
        }
      } catch {
        // Fall back to browser default
      }

      utterance.onstart = () => {
        setInternalSynState("speaking");
        setSpeakingMessageId(messageId);
        lastSpokenMessageIdRef.current = messageId;
      };

      utterance.onend = () => {
        setInternalSynState("idle");
        setSpeakingMessageId(null);
      };

      utterance.onerror = () => {
        setInternalSynState("idle");
        setSpeakingMessageId(null);
      };

      window.speechSynthesis.speak(utterance);
    },
    [isSynthesisSupported, synthesisState, speakingMessageId, selectedLanguage, stopSpeaking]
  );

  // Hook into incoming assistant messages for optional autoReadAloud
  const handleIncomingMessage = useCallback(
    (messageId: string, content: string, role: string) => {
      if (
        role === "assistant" &&
        autoReadAloud &&
        messageId !== lastSpokenMessageIdRef.current &&
        isSynthesisSupported
      ) {
        speakMessage(messageId, content);
      }
    },
    [autoReadAloud, isSynthesisSupported, speakMessage]
  );

  return {
    // States
    recognitionState,
    synthesisState,
    error,
    interimTranscript,
    hasConsent,
    needsConsentModal,
    autoReadAloud,
    speakingMessageId,
    selectedLanguage,
    safetyNotice,
    isRecognitionSupported,
    isSynthesisSupported,

    // Actions
    startListening,
    stopListening,
    cancelListening,
    speakMessage,
    stopSpeaking,
    grantConsent,
    denyConsent,
    toggleAutoReadAloud,
    setSelectedLanguage,
    handleIncomingMessage,
    clearSafetyNotice: () => setSafetyNotice(null),
    clearError: () => setError(null),
  };
}
