import test, { describe, it } from "node:test";
import assert from "node:assert/strict";
import { apiClient } from "../../client.ts";
import { journeyService } from "../journeyService.ts";
import type { JourneyCreateRequest } from "../../../types/journey.ts";

describe("NavSakhi Phase 51.60: Journey Client Timeout Configuration Suite", () => {
  it("1. planJourney specifies temporary 120,000ms timeout override in Axios config", async () => {
    let capturedUrl = "";
    let capturedConfig: any = undefined;

    // Temporarily spy on apiClient.post
    const originalPost = apiClient.post;
    apiClient.post = (async (url: string, data: unknown, config?: any) => {
      capturedUrl = url;
      capturedConfig = config;
      return {
        data: {
          success: true,
          data: {
            journey_id: "test-journey-id",
            recommended_routes: [],
          },
        },
      } as any;
    }) as any;

    try {
      const mockRequest: JourneyCreateRequest = {
        source: "Tambaram, Chennai",
        destination: "Chennai Central, Chennai",
      };

      await journeyService.planJourney(mockRequest);

      assert.equal(capturedUrl, "/api/v1/journeys/");
      assert.ok(capturedConfig, "Axios request configuration was provided");
      assert.equal(
        capturedConfig?.timeout,
        120000,
        "Journey plan request must explicitly specify timeout: 120000"
      );
    } finally {
      apiClient.post = originalPost;
    }
  });

  it("2. Autocomplete and lifecycle endpoints do not set the 120,000ms timeout", async () => {
    let capturedGetConfig: any = undefined;
    let capturedPostConfig: any = undefined;

    const originalGet = apiClient.get;
    const originalPost = apiClient.post;

    apiClient.get = (async (url: string, config?: any) => {
      capturedGetConfig = config;
      return {
        data: {
          success: true,
          data: [],
        },
      } as any;
    }) as any;

    apiClient.post = (async (url: string, data: unknown, config?: any) => {
      capturedPostConfig = config;
      return {
        data: {
          success: true,
          data: {},
        },
      } as any;
    }) as any;

    try {
      await journeyService.autocomplete("Guindy");
      assert.notEqual(
        capturedGetConfig?.timeout,
        120000,
        "Autocomplete must not override timeout with 120000ms"
      );

      await journeyService.startJourney("j-123", "r-456");
      assert.notEqual(
        capturedPostConfig?.timeout,
        120000,
        "startJourney must not override timeout with 120000ms"
      );
    } finally {
      apiClient.get = originalGet;
      apiClient.post = originalPost;
    }
  });

  it("3. Axios default client baseline remains 60,000ms for all standard requests", () => {
    assert.equal(
      apiClient.defaults.timeout,
      60000,
      "Base apiClient timeout must remain 60000ms default"
    );
  });
});
