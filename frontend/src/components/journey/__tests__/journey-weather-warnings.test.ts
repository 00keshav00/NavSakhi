import test, { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  isWeatherUnavailableWarning,
  filterJourneyWarnings,
} from "../route-sync-utils.ts";
import type { JourneyPlanResponse, MultimodalRoute } from "../../../types/journey.ts";

describe("NavSakhi Phase 51.78: Journey Planner Weather Warning Suppression Suite", () => {
  describe("1. isWeatherUnavailableWarning Predicate", () => {
    it("identifies primary backend weather unavailable warning", () => {
      const msg = "Live weather data is currently unavailable from provider.";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("identifies secondary provider hazard unavailable warning", () => {
      const msg = "Live weather information unavailable";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("identifies rate-limit cooldown weather warning", () => {
      const msg = "Live weather information unavailable (rate limit cooldown)";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("identifies temporary unreachable weather provider warning", () => {
      const msg = "Live weather provider is temporarily unreachable.";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("identifies alternative phrasing for unavailable live weather", () => {
      const msg = "Live weather data currently unavailable";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("identifies weather provider timeout warning", () => {
      const msg = "Live weather service timed out";
      assert.equal(isWeatherUnavailableWarning(msg), true);
    });

    it("strictly preserves the no-practical-transit routing warning", () => {
      const transitMsg =
        "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.";
      assert.equal(isWeatherUnavailableWarning(transitMsg), false);
    });

    it("strictly preserves legitimate environmental/corridor safety notices", () => {
      const safetyMsg =
        "Caution: Low lighting detected on pedestrian segment between 22:00 and 04:00.";
      assert.equal(isWeatherUnavailableWarning(safetyMsg), false);
    });

    it("strictly preserves zero-distance destination notices", () => {
      const destMsg = "You are already at your destination. Distance: 0 km.";
      assert.equal(isWeatherUnavailableWarning(destMsg), false);
    });

    it("strictly preserves legitimate real-world weather hazard advisories", () => {
      const severeAlert =
        "Severe weather alert: High wind and flash flood advisory along corridor";
      assert.equal(isWeatherUnavailableWarning(severeAlert), false);
    });

    it("returns false for non-string, empty, or null inputs", () => {
      assert.equal(isWeatherUnavailableWarning(""), false);
      assert.equal(isWeatherUnavailableWarning(null as any), false);
      assert.equal(isWeatherUnavailableWarning(undefined as any), false);
      assert.equal(isWeatherUnavailableWarning(123 as any), false);
    });
  });

  describe("2. filterJourneyWarnings Presentation Filter", () => {
    it("suppresses single weather unavailable warning, resulting in empty warning panel", () => {
      const input = ["Live weather data is currently unavailable from provider."];
      const result = filterJourneyWarnings(input);
      assert.deepEqual(result, []);
      assert.equal(result.length, 0);
    });

    it("suppresses duplicate weather warning variants, leaving 0 warnings", () => {
      const input = [
        "Live weather data is currently unavailable from provider.",
        "Live weather information unavailable",
      ];
      const result = filterJourneyWarnings(input);
      assert.deepEqual(result, []);
      assert.equal(result.length, 0);
    });

    it("preserves no-practical-transit warning when received alone", () => {
      const transitMsg =
        "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.";
      const input = [transitMsg];
      const result = filterJourneyWarnings(input);
      assert.deepEqual(result, [transitMsg]);
      assert.equal(result.length, 1);
    });

    it("retains the no-practical-transit warning while eliminating both weather warning variants", () => {
      const transitMsg =
        "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.";
      const input = [
        "Live weather data is currently unavailable from provider.",
        transitMsg,
        "Live weather information unavailable",
      ];
      const result = filterJourneyWarnings(input);
      assert.deepEqual(result, [transitMsg]);
      assert.equal(result.length, 1);
      assert.equal(result[0], transitMsg);
    });

    it("preserves multiple legitimate non-weather warnings", () => {
      const transitMsg =
        "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.";
      const safetyNotice = "Pedestrian crossing construction near segment 2.";
      const input = [
        "Live weather data is currently unavailable from provider.",
        transitMsg,
        safetyNotice,
      ];
      const result = filterJourneyWarnings(input);
      assert.deepEqual(result, [transitMsg, safetyNotice]);
      assert.equal(result.length, 2);
    });

    it("handles null, undefined, and empty arrays safely", () => {
      assert.deepEqual(filterJourneyWarnings(null), []);
      assert.deepEqual(filterJourneyWarnings(undefined), []);
      assert.deepEqual(filterJourneyWarnings([]), []);
    });
  });

  describe("3. Frozen Journey Features Preservation", () => {
    it("ensures route cards, scores, coverage, night activity, and geometry remain intact", () => {
      const mockRoute: MultimodalRoute = {
        id: "route-real-1",
        rank: 1,
        route_name: "Verified Road Route",
        mode: "road",
        travel_mode_chain: "cab",
        eta: "32 min",
        distance: "14.2 km",
        cost: "₹180",
        safety_score: 87.4,
        overall_safety_score: 87.4,
        score_status: "READY",
        scoreable_coverage_ratio: 0.94,
        is_recommended: true,
        ranking_labels: ["SAFEST", "SHORTEST"],
        environmental_risk: 12.6,
        model_explainability: { feature_police: "High proximity" },
        recommendation_reason: ["Safest road route with continuous surveillance"],
        strengths: ["High lighting", "Active emergency stations"],
        night_activity_score: {
          overall_score: 48,
          coverage_score: 55,
          isolation_penalty: 10,
          density_score: 45,
          emergency_score: 70,
          confidence_score: 85,
          status: "AVAILABLE",
        },
        segments: [
          {
            segment_id: "seg-101",
            segment_name: "Mount Road",
            transport_mode: "driving",
            distance: "14200 m",
            eta: "32 min",
            color: "#10b981",
            environmental_risk: 12.6,
            reason: "Verified primary arterial road",
            distance_m: 14200,
            duration_s: 1920,
            polyline: {
              type: "Feature",
              geometry: {
                type: "LineString",
                coordinates: [
                  [80.2024, 13.0067],
                  [80.2707, 13.0827],
                ],
              },
              properties: {},
            },
          },
        ],
      };

      const mockPlanResponse: JourneyPlanResponse = {
        journey_id: "journey-51-78-freeze-test",
        recommended_routes: [mockRoute],
        source_loc: [80.2024, 13.0067],
        dest_loc: [80.2707, 13.0827],
        zero_distance: false,
        warnings: [
          "Live weather data is currently unavailable from provider.",
          "Live weather information unavailable",
          "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.",
        ],
      };

      // Verify original response properties
      assert.equal(mockPlanResponse.recommended_routes.length, 1);
      assert.equal(mockPlanResponse.recommended_routes[0].safety_score, 87.4);
      assert.equal(mockPlanResponse.recommended_routes[0].scoreable_coverage_ratio, 0.94);
      assert.equal(mockPlanResponse.recommended_routes[0].night_activity_score?.overall_score, 48);
      const geom = mockPlanResponse.recommended_routes[0].segments[0].polyline.geometry as GeoJSON.LineString;
      assert.equal(geom.coordinates.length, 2);

      // Apply the presentation warnings filter as done in JourneyPage
      const filteredWarnings = filterJourneyWarnings(mockPlanResponse.warnings);

      // Verify that warnings are filtered
      assert.equal(filteredWarnings.length, 1);
      assert.equal(
        filteredWarnings[0],
        "No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives."
      );

      // Verify all other journey features are 100% frozen and untouched
      assert.equal(mockPlanResponse.recommended_routes[0].safety_score, 87.4);
      assert.equal(mockPlanResponse.recommended_routes[0].score_status, "READY");
      assert.equal(mockPlanResponse.recommended_routes[0].scoreable_coverage_ratio, 0.94);
      assert.equal(mockPlanResponse.recommended_routes[0].night_activity_score?.overall_score, 48);
      assert.equal(mockPlanResponse.recommended_routes[0].night_activity_score?.coverage_score, 55);
      assert.equal(mockPlanResponse.recommended_routes[0].segments[0].polyline.geometry.type, "LineString");
      assert.deepEqual(geom.coordinates, [
        [80.2024, 13.0067],
        [80.2707, 13.0827],
      ]);
    });
  });
});
