import type { JourneyPlanResponse } from "../types/journey.ts";

export interface PendingJourneyDraft {
  source: string;
  destination: string;
  preferences: string[];
  travelTime?: string;
  selectedRouteId?: string;
  routesData?: JourneyPlanResponse | null;
  savedAt: number; // timestamp in milliseconds
}

const STORAGE_KEY = "safeshe_pending_journey_draft";
const DRAFT_EXPIRY_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Saves non-secret journey draft to session-scoped storage.
 * Strictly does not contain credentials, tokens, or passwords.
 */
export function savePendingJourneyDraft(draft: Omit<PendingJourneyDraft, "savedAt">): void {
  if (typeof window === "undefined" || !window.sessionStorage) {
    return;
  }

  try {
    const payload: PendingJourneyDraft = {
      source: draft.source?.trim() || "",
      destination: draft.destination?.trim() || "",
      preferences: Array.isArray(draft.preferences) ? draft.preferences : [],
      travelTime: draft.travelTime,
      selectedRouteId: draft.selectedRouteId,
      routesData: draft.routesData || null,
      savedAt: Date.now(),
    };

    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (err) {
    console.warn("[pendingJourneyStorage] Failed to save journey draft to sessionStorage:", err);
  }
}

/**
 * Retrieves and validates the pending journey draft.
 * Verifies non-empty origin/destination and ensures draft has not expired.
 * Cleans up expired or malformed drafts safely.
 */
export function getPendingJourneyDraft(): PendingJourneyDraft | null {
  if (typeof window === "undefined" || !window.sessionStorage) {
    return null;
  }

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as Partial<PendingJourneyDraft>;
    if (!parsed || typeof parsed !== "object") {
      clearPendingJourneyDraft();
      return null;
    }

    // Expiry verification (30 minutes)
    const savedAt = typeof parsed.savedAt === "number" ? parsed.savedAt : 0;
    if (Date.now() - savedAt > DRAFT_EXPIRY_MS) {
      clearPendingJourneyDraft();
      return null;
    }

    // Structural validation: must contain valid non-empty source and destination
    if (!parsed.source || !parsed.destination || typeof parsed.source !== "string" || typeof parsed.destination !== "string") {
      clearPendingJourneyDraft();
      return null;
    }

    return {
      source: parsed.source,
      destination: parsed.destination,
      preferences: Array.isArray(parsed.preferences) ? parsed.preferences : [],
      travelTime: typeof parsed.travelTime === "string" ? parsed.travelTime : undefined,
      selectedRouteId: typeof parsed.selectedRouteId === "string" ? parsed.selectedRouteId : undefined,
      routesData: parsed.routesData || null,
      savedAt,
    };
  } catch (err) {
    console.warn("[pendingJourneyStorage] Failed to parse pending journey draft:", err);
    clearPendingJourneyDraft();
    return null;
  }
}

/**
 * Clears the consumed or invalidated pending journey draft so it is never replayed.
 */
export function clearPendingJourneyDraft(): void {
  if (typeof window === "undefined" || !window.sessionStorage) {
    return;
  }

  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore errors during removal
  }
}
