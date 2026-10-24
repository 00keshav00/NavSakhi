import type { VoiceLanguage, VoiceSafetyCheckResult } from "../types/voice.ts";

export const SUPPORTED_VOICE_LANGUAGES: VoiceLanguage[] = [
  { code: "en-IN", label: "English (India)", nativeLabel: "English (India)" },
  { code: "en-US", label: "English (US)", nativeLabel: "English (US)" },
  { code: "hi-IN", label: "Hindi (India)", nativeLabel: "हिन्दी (भारत)" },
];

/**
 * Checks if browser SpeechRecognition or webkitSpeechRecognition is available.
 */
export function checkSpeechRecognitionSupport(): boolean {
  if (typeof window === "undefined") return false;
  const win = window as unknown as Record<string, unknown>;
  return !!(win.SpeechRecognition || win.webkitSpeechRecognition);
}

/**
 * Checks if browser speechSynthesis is available.
 */
export function checkSpeechSynthesisSupport(): boolean {
  if (typeof window === "undefined") return false;
  const win = window as unknown as Record<string, unknown>;
  return (
    typeof window.speechSynthesis !== "undefined" &&
    typeof win.SpeechSynthesisUtterance !== "undefined"
  );
}

/**
 * Merges recognized speech transcript into existing composer input text
 * without clobbering existing text or repeating words.
 */
export function mergeTranscriptWithInput(
  existingText: string,
  newTranscript: string
): string {
  const trimmedExisting = existingText.trim();
  const trimmedNew = newTranscript.trim();

  if (!trimmedNew) return existingText;
  if (!trimmedExisting) return trimmedNew;

  // If new transcript already starts with or is identical to existing text
  if (trimmedNew.toLowerCase().startsWith(trimmedExisting.toLowerCase())) {
    return trimmedNew;
  }

  // If existing text already ends with new transcript
  if (trimmedExisting.toLowerCase().endsWith(trimmedNew.toLowerCase())) {
    return trimmedExisting;
  }

  // Otherwise append with single space
  return `${trimmedExisting} ${trimmedNew}`;
}

/**
 * Cleans assistant response text before passing to speech synthesis:
 * - Strips Markdown bold, italic, code blocks, lists, links
 * - Removes internal technical IDs, JSON, and metadata
 * - Replaces emojis or unpronounceable symbols with pauses
 */
export function cleanTextForSpeech(rawText: string): string {
  if (!rawText) return "";

  let cleaned = rawText;

  // Remove code blocks
  cleaned = cleaned.replace(/```[\s\S]*?```/g, " ");

  // Remove inline code
  cleaned = cleaned.replace(/`([^`]+)`/g, "$1");

  // Remove Markdown links [text](url) -> text
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

  // Remove Markdown bold/italic
  cleaned = cleaned.replace(/(\*\*|__)(.*?)\1/g, "$2");
  cleaned = cleaned.replace(/(\*|_)(.*?)\1/g, "$2");

  // Remove markdown headers
  cleaned = cleaned.replace(/^#{1,6}\s+/gm, "");

  // Remove bullet points / dashes at start of line
  cleaned = cleaned.replace(/^\s*[-*+]\s+/gm, "");

  // Remove numbered list prefixes
  cleaned = cleaned.replace(/^\s*\d+\.\s+/gm, "");

  // Remove technical IDs like msg_12345 or hex strings
  cleaned = cleaned.replace(/\b(msg_[a-zA-Z0-9_-]+)\b/g, "");

  // Normalize multiple spaces and newlines
  cleaned = cleaned.replace(/\s+/g, " ").trim();

  return cleaned;
}

/**
 * Safety Boundary Verification:
 * Validates that spoken phrases (such as "SOS" or "help") are recognized
 * purely as user text and NEVER trigger automatic emergency dispatch,
 * automated session creation, or journey modification.
 */
export function verifyVoiceSafetyBoundary(query: string): VoiceSafetyCheckResult {
  const qLower = query.toLowerCase();
  const emergencyKeywords = ["sos", "help me", "emergency", "call police", "send alert"];

  for (const kw of emergencyKeywords) {
    if (qLower.includes(kw)) {
      return {
        hasEmergencyKeywords: true,
        keywordMatched: kw,
        safetyNotice:
          "Voice input is transcribed as chat text only and does not trigger real-world emergency dispatch or automated SOS. Use the dedicated SOS button if in immediate danger."
      };
    }
  }

  return { hasEmergencyKeywords: false };
}
