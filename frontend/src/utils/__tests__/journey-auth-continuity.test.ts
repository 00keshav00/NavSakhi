import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  savePendingJourneyDraft,
  getPendingJourneyDraft,
  clearPendingJourneyDraft,
  type PendingJourneyDraft,
} from "../pendingJourneyStorage.ts";
import { getSafeRedirectUrl, getFriendlyRedirectInfo } from "../safeRedirect.ts";

// Minimal global sessionStorage mock for Node.js test environment
const mockStorage: Record<string, string> = {};
const mockSessionStorage = {
  getItem: (key: string) => mockStorage[key] || null,
  setItem: (key: string, value: string) => { mockStorage[key] = String(value); },
  removeItem: (key: string) => { delete mockStorage[key]; },
  clear: () => {
    for (const key of Object.keys(mockStorage)) {
      delete mockStorage[key];
    }
  },
};

// Polyfill window.sessionStorage in Node test runtime if missing
if (typeof globalThis.window === "undefined") {
  (globalThis as unknown as { window: { sessionStorage: Storage } }).window = {
    sessionStorage: mockSessionStorage as unknown as Storage,
  };
} else if (!globalThis.window.sessionStorage) {
  (globalThis.window as unknown as { sessionStorage: Storage }).sessionStorage =
    mockSessionStorage as unknown as Storage;
}

describe("Phase 51.93 — Journey Authentication Continuity & Safe Redirects", () => {
  beforeEach(() => {
    mockSessionStorage.clear();
  });

  describe("Pending Journey Storage", () => {
    it("preserves journey inputs, selected route, and route data in session storage", () => {
      savePendingJourneyDraft({
        source: "Guindy Railway Station",
        destination: "Tidel Park",
        preferences: ["well_lit", "prefer_transit"],
        travelTime: "20:30",
        selectedRouteId: "route_test_123",
        routesData: {
          recommended_routes: [
            {
              id: "route_test_123",
              name: "Transit Safe Route",
              total_duration: "35 mins",
              total_distance: "8.2 km",
              safety_score: 88,
              mode_summary: ["walk", "train"],
              segments: [],
            } as unknown as NonNullable<PendingJourneyDraft["routesData"]>["recommended_routes"][0],
          ],
          source_coords: [13.0067, 80.2023],
          dest_coords: [12.9892, 80.2486],
        } as unknown as NonNullable<PendingJourneyDraft["routesData"]>,
      });

      const draft = getPendingJourneyDraft();
      assert.ok(draft !== null);
      assert.equal(draft?.source, "Guindy Railway Station");
      assert.equal(draft?.destination, "Tidel Park");
      assert.equal(draft?.selectedRouteId, "route_test_123");
      assert.deepEqual(draft?.preferences, ["well_lit", "prefer_transit"]);
      assert.equal(draft?.routesData?.recommended_routes.length, 1);
    });

    it("expires draft after 30 minutes TTL and clears safely", () => {
      const thirtyOneMinutesAgo = Date.now() - 31 * 60 * 1000;
      const expiredPayload: PendingJourneyDraft = {
        source: "Koyambedu",
        destination: "Marina Beach",
        preferences: [],
        savedAt: thirtyOneMinutesAgo,
      };

      mockSessionStorage.setItem("safeshe_pending_journey_draft", JSON.stringify(expiredPayload));

      const retrieved = getPendingJourneyDraft();
      assert.equal(retrieved, null);
      assert.equal(mockSessionStorage.getItem("safeshe_pending_journey_draft"), null);
    });

    it("handles corrupted or invalid JSON in session storage safely", () => {
      mockSessionStorage.setItem("safeshe_pending_journey_draft", "INVALID_NON_JSON_DATA{{{");

      const retrieved = getPendingJourneyDraft();
      assert.equal(retrieved, null);
      assert.equal(mockSessionStorage.getItem("safeshe_pending_journey_draft"), null);
    });

    it("clears pending journey state on demand so it cannot be replayed", () => {
      savePendingJourneyDraft({
        source: "Central",
        destination: "Airport",
        preferences: [],
      });

      assert.ok(getPendingJourneyDraft() !== null);
      clearPendingJourneyDraft();
      assert.equal(getPendingJourneyDraft(), null);
    });
  });

  describe("Safe Redirect URL Validation", () => {
    it("allows recognized internal routes with query params", () => {
      assert.equal(getSafeRedirectUrl("/journey"), "/journey");
      assert.equal(getSafeRedirectUrl("/journey?origin=draft"), "/journey?origin=draft");
      assert.equal(getSafeRedirectUrl("/live?journeyId=123"), "/live?journeyId=123");
      assert.equal(getSafeRedirectUrl("/settings"), "/settings");
      assert.equal(getSafeRedirectUrl("/profile"), "/profile");
      assert.equal(getSafeRedirectUrl("/home"), "/home");
      assert.equal(getSafeRedirectUrl("/assistant"), "/assistant");
      assert.equal(getSafeRedirectUrl("/resources"), "/resources");
      assert.equal(getSafeRedirectUrl("/safety-guidelines"), "/safety-guidelines");
      assert.equal(getSafeRedirectUrl("/about"), "/about");
      assert.equal(getSafeRedirectUrl("/help"), "/help");
      assert.equal(getSafeRedirectUrl("/limitations"), "/limitations");
      assert.equal(getSafeRedirectUrl("/terms"), "/terms");
      assert.equal(getSafeRedirectUrl("/privacy"), "/privacy");
      assert.equal(getSafeRedirectUrl("/accessibility"), "/accessibility");
    });

    it("rejects open redirect attempts with external domains", () => {
      assert.equal(getSafeRedirectUrl("https://evil.com"), "/home");
      assert.equal(getSafeRedirectUrl("http://attacker.org/phish"), "/home");
      assert.equal(getSafeRedirectUrl("//malicious-site.com"), "/home");
      assert.equal(getSafeRedirectUrl("/\\attacker.com"), "/home");
    });

    it("rejects dangerous URI schemes like javascript: or data:", () => {
      assert.equal(getSafeRedirectUrl("javascript:alert(1)"), "/home");
      assert.equal(getSafeRedirectUrl("data:text/html,<script>alert(1)</script>"), "/home");
    });

    it("rejects unrecognized internal paths and falls back safely", () => {
      assert.equal(getSafeRedirectUrl("/admin/secret"), "/home");
      assert.equal(getSafeRedirectUrl("/unknown_path"), "/home");
      assert.equal(getSafeRedirectUrl(null), "/home");
      assert.equal(getSafeRedirectUrl(""), "/home");
    });
  });

  describe("Friendly Redirect Copy Mapping", () => {
    it("replaces raw route /journey with friendly, empathetic copy", () => {
      const info = getFriendlyRedirectInfo("/journey");
      assert.equal(info.message, "Sign in to continue your journey.");
      assert.equal(info.label, "continue your journey");
      assert.equal(info.safePath, "/journey");
    });

    it("provides friendly copy for settings, live monitoring, dashboard, and legal pages", () => {
      assert.equal(getFriendlyRedirectInfo("/settings").message, "Sign in to access account settings.");
      assert.equal(getFriendlyRedirectInfo("/live").message, "Sign in to access live journey monitoring.");
      assert.equal(getFriendlyRedirectInfo("/home").message, "Sign in to access your dashboard.");
      assert.equal(getFriendlyRedirectInfo("/safety-guidelines").message, "You can view safety guidelines directly without signing in, or sign in below to continue.");
      assert.equal(getFriendlyRedirectInfo("/privacy").message, "You can review our privacy policy directly without signing in, or sign in below to continue.");
      assert.equal(getFriendlyRedirectInfo("/limitations").message, "You can review AI and ML limitations directly without signing in, or sign in below to continue.");
      assert.equal(getFriendlyRedirectInfo("/terms").message, "You can review terms and conditions directly without signing in, or sign in below to continue.");
    });
  });
});
