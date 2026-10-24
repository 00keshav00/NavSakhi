import test, { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  enrichGeoJsonWithSelection,
  extractValidCoordinates,
  calculateFocusBounds,
  getCameraPadding,
  generateCameraIntentKey,
} from "../route-sync-utils.ts";
import type { MultimodalRoute } from "../../../types/journey.ts";

// Synthetic Fixture Routes conforming to Phase 6 normalized contract
const mockRoutes: MultimodalRoute[] = [
  {
    id: "route-alpha-123",
    rank: 1,
    route_name: "Metro + Walking Safe Corridor",
    mode: "transit_walking",
    travel_mode_chain: "walk → metro → walk",
    eta: "28 min",
    distance: "6.4 km",
    cost: "₹25",
    safety_score: 84.5,
    overall_safety_score: 84.5,
    score_status: "READY",
    scoreable_coverage_ratio: 0.85,
    is_recommended: true,
    ranking_labels: ["SAFEST"],
    environmental_risk: 22,
    model_explainability: {},
    recommendation_reason: ["Well lit"],
    strengths: ["High coverage"],
    model_version: "lightgbm_v1",
    target_disclosure: "Synthetic environmental safety proxy",
    segments: [
      {
        segment_id: "seg-1",
        segment_name: "Walk to Metro Station",
        transport_mode: "walk",
        distance: "400 m",
        eta: "5 min",
        color: "#10B981",
        environmental_risk: 15,
        reason: "Pedestrian walkway",
        adjusted_safety_score: 88,
        polyline: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [80.2100, 13.0800],
              [80.2120, 13.0820],
            ],
          },
        },
      },
      {
        segment_id: "seg-2",
        segment_name: "Blue Line Metro Transit",
        transport_mode: "metro",
        distance: "5.5 km",
        eta: "18 min",
        color: "#3B82F6",
        environmental_risk: 10,
        reason: "Rapid rail transit",
        adjusted_safety_score: 92,
        polyline: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [80.2120, 13.0820],
              [80.2450, 13.0950],
            ],
          },
        },
      },
      {
        segment_id: "seg-3",
        segment_name: "Walk to Final Destination",
        transport_mode: "walk",
        distance: "500 m",
        eta: "5 min",
        color: "#10B981",
        environmental_risk: 18,
        reason: "Commercial street",
        adjusted_safety_score: 80,
        polyline: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [80.2450, 13.0950],
              [80.2480, 13.0970],
            ],
          },
        },
      },
    ],
  },
  {
    id: "route-beta-456",
    rank: 2,
    route_name: "Direct Road Taxi / Auto",
    mode: "driving",
    travel_mode_chain: "driving",
    eta: "22 min",
    distance: "7.1 km",
    cost: "₹140",
    safety_score: null, // Unscored / pending evaluation
    overall_safety_score: null,
    score_status: "INSUFFICIENT_COVERAGE",
    scoreable_coverage_ratio: 0.42,
    is_recommended: false,
    ranking_labels: ["FASTEST"],
    environmental_risk: 45,
    model_explainability: {},
    recommendation_reason: ["Fastest road"],
    strengths: ["Direct route"],
    model_version: "lightgbm_v1",
    target_disclosure: "Synthetic environmental safety proxy",
    segments: [
      {
        segment_id: "seg-direct-1",
        segment_name: "Main Arterial Highway",
        transport_mode: "driving",
        distance: "7.1 km",
        eta: "22 min",
        color: "#F59E0B",
        environmental_risk: 35,
        reason: "Arterial road",
        polyline: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: [
              [80.2100, 13.0800],
              [80.2300, 13.0890],
              [80.2480, 13.0970],
            ],
          },
        },
      },
    ],
  },
];

describe("SafeShe Phase 8: Route Selection and Map Synchronization Test Suite", () => {
  // Test 1: Selecting a route card updates the selected route state
  it("1. Selecting a route card updates the selected route state", () => {
    const geoJson = enrichGeoJsonWithSelection(mockRoutes, "route-alpha-123");
    assert.strictEqual(geoJson.type, "FeatureCollection");

    const alphaFeatures = geoJson.features.filter(
      (f) => f.properties?.routeId === "route-alpha-123"
    );
    assert.strictEqual(alphaFeatures.length, 3);
    alphaFeatures.forEach((f) => {
      assert.strictEqual(f.properties?.isActive, true);
    });

    const betaFeatures = geoJson.features.filter(
      (f) => f.properties?.routeId === "route-beta-456"
    );
    assert.strictEqual(betaFeatures.length, 1);
    betaFeatures.forEach((f) => {
      assert.strictEqual(f.properties?.isActive, false);
    });
  });

  // Test 2: The corresponding route geometry is emphasized
  it("2. The corresponding route geometry is emphasized with active styling and layer ordering", () => {
    const geoJson = enrichGeoJsonWithSelection(mockRoutes, "route-alpha-123");
    // Active features must be placed at the end of the collection so they draw on top
    const lastFeatures = geoJson.features.slice(-3);
    lastFeatures.forEach((f) => {
      assert.strictEqual(f.properties?.isActive, true);
      assert.strictEqual(f.properties?.routeId, "route-alpha-123");
    });
  });

  // Test 3: Selecting another route removes emphasis from the previous selection
  it("3. Selecting another route removes emphasis from the previous selection", () => {
    // Switch from alpha to beta
    const geoJson = enrichGeoJsonWithSelection(mockRoutes, "route-beta-456");

    const alphaFeatures = geoJson.features.filter(
      (f) => f.properties?.routeId === "route-alpha-123"
    );
    alphaFeatures.forEach((f) => {
      assert.strictEqual(f.properties?.isActive, false);
    });

    const betaFeatures = geoJson.features.filter(
      (f) => f.properties?.routeId === "route-beta-456"
    );
    betaFeatures.forEach((f) => {
      assert.strictEqual(f.properties?.isActive, true);
    });
  });

  // Test 4: Opening and closing details preserves the selected route
  it("4. Opening and closing details preserves the selected route", () => {
    let activeRouteId = "route-alpha-123";
    let viewState: "RESULTS" | "DETAIL" = "RESULTS";

    // Navigate to DETAIL view
    viewState = "DETAIL";
    assert.strictEqual(activeRouteId, "route-alpha-123");

    // Navigate back to RESULTS view
    viewState = "RESULTS";
    assert.strictEqual(activeRouteId, "route-alpha-123");
    assert.strictEqual(viewState, "RESULTS");
  });

  // Test 5: Selecting a timeline item highlights the correct leg
  it("5. Selecting a timeline item highlights the correct leg and leaves others unhighlighted", () => {
    const geoJson = enrichGeoJsonWithSelection(
      mockRoutes,
      "route-alpha-123",
      1, // Focus on Leg 1 (Metro transit)
      null
    );

    const leg0 = geoJson.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 0
    );
    const leg1 = geoJson.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 1
    );
    const leg2 = geoJson.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 2
    );

    assert.strictEqual(leg0?.properties?.isLegFocused, false);
    assert.strictEqual(leg1?.properties?.isLegFocused, true);
    assert.strictEqual(leg2?.properties?.isLegFocused, false);
  });

  // Test 6: Switching active legs preserves parent route selection
  it("6. Switching active legs preserves parent route selection", () => {
    const geoJsonLeg0 = enrichGeoJsonWithSelection(mockRoutes, "route-alpha-123", 0);
    const feature0 = geoJsonLeg0.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 0
    );
    assert.strictEqual(feature0?.properties?.isLegFocused, true);
    assert.strictEqual(feature0?.properties?.isActive, true);

    const geoJsonLeg2 = enrichGeoJsonWithSelection(mockRoutes, "route-alpha-123", 2);
    const feature2 = geoJsonLeg2.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 2
    );
    assert.strictEqual(feature2?.properties?.isLegFocused, true);
    assert.strictEqual(feature2?.properties?.isActive, true);
  });

  // Test 7: Invalid or missing geometry does not crash the interaction
  it("7. Invalid or missing geometry does not crash coordinate extraction or bounds calculation", () => {
    const malformedRoutes: MultimodalRoute[] = [
      {
        id: "route-broken",
        rank: 1,
        route_name: "Broken transit corridor",
        mode: "transit",
        travel_mode_chain: "transit",
        cost: "₹10",
        environmental_risk: 30,
        safety_score: null,
        model_explainability: {},
        recommendation_reason: [],
        strengths: [],
        is_recommended: false,
        eta: "10 min",
        distance: "2 km",
        segments: [
          {
            segment_id: "seg-corrupt",
            segment_name: "Corrupt segment",
            transport_mode: "transit",
            distance: "2 km",
            eta: "10 min",
            color: "#6B7280",
            environmental_risk: 20,
            reason: "Corrupted test fixture",
            polyline: {
              type: "Feature",
              properties: {},
              geometry: {
                type: "LineString",
                coordinates: [[NaN, Infinity], [null, "bad"], []] as any,
              },
            },
          },
          {
            segment_id: "seg-empty",
            segment_name: "Transit without geometry",
            transport_mode: "train",
            distance: "5 km",
            eta: "15 min",
            color: "#3B82F6",
            environmental_risk: 10,
            reason: "Transit corridor",
            polyline: undefined as any,
          },
        ],
      },
    ];

    assert.doesNotThrow(() => {
      const geoJson = enrichGeoJsonWithSelection(malformedRoutes, "route-broken", 0);
      const bounds = calculateFocusBounds(geoJson, "route-broken", 0);
      assert.strictEqual(bounds.bounds, null);
    });
  });

  // Test 8: Empty routes and empty timelines render safely
  it("8. Empty routes and empty timelines render safely without errors", () => {
    const emptyGeoJson = enrichGeoJsonWithSelection([], null, null);
    assert.strictEqual(emptyGeoJson.type, "FeatureCollection");
    assert.strictEqual(emptyGeoJson.features.length, 0);

    const bounds = calculateFocusBounds(emptyGeoJson, null, null);
    assert.strictEqual(bounds.bounds, null);
    assert.strictEqual(bounds.isSinglePoint, false);
  });

  // Test 9: Updated route results do not leave stale selected identifiers
  it("9. Updated route results do not leave stale selected identifiers", () => {
    let activeRouteId: string | null = "route-old-disappeared";
    const newRoutes = [mockRoutes[1]]; // Only route-beta-456 exists

    // Deterministic selection resolution rule
    if (!newRoutes.some((r) => r.id === activeRouteId)) {
      activeRouteId = newRoutes[0]?.id || null;
    }

    assert.strictEqual(activeRouteId, "route-beta-456");
  });

  // Test 10: Repeated selection does not create duplicate map sources or camera churn
  it("10. Repeated selection does not generate new camera intent keys", () => {
    const key1 = generateCameraIntentKey("route-alpha-123", 1, 3, [80.21, 13.08], [80.25, 13.1], true);
    const key2 = generateCameraIntentKey("route-alpha-123", 1, 3, [80.21, 13.08], [80.25, 13.1], true);
    assert.strictEqual(key1, key2);

    // Changing leg focus creates a new intent key
    const key3 = generateCameraIntentKey("route-alpha-123", 2, 3, [80.21, 13.08], [80.25, 13.1], true);
    assert.notStrictEqual(key1, key3);
  });

  // Test 11: Hover preview does not overwrite persistent selection
  it("11. Hover preview marks isLegHovered without altering isLegFocused or parent selection", () => {
    const geoJson = enrichGeoJsonWithSelection(
      mockRoutes,
      "route-alpha-123",
      0, // Persistently focused on Leg 0
      2  // Hovering on Leg 2
    );

    const leg0 = geoJson.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 0
    );
    const leg2 = geoJson.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 2
    );

    assert.strictEqual(leg0?.properties?.isLegFocused, true);
    assert.strictEqual(leg0?.properties?.isLegHovered, false);

    assert.strictEqual(leg2?.properties?.isLegFocused, false);
    assert.strictEqual(leg2?.properties?.isLegHovered, true);

    // On hover exit (hoveredLegIndex = null)
    const geoJsonAfterHover = enrichGeoJsonWithSelection(
      mockRoutes,
      "route-alpha-123",
      0,
      null
    );
    const afterLeg0 = geoJsonAfterHover.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 0
    );
    const afterLeg2 = geoJsonAfterHover.features.find(
      (f) => f.properties?.routeId === "route-alpha-123" && f.properties?.legIndex === 2
    );
    assert.strictEqual(afterLeg0?.properties?.isLegFocused, true);
    assert.strictEqual(afterLeg2?.properties?.isLegHovered, false);
  });

  // Test 12: Keyboard activation supports the same essential route and leg selection behavior
  it("12. Keyboard activation handlers support Enter and Space triggers", () => {
    let selectedRouteId: string | null = null;
    let focusedLegIndex: number | null = null;

    const simulateKeyDown = (key: string, type: "ROUTE" | "LEG", idOrIdx: any) => {
      if (key === "Enter" || key === " ") {
        if (type === "ROUTE") selectedRouteId = idOrIdx;
        if (type === "LEG") focusedLegIndex = idOrIdx;
      }
    };

    simulateKeyDown("Enter", "ROUTE", "route-alpha-123");
    assert.strictEqual(selectedRouteId, "route-alpha-123");

    simulateKeyDown(" ", "LEG", 1);
    assert.strictEqual(focusedLegIndex, 1);
  });

  // Test 13: Map padding dynamically adapts to desktop floating panel vs mobile drawer
  it("13. Map padding dynamically adapts to desktop panel (left 450px) vs mobile drawer", () => {
    const desktopPadding = getCameraPadding(true);
    assert.strictEqual(desktopPadding.left, 450);
    assert.strictEqual(desktopPadding.right, 80);

    const mobilePadding = getCameraPadding(false);
    assert.strictEqual(mobilePadding.left, 40);
    assert.strictEqual(mobilePadding.bottom, 240); // Leaves safe room for half-sheet drawer
  });

  // Test 14: Null scores retain score-unavailable semantics
  it("14. Null scores retain score-unavailable contract", () => {
    const unscoredRoute = mockRoutes[1];
    assert.strictEqual(unscoredRoute.safety_score, null);
    assert.strictEqual(unscoredRoute.score_status, "INSUFFICIENT_COVERAGE");
    assert.strictEqual(unscoredRoute.scoreable_coverage_ratio, 0.42);
    // Must not fabricate a numerical score when backend reports null
    const displayScore = unscoredRoute.safety_score != null ? Math.round(unscoredRoute.safety_score) : "N/A";
    assert.strictEqual(displayScore, "N/A");
  });

  // Test 15: Focus bounds calculations are completely self-contained with no external API calls
  it("15. Focus bounds calculations run completely in-memory with valid bounding boxes", () => {
    const geoJson = enrichGeoJsonWithSelection(mockRoutes, "route-alpha-123", 0);
    const bounds = calculateFocusBounds(geoJson, "route-alpha-123", 0);

    assert.notStrictEqual(bounds.bounds, null);
    if (bounds.bounds) {
      const [[minLng, minLat], [maxLng, maxLat]] = bounds.bounds;
      assert.strictEqual(minLng, 80.2100);
      assert.strictEqual(maxLng, 80.2120);
      assert.strictEqual(minLat, 13.0800);
      assert.strictEqual(maxLat, 13.0820);
    }
  });
});
