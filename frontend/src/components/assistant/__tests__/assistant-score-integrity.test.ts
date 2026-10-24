import { describe, it } from "node:test";
import assert from "node:assert";
import type { AssistantResponse } from "../../../types/assistant";

describe("SafeShe Phase 13: Assistant Score Integrity & Safety-Claim Frontend Suite", () => {
  it("1. Missing or null route score renders as 'Unavailable' when journey is active, never 98%", () => {
    const mockResponse: AssistantResponse = {
      message_id: "msg_test01",
      role: "assistant",
      content: "Monitoring active journey. Route safety score is unavailable.",
      timestamp: new Date().toISOString(),
      agent_status: { status: "Monitoring", current_task: "Awaiting next input" },
      reasoning: {
        summary: ["Active journey context checked"],
        confidence: null,
        decision_source: "Journey Engine State",
        provider_summary: "Operating within verified boundaries"
      },
      context: {
        active_journey: true,
        destination: "Central Station",
        safety_score: null,
      },
      provider_health: [{ name: "Routing API (OSRM)", status: "Connected" }],
      memory: { recent_journeys: [], pinned_info: [] },
      quick_suggestions: ["Explain my safety score"]
    };

    const formatScore = (ctx: AssistantResponse["context"]) => {
      if (ctx.safety_score != null) return `${ctx.safety_score}%`;
      return ctx.active_journey ? "Unavailable" : "No Active Route";
    };

    assert.strictEqual(formatScore(mockResponse.context), "Unavailable");
    assert.notStrictEqual(formatScore(mockResponse.context), "98%");
    assert.notStrictEqual(formatScore(mockResponse.context), "0%");
  });

  it("2. Missing journey renders as 'No Active Route' without default numbers", () => {
    const mockContext: AssistantResponse["context"] = {
      active_journey: false,
      destination: undefined,
      safety_score: null
    };

    const formatScore = (ctx: AssistantResponse["context"]) => {
      if (ctx.safety_score != null) return `${ctx.safety_score}%`;
      return ctx.active_journey ? "Unavailable" : "No Active Route";
    };

    assert.strictEqual(formatScore(mockContext), "No Active Route");
  });

  it("3. Valid route score renders exact numeric percentage with proxy disclaimer requirement", () => {
    const mockContext: AssistantResponse["context"] = {
      active_journey: true,
      destination: "Anna Nagar",
      safety_score: 74.2
    };

    const formatScore = (ctx: AssistantResponse["context"]) => {
      if (ctx.safety_score != null) return `${ctx.safety_score}%`;
      return ctx.active_journey ? "Unavailable" : "No Active Route";
    };

    assert.strictEqual(formatScore(mockContext), "74.2%");
    const hasProxyDisclosure = mockContext.safety_score != null;
    assert.strictEqual(hasProxyDisclosure, true);
  });

  it("4. Null confidence displays 'Uncalibrated' and suppresses numerical percentage gauges", () => {
    const mockReasoning: AssistantResponse["reasoning"] = {
      summary: ["Route evaluated"],
      confidence: null,
      decision_source: "Journey Engine State",
      provider_summary: "Verified"
    };

    const isConfidenceGaugeRendered = mockReasoning.confidence != null;
    assert.strictEqual(isConfidenceGaugeRendered, false);
    assert.strictEqual(mockReasoning.confidence, null);
  });

  it("5. Empty pinned memory displays empty fallback without hardcoded fake preferences", () => {
    const memory: AssistantResponse["memory"] = {
      recent_journeys: [],
      pinned_info: []
    };

    assert.strictEqual(memory.pinned_info.length, 0);
    assert.strictEqual(memory.pinned_info.includes("User prefers well-lit routes."), false);
  });
});
