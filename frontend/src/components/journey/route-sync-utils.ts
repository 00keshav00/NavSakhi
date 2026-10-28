import type { MultimodalRoute } from "../../types/journey.ts";

export interface GeoJsonExtractionResult {
  lngs: number[];
  lats: number[];
}

export interface BoundsResult {
  bounds: [[number, number], [number, number]] | null;
  isSinglePoint: boolean;
  center?: [number, number];
}

/**
 * Safely extracts valid finite longitude and latitude pairs from any GeoJSON coordinate array or structure.
 * Validates range: lng [-180, 180], lat [-90, 90].
 */
export function extractValidCoordinates(coords: unknown): GeoJsonExtractionResult {
  const lngs: number[] = [];
  const lats: number[] = [];

  function recurse(val: unknown) {
    if (!Array.isArray(val) || val.length === 0) return;

    if (
      typeof val[0] === "number" &&
      typeof val[1] === "number" &&
      val.length >= 2
    ) {
      const lng = val[0];
      const lat = val[1];
      if (
        Number.isFinite(lng) &&
        Number.isFinite(lat) &&
        lng >= -180 &&
        lng <= 180 &&
        lat >= -90 &&
        lat <= 90
      ) {
        lngs.push(lng);
        lats.push(lat);
      }
    } else {
      for (const item of val) {
        recurse(item);
      }
    }
  }

  recurse(coords);
  return { lngs, lats };
}

/**
 * Constructs a single GeoJSON FeatureCollection containing all route segments,
 * tagged with selection, focus, hover, and styling properties.
 *
 * Requirements satisfied:
 * - Active route features are elevated so they render above inactive alternatives.
 * - Each segment retains its legIndex, routeId, transportMode, and focus state.
 * - Handles empty routes, missing polylines, and malformed segments gracefully.
 */
export function enrichGeoJsonWithSelection(
  routes: MultimodalRoute[],
  activeRouteId: string | null,
  focusedLegIndex: number | null = null,
  hoveredLegIndex: number | null = null
): GeoJSON.FeatureCollection {
  if (!routes || !Array.isArray(routes) || routes.length === 0) {
    return { type: "FeatureCollection", features: [] };
  }

  const activeFeatures: GeoJSON.Feature[] = [];
  const inactiveFeatures: GeoJSON.Feature[] = [];

  routes.forEach((route) => {
    if (!route || !route.id) return;
    const isActive = route.id === activeRouteId;
    const segments = Array.isArray(route.segments) ? route.segments : [];

    segments.forEach((seg, idx) => {
      const isLegFocused = isActive && focusedLegIndex === idx;
      const isLegHovered = isActive && hoveredLegIndex === idx;

      // Extract raw polyline feature or construct a fallback LineString
      let featureGeometry: GeoJSON.Geometry = {
        type: "LineString",
        coordinates: [],
      };

      if (seg?.polyline?.geometry) {
        featureGeometry = seg.polyline.geometry;
      }

      const feature: GeoJSON.Feature = {
        type: "Feature",
        geometry: featureGeometry,
        properties: {
          ...(seg?.polyline?.properties || {}),
          routeId: route.id,
          routeName: route.route_name || "Alternative Route",
          legIndex: idx,
          segmentName: seg?.segment_name || `Leg ${idx + 1}`,
          transportMode: seg?.transport_mode || "walk",
          origin: seg?.origin,
          destination: seg?.destination,
          color: seg?.color || (isActive ? "#8B5CF6" : "#94A3B8"),
          isActive,
          isLegFocused,
          isLegHovered,
        },
      };

      if (isActive) {
        activeFeatures.push(feature);
      } else {
        inactiveFeatures.push(feature);
      }
    });
  });

  // Layer ordering: Inactive routes first (underneath), active route last (on top)
  return {
    type: "FeatureCollection",
    features: [...inactiveFeatures, ...activeFeatures],
  };
}

/**
 * Calculates camera bounds focusing either on a specific route leg,
 * the entire active route, or the complete set of routes and origin/destination markers.
 */
export function calculateFocusBounds(
  geoJson: GeoJSON.FeatureCollection | null,
  activeRouteId: string | null,
  focusedLegIndex: number | null = null,
  sourceCoords?: number[] | null,
  destCoords?: number[] | null
): BoundsResult {
  const allLngs: number[] = [];
  const allLats: number[] = [];

  const features = geoJson?.features || [];

  // 1. If a specific leg is focused on the active route, extract only its geometry
  if (focusedLegIndex !== null && activeRouteId) {
    const legFeatures = features.filter(
      (f) =>
        f.properties?.routeId === activeRouteId &&
        f.properties?.legIndex === focusedLegIndex
    );

    legFeatures.forEach((f) => {
      if (f.geometry && "coordinates" in f.geometry) {
        const { lngs, lats } = extractValidCoordinates(f.geometry.coordinates);
        allLngs.push(...lngs);
        allLats.push(...lats);
      }
    });
  }

  // 2. If no leg geometry was found (e.g. unmapped transit or full route requested),
  // extract from the active route features
  if (allLngs.length === 0 && activeRouteId) {
    const activeFeatures = features.filter(
      (f) => f.properties?.routeId === activeRouteId
    );

    activeFeatures.forEach((f) => {
      if (f.geometry && "coordinates" in f.geometry) {
        const { lngs, lats } = extractValidCoordinates(f.geometry.coordinates);
        allLngs.push(...lngs);
        allLats.push(...lats);
      }
    });
  }

  // 3. Fallback: all features across all routes
  if (allLngs.length === 0) {
    features.forEach((f) => {
      if (f.geometry && "coordinates" in f.geometry) {
        const { lngs, lats } = extractValidCoordinates(f.geometry.coordinates);
        allLngs.push(...lngs);
        allLats.push(...lats);
      }
    });
  }

  // Include origin and destination markers if looking at full route
  if (focusedLegIndex === null) {
    if (sourceCoords && Array.isArray(sourceCoords) && sourceCoords.length >= 2) {
      const { lngs, lats } = extractValidCoordinates(sourceCoords);
      allLngs.push(...lngs);
      allLats.push(...lats);
    }
    if (destCoords && Array.isArray(destCoords) && destCoords.length >= 2) {
      const { lngs, lats } = extractValidCoordinates(destCoords);
      allLngs.push(...lngs);
      allLats.push(...lats);
    }
  }

  if (allLngs.length === 0 || allLats.length === 0) {
    return { bounds: null, isSinglePoint: false };
  }

  const minLng = Math.min(...allLngs);
  const maxLng = Math.max(...allLngs);
  const minLat = Math.min(...allLats);
  const maxLat = Math.max(...allLats);

  if (minLng === maxLng && minLat === maxLat) {
    return {
      bounds: null,
      isSinglePoint: true,
      center: [minLng, minLat],
    };
  }

  return {
    bounds: [
      [minLng, minLat],
      [maxLng, maxLat],
    ],
    isSinglePoint: false,
    center: [(minLng + maxLng) / 2, (minLat + maxLat) / 2],
  };
}

/**
 * Returns safe camera padding respecting the desktop floating panel
 * (occupying left 420px) vs mobile bottom-sheet layouts.
 */
export function getCameraPadding(isDesktop: boolean) {
  if (isDesktop) {
    return { top: 80, bottom: 80, left: 450, right: 80 };
  }
  return { top: 90, bottom: 240, left: 40, right: 40 };
}

/**
 * Generates an intent key to avoid unnecessary repeated MapLibre fitBounds calls.
 */
export function generateCameraIntentKey(
  activeRouteId: string | null,
  focusedLegIndex: number | null,
  featureCount: number,
  sourceCoords?: number[] | null,
  destCoords?: number[] | null,
  isDesktop: boolean = false
): string {
  const sKey = sourceCoords ? sourceCoords.slice(0, 2).join(",") : "none";
  const dKey = destCoords ? destCoords.slice(0, 2).join(",") : "none";
  const layout = isDesktop ? "desktop" : "mobile";
  return `${activeRouteId || "none"}_leg_${focusedLegIndex ?? "all"}_features_${featureCount}_src_${sKey}_dst_${dKey}_${layout}`;
}

/**
 * Identifies weather-provider failure or unavailability alert messages that
 * should be suppressed from the user-facing Journey Planner warning panel.
 *
 * Suppresses:
 * - "Live weather data is currently unavailable from provider."
 * - "Live weather information unavailable"
 * - "Live weather information unavailable (rate limit cooldown)"
 * - "Live weather provider is temporarily unreachable."
 * - Any weather telemetry failure/unavailable warning.
 *
 * Preserves:
 * - Transit availability notices ("No practical direct public transit route...")
 * - Night activity or lighting guidance
 * - Safety notices, road restrictions, or corridor advisories
 * - Any non-weather warning
 */
export function isWeatherUnavailableWarning(warning: string): boolean {
  if (!warning || typeof warning !== "string") return false;
  const lower = warning.toLowerCase().trim();

  // Must explicitly mention weather to be considered for weather-unavailable suppression
  if (!lower.includes("weather")) {
    return false;
  }

  // Must be an unavailability, provider outage, rate limit, or failure advisory
  const isUnavailabilityAlert =
    lower.includes("unavailable") ||
    lower.includes("unreachable") ||
    lower.includes("rate limit") ||
    lower.includes("offline") ||
    lower.includes("timed out") ||
    lower.includes("timeout") ||
    lower.includes("failed to fetch") ||
    lower.includes("provider error");

  return isUnavailabilityAlert;
}

/**
 * Filters a list of journey warnings, suppressing redundant weather-unavailable
 * messages while strictly preserving legitimate routing, transit, and safety warnings.
 */
export function filterJourneyWarnings(warnings?: string[] | null): string[] {
  if (!warnings || !Array.isArray(warnings)) return [];
  return warnings.filter((w) => !isWeatherUnavailableWarning(w));
}
