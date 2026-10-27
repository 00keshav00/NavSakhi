"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Map, { Source, Layer, Marker, NavigationControl, Popup, MapRef } from "react-map-gl/maplibre";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Loader2, Layers, X, ChevronDown, ChevronUp, Info, Check, Eye, EyeOff, Sparkles, Building2, Store, ShieldAlert, Train } from "lucide-react";
import { RoutePOI, ActivityZone } from "@/types/journey";

export const EMERGENCY_CATEGORIES = new Set(["police", "hospital", "clinic", "pharmacy", "fire_station", "fuel"]);
export const LANDMARK_CATEGORIES = new Set(["mall", "university", "college", "entertainment", "landmark", "transit_hub"]);
export const COMMERCIAL_CATEGORIES = new Set([
  "convenience", "supermarket", "retail_shop", "food_retail", "restaurant", "cafe", "fast_food", "hotel", "bank_atm", "salon"
]);

if (typeof window !== "undefined") {
  maplibregl.setWorkerUrl("/maplibre-worker.js");
}

// Refined map style using standard OpenStreetMap tiles with full color spectrum (natural water, parks, and road hierarchies without grayscale filter)
const DARK_MAP_STYLE = {
  version: 8 as const,
  sources: {
    "osm-tiles": {
      type: "raster",
      tiles: [
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
    },
  },
  layers: [
    {
      id: "osm-layer",
      type: "raster",
      source: "osm-tiles",
      minzoom: 0,
      maxzoom: 19,
      paint: {
        "raster-saturation": 0.0,
        "raster-contrast": 0.1,
        "raster-brightness-min": 0.05,
        "raster-brightness-max": 0.95,
        "raster-opacity": 0.95,
      },
    },
  ],
};

import {
  calculateFocusBounds,
  generateCameraIntentKey,
  getCameraPadding,
} from "@/components/journey/route-sync-utils";

export const POI_CATEGORY_CONFIG: Record<string, { label: string; icon: string; bg: string; border: string; text: string; pinBg: string; pinBorder: string }> = {
  police: {
    label: "Police",
    icon: "🛡️",
    bg: "bg-blue-600/90 hover:bg-blue-600",
    border: "border-blue-400",
    text: "text-white",
    pinBg: "bg-blue-600",
    pinBorder: "border-blue-300",
  },
  hospital: {
    label: "Hospital",
    icon: "🏥",
    bg: "bg-rose-600/90 hover:bg-rose-600",
    border: "border-rose-400",
    text: "text-white",
    pinBg: "bg-rose-600",
    pinBorder: "border-rose-300",
  },
  clinic: {
    label: "Clinic",
    icon: "🩺",
    bg: "bg-orange-600/90 hover:bg-orange-600",
    border: "border-orange-400",
    text: "text-white",
    pinBg: "bg-orange-600",
    pinBorder: "border-orange-300",
  },
  pharmacy: {
    label: "Pharmacy",
    icon: "💊",
    bg: "bg-emerald-600/90 hover:bg-emerald-600",
    border: "border-emerald-400",
    text: "text-white",
    pinBg: "bg-emerald-600",
    pinBorder: "border-emerald-300",
  },
  fire_station: {
    label: "Fire Station",
    icon: "🚒",
    bg: "bg-amber-600/90 hover:bg-amber-600",
    border: "border-amber-400",
    text: "text-white",
    pinBg: "bg-amber-600",
    pinBorder: "border-amber-300",
  },
  fuel: {
    label: "Fuel / Service",
    icon: "⛽",
    bg: "bg-cyan-600/90 hover:bg-cyan-600",
    border: "border-cyan-400",
    text: "text-white",
    pinBg: "bg-cyan-600",
    pinBorder: "border-cyan-300",
  },
  convenience: {
    label: "General Store",
    icon: "🏪",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  supermarket: {
    label: "Supermarket",
    icon: "🛒",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  retail_shop: {
    label: "Retail Shop",
    icon: "🛍️",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  food_retail: {
    label: "Food Retail",
    icon: "🥖",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  restaurant: {
    label: "Restaurant",
    icon: "🍽️",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  cafe: {
    label: "Café",
    icon: "☕",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  fast_food: {
    label: "Fast Food",
    icon: "🍔",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  hotel: {
    label: "Hotel",
    icon: "🏨",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  salon: {
    label: "Salon & Care",
    icon: "💇",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  mall: {
    label: "Shopping Mall",
    icon: "🏬",
    bg: "bg-fuchsia-700/90 hover:bg-fuchsia-700",
    border: "border-fuchsia-500",
    text: "text-white",
    pinBg: "bg-fuchsia-700",
    pinBorder: "border-fuchsia-400",
  },
  university: {
    label: "College / Campus",
    icon: "🎓",
    bg: "bg-blue-800/90 hover:bg-blue-800",
    border: "border-blue-600",
    text: "text-white",
    pinBg: "bg-blue-800",
    pinBorder: "border-blue-500",
  },
  bank_atm: {
    label: "Bank / ATM",
    icon: "🏧",
    bg: "bg-amber-400/90 text-slate-950 hover:bg-amber-300",
    border: "border-amber-500",
    text: "text-slate-950 font-bold",
    pinBg: "bg-amber-400 text-slate-950",
    pinBorder: "border-amber-600",
  },
  entertainment: {
    label: "Entertainment",
    icon: "🎭",
    bg: "bg-pink-700/90 hover:bg-pink-700",
    border: "border-pink-500",
    text: "text-white",
    pinBg: "bg-pink-700",
    pinBorder: "border-pink-400",
  },
  surveillance: {
    label: "Surveillance Camera",
    icon: "📹",
    bg: "bg-slate-700/90 hover:bg-slate-600",
    border: "border-slate-500",
    text: "text-white",
    pinBg: "bg-slate-700",
    pinBorder: "border-slate-400",
  },
};

interface SafeMapProps {
  source?: { coordinates?: number[] };
  destination?: { coordinates?: number[] };
  sourceName?: string;
  destinationName?: string;
  routeGeometry?: GeoJSON.FeatureCollection | null;
  hasSearched?: boolean;
  isLoading?: boolean;
  hasError?: boolean;
  activeRouteId?: string | null;
  focusedLegIndex?: number | null;
  hoveredLegIndex?: number | null;
  isDesktop?: boolean;
  reports?: unknown[];
  liveLocation?: { lat: number; lng: number; accuracy?: number | null } | null;
  nearbyPois?: RoutePOI[];
  activityZones?: ActivityZone[];
  selectedPoi?: RoutePOI | null;
  selectedZone?: ActivityZone | null;
  onPoiSelect?: (poi: RoutePOI | null) => void;
  onZoneSelect?: (zone: ActivityZone | null) => void;
  onLocationDetected?: (lat: number, lng: number) => void;
  onRouteClick?: (properties: Record<string, unknown>) => void;
}

export default function SafeMap({
  source,
  destination,
  sourceName = "Origin",
  destinationName = "Destination",
  routeGeometry, // Expects a FeatureCollection
  hasSearched = false,
  isLoading = false,
  hasError = false,
  activeRouteId = null,
  focusedLegIndex = null,
  isDesktop = false,
  liveLocation = null,
  nearbyPois,
  activityZones,
  selectedPoi: propSelectedPoi,
  selectedZone: propSelectedZone,
  onPoiSelect,
  onZoneSelect,
  onRouteClick,
}: SafeMapProps) {
  const mapRef = useRef<MapRef | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [viewState, setViewState] = useState({
    longitude: 80.2090, // Chennai Default
    latitude: 13.0827,
    zoom: 12,
  });
  const lastFitKeyRef = useRef<string>("");
  const [internalSelectedPoi, setInternalSelectedPoi] = useState<RoutePOI | null>(null);
  const selectedPoi = propSelectedPoi !== undefined ? propSelectedPoi : internalSelectedPoi;
  const [internalSelectedZone, setInternalSelectedZone] = useState<ActivityZone | null>(null);
  const selectedZone = propSelectedZone !== undefined ? propSelectedZone : internalSelectedZone;
  const [activeCategoryFilters, setActiveCategoryFilters] = useState<Set<string>>(
    () => new Set([
      "police", "hospital", "clinic", "pharmacy", "fire_station", "fuel",
      "convenience", "supermarket", "retail_shop", "food_retail", "restaurant", "cafe", "fast_food", "hotel",
      "mall", "university", "bank_atm", "entertainment"
    ])
  );
  const [showLayers, setShowLayers] = useState<boolean>(false);
  const [showLegend, setShowLegend] = useState<boolean>(false);
  const [layerVisibility, setLayerVisibility] = useState({
    emergency: true,
    transit: true,
    commercial: true,
    landmarks: true,
    activity: true,
  });

  // Automatically trigger map resize when container element resizes (e.g. desktop panel toggle)
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      mapRef.current?.resize();
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Keyboard accessibility: Close overlays and detail panels on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowLayers(false);
        setShowLegend(false);
        setInternalSelectedPoi(null);
        setInternalSelectedZone(null);
        onPoiSelect?.(null);
        onZoneSelect?.(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onPoiSelect, onZoneSelect]);

  const handlePoiSelect = (poi: RoutePOI) => {
    setInternalSelectedPoi(poi);
    setInternalSelectedZone(null);
    onPoiSelect?.(poi);
    onZoneSelect?.(null);
    setShowLayers(false);
    setShowLegend(false);
    mapRef.current?.easeTo({
      center: [poi.longitude, poi.latitude],
      offset: [0, -60],
      duration: 350,
    });
  };

  const handleZoneSelect = (zone: ActivityZone) => {
    setInternalSelectedZone(zone);
    setInternalSelectedPoi(null);
    onZoneSelect?.(zone);
    onPoiSelect?.(null);
    setShowLayers(false);
    setShowLegend(false);
    mapRef.current?.easeTo({
      center: [zone.longitude, zone.latitude],
      offset: [0, -60],
      duration: 350,
    });
  };

  // Derive guaranteed endpoint coordinates: prefer explicit props, fallback to active route endpoints
  const resolvedSourceCoords = useMemo<[number, number] | null>(() => {
    const s = source?.coordinates;
    if (Array.isArray(s) && s.length >= 2 && Number.isFinite(s[0]) && Number.isFinite(s[1])) {
      return [s[0], s[1]];
    }
    // Fallback: first coordinate of the active route's features
    if (routeGeometry?.features && routeGeometry.features.length > 0) {
      const activeFeature =
        routeGeometry.features.find((f) => f.properties?.isActive === true) ||
        routeGeometry.features[0];
      const geom = activeFeature?.geometry;
      if (geom?.type === "LineString" && Array.isArray(geom.coordinates) && geom.coordinates.length > 0) {
        const first = geom.coordinates[0];
        if (Array.isArray(first) && first.length >= 2) {
          return [first[0], first[1]];
        }
      }
    }
    return null;
  }, [source, routeGeometry]);

  const resolvedDestCoords = useMemo<[number, number] | null>(() => {
    const d = destination?.coordinates;
    if (Array.isArray(d) && d.length >= 2 && Number.isFinite(d[0]) && Number.isFinite(d[1])) {
      return [d[0], d[1]];
    }
    // Fallback: last coordinate of the active route's features
    if (routeGeometry?.features && routeGeometry.features.length > 0) {
      const activeFeature =
        routeGeometry.features.find((f) => f.properties?.isActive === true) ||
        routeGeometry.features[routeGeometry.features.length - 1];
      const geom = activeFeature?.geometry;
      if (geom?.type === "LineString" && Array.isArray(geom.coordinates) && geom.coordinates.length > 0) {
        const last = geom.coordinates[geom.coordinates.length - 1];
        if (Array.isArray(last) && last.length >= 2) {
          return [last[0], last[1]];
        }
      }
    }
    return null;
  }, [destination, routeGeometry]);

  // Derive intermediate transit station transfer markers for active route
  const activeTransitStations = useMemo(() => {
    if (!routeGeometry?.features) return [];
    const stations: { name: string; type: "board" | "alight"; coords: [number, number]; mode: string }[] = [];
    
    routeGeometry.features.forEach((f) => {
      if (f.properties?.isActive) {
        const mode = (f.properties?.transportMode || "").toLowerCase();
        const isTransit = mode.includes("metro") || mode.includes("suburban") || mode.includes("train") || mode.includes("mrts");
        if (isTransit && f.geometry?.type === "LineString" && Array.isArray(f.geometry.coordinates) && f.geometry.coordinates.length >= 2) {
          const coords = f.geometry.coordinates;
          const first = coords[0];
          const last = coords[coords.length - 1];
          if (f.properties?.origin && Array.isArray(first) && first.length >= 2) {
            stations.push({
              name: f.properties.origin,
              type: "board",
              coords: [first[0], first[1]],
              mode: f.properties.transportMode,
            });
          }
          if (f.properties?.destination && Array.isArray(last) && last.length >= 2) {
            stations.push({
              name: f.properties.destination,
              type: "alight",
              coords: [last[0], last[1]],
              mode: f.properties.transportMode,
            });
          }
        }
      }
    });
    return stations;
  }, [routeGeometry]);

  // Fit bounds dynamically with intent tracking and panel-safe padding
  useEffect(() => {
    if (!mapRef.current) return;

    const featureCount = routeGeometry?.features?.length || 0;
    const currentIntentKey = generateCameraIntentKey(
      activeRouteId,
      focusedLegIndex,
      featureCount,
      resolvedSourceCoords || undefined,
      resolvedDestCoords || undefined,
      isDesktop
    );

    // Prevent repeated fitBounds during ordinary renders or manual map panning
    if (currentIntentKey === lastFitKeyRef.current) return;
    lastFitKeyRef.current = currentIntentKey;

    const boundsResult = calculateFocusBounds(
      routeGeometry || null,
      activeRouteId,
      focusedLegIndex,
      resolvedSourceCoords || undefined,
      resolvedDestCoords || undefined
    );

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duration = prefersReducedMotion ? 0 : 800;
    const padding = getCameraPadding(isDesktop);

    try {
      if (boundsResult.isSinglePoint && boundsResult.center) {
        mapRef.current.easeTo({
          center: boundsResult.center,
          zoom: 14,
          duration,
        });
      } else if (boundsResult.bounds) {
        mapRef.current.fitBounds(boundsResult.bounds, {
          padding,
          duration,
          maxZoom: 16,
        });
      }
    } catch (err) {
      console.warn("Map camera fitBounds prevented an invalid bounds operation:", err);
    }
  }, [
    routeGeometry,
    resolvedSourceCoords,
    resolvedDestCoords,
    activeRouteId,
    focusedLegIndex,
    isDesktop,
  ]);

  // Category counts and layer counts
  const poiCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    (nearbyPois || []).forEach((p) => {
      counts[p.category] = (counts[p.category] || 0) + 1;
    });
    return counts;
  }, [nearbyPois]);

  const layerCounts = useMemo(() => {
    const pois = nearbyPois || [];
    return {
      emergency: pois.filter((p) => p.is_emergency || EMERGENCY_CATEGORIES.has(p.category)).length,
      transit: activeTransitStations.length,
      commercial: pois.filter((p) => !p.is_emergency && !LANDMARK_CATEGORIES.has(p.category) && COMMERCIAL_CATEGORIES.has(p.category)).length,
      landmarks: pois.filter((p) => LANDMARK_CATEGORIES.has(p.category)).length,
      activity: (activityZones || []).length,
    };
  }, [nearbyPois, activeTransitStations, activityZones]);

  const visiblePois = useMemo(() => {
    if (!nearbyPois) return [];
    const filtered = nearbyPois.filter((p) => {
      const isEmerg = p.is_emergency || EMERGENCY_CATEGORIES.has(p.category);
      const isLand = LANDMARK_CATEGORIES.has(p.category);
      const isComm = !isEmerg && !isLand;

      if (isEmerg && !layerVisibility.emergency) return false;
      if (isLand && !layerVisibility.landmarks) return false;
      if (isComm && !layerVisibility.commercial) return false;

      return activeCategoryFilters.has(p.category);
    });

    // Priority B1 & B3: Commercial renders first, Landmarks second, Emergency & Medical LAST (so they paint on top)
    return filtered.sort((a, b) => {
      const aEmerg = a.is_emergency || EMERGENCY_CATEGORIES.has(a.category);
      const bEmerg = b.is_emergency || EMERGENCY_CATEGORIES.has(b.category);
      if (aEmerg && !bEmerg) return 1;
      if (!aEmerg && bEmerg) return -1;
      const aLand = LANDMARK_CATEGORIES.has(a.category);
      const bLand = LANDMARK_CATEGORIES.has(b.category);
      if (aLand && !bLand) return 1;
      if (!aLand && bLand) return -1;
      return 0;
    });
  }, [nearbyPois, layerVisibility, activeCategoryFilters]);

  const { shopClusters, nonClusteredPois } = useMemo(() => {
    if (!visiblePois || visiblePois.length === 0) {
      return { shopClusters: [] as { id: string; latitude: number; longitude: number; pois: RoutePOI[] }[], nonClusteredPois: [] as RoutePOI[] };
    }

    const emergenciesAndLandmarks: RoutePOI[] = [];
    const commercialPois: RoutePOI[] = [];

    for (const p of visiblePois) {
      if (p.is_emergency || EMERGENCY_CATEGORIES.has(p.category) || LANDMARK_CATEGORIES.has(p.category)) {
        emergenciesAndLandmarks.push(p);
      } else {
        commercialPois.push(p);
      }
    }

    // When zoomed in close (zoom >= 14.5) or very few shops, show each shop individually
    if (viewState.zoom >= 14.5 || commercialPois.length <= 3) {
      return {
        shopClusters: [],
        nonClusteredPois: [...commercialPois, ...emergenciesAndLandmarks],
      };
    }

    // Grid-based clustering with threshold ~300m - 800m depending on zoom level
    const threshold = viewState.zoom < 12 ? 0.012 : viewState.zoom < 13.5 ? 0.007 : 0.0035;
    const groups: Record<string, RoutePOI[]> = {};

    for (const p of commercialPois) {
      const lat = p.latitude ?? (p as any).lat;
      const lon = p.longitude ?? (p as any).lon;
      if (typeof lat !== "number" || typeof lon !== "number") continue;
      const key = `${Math.round(lat / threshold)}_${Math.round(lon / threshold)}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(p);
    }

    const clustersList: { id: string; latitude: number; longitude: number; pois: RoutePOI[] }[] = [];
    const singlesList: RoutePOI[] = [...emergenciesAndLandmarks];

    for (const [key, groupPois] of Object.entries(groups)) {
      if (groupPois.length >= 3) {
        const avgLat = groupPois.reduce((sum, p) => sum + (p.latitude ?? (p as any).lat), 0) / groupPois.length;
        const avgLon = groupPois.reduce((sum, p) => sum + (p.longitude ?? (p as any).lon), 0) / groupPois.length;
        clustersList.push({
          id: `cluster-${key}`,
          latitude: avgLat,
          longitude: avgLon,
          pois: groupPois,
        });
      } else {
        singlesList.push(...groupPois);
      }
    }

    return { shopClusters: clustersList, nonClusteredPois: singlesList };
  }, [visiblePois, viewState.zoom]);

  const toggleCategory = (cat: string) => {
    setActiveCategoryFilters((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  const hasEmptyGeometry =
    !isLoading &&
    !hasError &&
    hasSearched &&
    (!routeGeometry || !routeGeometry.features || routeGeometry.features.length === 0);

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden" ref={containerRef}>
      {/* 1. Subtle In-flight Routing Progress Banner */}
      {isLoading && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 pointer-events-none">
          <div className="flex items-center gap-2.5 px-4 py-2 rounded-full bg-card/90 backdrop-blur-md border border-primary/30 shadow-xl text-xs font-semibold text-foreground">
            <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
            <span>Calculating environmental safety routes...</span>
          </div>
        </div>
      )}

      {/* 2. Genuine Empty / No Route Result Notice (Suppressed during Loading) */}
      {hasEmptyGeometry && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-background/50 backdrop-blur-xs pointer-events-none">
          <div className="bg-card/95 backdrop-blur-md px-6 py-4 rounded-2xl shadow-2xl border border-border flex items-center gap-3.5 pointer-events-auto max-w-md mx-4">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-500 shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
            </div>
            <div>
              <h3 className="font-bold text-foreground text-sm">No route geometry available</h3>
              <p className="text-xs text-muted-foreground mt-0.5">The routing engine could not find supported routes between these points.</p>
            </div>
          </div>
        </div>
      )}

      {/* 2C. CONSOLIDATED MAP CONTROLS (LAYERS & LEGEND) */}
      <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2">
        <div className="flex items-center gap-2">
          {/* Map Layers Toggle */}
          <button
            type="button"
            onClick={() => {
              setShowLayers(!showLayers);
              if (!showLayers) setShowLegend(false);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border shadow-xl text-xs font-bold transition-all backdrop-blur-md ${
              showLayers
                ? "bg-primary text-primary-foreground border-primary shadow-primary/20"
                : "bg-slate-900/90 hover:bg-slate-800 text-slate-200 border-slate-700"
            }`}
            title="Toggle Map Layers & POI Categories"
            aria-label="Map Layers"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Layers</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-black/40 font-extrabold">
              {Object.values(layerVisibility).filter(Boolean).length}/5
            </span>
            {showLayers ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>

          {/* Legend Toggle */}
          <button
            type="button"
            onClick={() => {
              setShowLegend(!showLegend);
              if (!showLegend) setShowLayers(false);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border shadow-xl text-xs font-bold transition-all backdrop-blur-md ${
              showLegend
                ? "bg-primary text-primary-foreground border-primary shadow-primary/20"
                : "bg-slate-900/90 hover:bg-slate-800 text-slate-200 border-slate-700"
            }`}
            title="Toggle map symbols and transport legend"
            aria-label="Map Legend"
          >
            <Info className="w-3.5 h-3.5" />
            <span>Legend</span>
            {showLegend ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {/* Map Layers Popover */}
        {showLayers && (
          <div className="p-3 bg-slate-950/95 backdrop-blur-md border border-slate-800 rounded-2xl shadow-2xl text-xs text-slate-200 w-80 max-h-[calc(100vh-8rem)] overflow-y-auto space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-extrabold uppercase tracking-wider text-[11px] text-white flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" />
                <span>Map Layers</span>
              </span>
              <div className="flex items-center gap-1.5 text-[10px]">
                <button
                  type="button"
                  onClick={() =>
                    setLayerVisibility({
                      emergency: true,
                      transit: true,
                      commercial: true,
                      landmarks: true,
                      activity: true,
                    })
                  }
                  className="text-cyan-400 hover:underline font-bold"
                >
                  Show All
                </button>
                <span className="text-slate-600">|</span>
                <button
                  type="button"
                  onClick={() =>
                    setLayerVisibility({
                      emergency: false,
                      transit: false,
                      commercial: false,
                      landmarks: false,
                      activity: false,
                    })
                  }
                  className="text-slate-400 hover:underline font-bold"
                >
                  Hide All
                </button>
                <button
                  type="button"
                  onClick={() => setShowLayers(false)}
                  className="text-slate-400 hover:text-white ml-1"
                  title="Close layers (Esc)"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Core Layer Groups */}
            <div className="space-y-1.5">
              {/* Emergency Services */}
              <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-900/60 cursor-pointer transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🛡️</span>
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200 text-[11px]">Emergency Services</span>
                    <span className="text-[9.5px] text-slate-400">Police, hospitals, clinics, fire</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono font-bold">
                    {layerCounts.emergency}
                  </span>
                  <input
                    type="checkbox"
                    checked={layerVisibility.emergency}
                    onChange={(e) =>
                      setLayerVisibility((prev) => ({ ...prev, emergency: e.target.checked }))
                    }
                    className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                </div>
              </label>

              {/* Transit Hubs */}
              <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-900/60 cursor-pointer transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🚆</span>
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200 text-[11px]">Transit Hubs</span>
                    <span className="text-[9.5px] text-slate-400">Metro, suburban rail & bus transfers</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono font-bold">
                    {layerCounts.transit}
                  </span>
                  <input
                    type="checkbox"
                    checked={layerVisibility.transit}
                    onChange={(e) =>
                      setLayerVisibility((prev) => ({ ...prev, transit: e.target.checked }))
                    }
                    className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                </div>
              </label>

              {/* Commercial Establishments */}
              <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-900/60 cursor-pointer transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🏪</span>
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200 text-[11px]">Commercial Shops</span>
                    <span className="text-[9.5px] text-slate-400">Retail, groceries, cafes, ATMs</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono font-bold">
                    {layerCounts.commercial}
                  </span>
                  <input
                    type="checkbox"
                    checked={layerVisibility.commercial}
                    onChange={(e) =>
                      setLayerVisibility((prev) => ({ ...prev, commercial: e.target.checked }))
                    }
                    className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                </div>
              </label>

              {/* Major Landmarks */}
              <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-900/60 cursor-pointer transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🏬</span>
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200 text-[11px]">Major Landmarks</span>
                    <span className="text-[9.5px] text-slate-400">Shopping malls, colleges, campuses</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono font-bold">
                    {layerCounts.landmarks}
                  </span>
                  <input
                    type="checkbox"
                    checked={layerVisibility.landmarks}
                    onChange={(e) =>
                      setLayerVisibility((prev) => ({ ...prev, landmarks: e.target.checked }))
                    }
                    className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                </div>
              </label>

              {/* Mapped Activity Zones */}
              <label className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-900/60 cursor-pointer transition-colors">
                <div className="flex items-center gap-2">
                  <span className="text-sm">✨</span>
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200 text-[11px]">Activity Zones</span>
                    <span className="text-[9.5px] text-slate-400">Commercial spatial clusters (ODbL)</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono font-bold">
                    {layerCounts.activity}
                  </span>
                  <input
                    type="checkbox"
                    checked={layerVisibility.activity}
                    onChange={(e) =>
                      setLayerVisibility((prev) => ({ ...prev, activity: e.target.checked }))
                    }
                    className="w-4 h-4 rounded text-primary accent-primary cursor-pointer"
                  />
                </div>
              </label>
            </div>

            {/* Specific Category Filters */}
            {nearbyPois && nearbyPois.length > 0 && (
              <div className="border-t border-slate-800 pt-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[10px] text-slate-400 uppercase tracking-wider">
                    Filter Categories ({activeCategoryFilters.size} active)
                  </span>
                  <div className="flex gap-1.5 text-[9.5px]">
                    <button
                      type="button"
                      onClick={() =>
                        setActiveCategoryFilters(
                          new Set(Object.keys(POI_CATEGORY_CONFIG))
                        )
                      }
                      className="text-cyan-400 hover:underline"
                    >
                      All
                    </button>
                    <span className="text-slate-600">|</span>
                    <button
                      type="button"
                      onClick={() => setActiveCategoryFilters(new Set())}
                      className="text-slate-400 hover:underline"
                    >
                      Clear
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 max-h-36 overflow-y-auto pr-1">
                  {Object.entries(POI_CATEGORY_CONFIG).map(([key, cfg]) => {
                    const count = poiCounts[key] || 0;
                    if (count === 0) return null;
                    const isActive = activeCategoryFilters.has(key);
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => toggleCategory(key)}
                        className={`flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium border transition-colors ${
                          isActive
                            ? `${cfg.bg} ${cfg.border} text-white shadow-xs`
                            : "bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800"
                        }`}
                        title={`${cfg.label}: ${count} along route`}
                      >
                        <span>{cfg.icon}</span>
                        <span>{cfg.label}</span>
                        <span className="px-1 py-0.2 rounded-full text-[8.5px] bg-black/40 font-mono font-bold">
                          {count}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Legend Popover */}
        {showLegend && (
          <div className="mt-2 p-3 bg-slate-950/95 backdrop-blur-md border border-slate-800 rounded-2xl shadow-2xl text-xs text-slate-200 w-64 space-y-2.5 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
              <span className="font-extrabold uppercase tracking-wider text-[11px] text-white flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-primary" />
                <span>Map Legend</span>
              </span>
              <button
                type="button"
                onClick={() => setShowLegend(false)}
                className="text-slate-400 hover:text-white"
                title="Close legend"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            
            {/* Pins */}
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Journey Pins</p>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-4 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center font-black text-[9px]">S</span>
                  <span>Origin (Start)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-4 rounded-full bg-rose-600 text-white flex items-center justify-center font-black text-[9px]">D</span>
                  <span>Destination</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-4 rounded-full bg-indigo-600 text-white flex items-center justify-center text-[10px]">🚆</span>
                  <span>Transit Station</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-4 h-4 rounded-full bg-cyan-500 ring-2 ring-cyan-500/40 text-slate-950 flex items-center justify-center text-[9px]">📍</span>
                  <span>Live Location</span>
                </div>
              </div>
            </div>

            {/* Facilities */}
            <div className="space-y-1 border-t border-slate-800 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Verified Facilities</p>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span>🛡️</span>
                  <span>Police Station</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🏥</span>
                  <span>Hospital</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🩺</span>
                  <span>Clinic</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>💊</span>
                  <span>Pharmacy</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🚒</span>
                  <span>Fire & Rescue</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>⛽</span>
                  <span>Fuel / Service</span>
                </div>
              </div>
            </div>

            {/* Landmarks */}
            <div className="space-y-1 border-t border-slate-800 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Major Landmarks</p>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span>🏬</span>
                  <span>Shopping Mall</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🎓</span>
                  <span>College Campus</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🏧</span>
                  <span>Bank / ATM</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span>🎭</span>
                  <span>Entertainment</span>
                </div>
              </div>
            </div>

            {/* Mapped Commercial Shops & Clusters */}
            <div className="space-y-1 border-t border-slate-800 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Commercial Establishments</p>
              <div className="grid grid-cols-1 gap-1 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-amber-600 ring-1.5 ring-amber-400/40 shrink-0" />
                  <span>Mapped Shop (Retail, Cafe, Dining)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 font-black text-[9px] shrink-0 border border-amber-600">8</span>
                  <span>Shop Cluster (Click to zoom into group)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-emerald-500/70 shrink-0" />
                  <span>Open at journey pass-through time</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-rose-500/70 shrink-0" />
                  <span>Closed at journey pass-through time</span>
                </div>
              </div>
              <p className="text-[8.5px] text-slate-400 italic pt-0.5 leading-tight">
                Yellow markers denote ordinary mapped commercial establishments. Mapped presence does not guarantee operating status or safety.
              </p>
            </div>

            {/* Surveillance & Activity Zones */}
            <div className="space-y-1 border-t border-slate-800 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Surveillance &amp; Activity</p>
              <div className="grid grid-cols-1 gap-1 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="text-xs">📹</span>
                  <span>Surveillance Camera (Unverified operation)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 rounded-full bg-amber-400/20 border border-amber-400/60 ring-1 ring-amber-400/30 shrink-0" />
                  <span>Activity Area (Commercial cluster zone)</span>
                </div>
              </div>
              <p className="text-[8.5px] text-slate-400 italic pt-0.5 leading-tight">
                Camera coordinates are mapped physical positions; active monitoring is unverified. Activity zones reflect commercial density, not verified safety.
              </p>
            </div>

            {/* Transport Modes */}
            <div className="space-y-1 border-t border-slate-800 pt-1.5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Transit Modes</p>
              <div className="grid grid-cols-2 gap-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#8B5CF6]" />
                  <span>Metro</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#3B82F6]" />
                  <span>Suburban Rail</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#06B6D4]" />
                  <span>MRTS</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#10B981]" />
                  <span>Govt Bus</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#EAB308]" />
                  <span>Walking</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 rounded-full bg-[#0284C7]" />
                  <span>Cab / Vehicle</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        style={{ display: "none" }}
      />

      <Map
        ref={mapRef}
        mapLib={maplibregl}
        {...viewState}
        onMove={(e) => setViewState(e.viewState)}
        mapStyle={DARK_MAP_STYLE as unknown as maplibregl.StyleSpecification}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={[
          "route-layer-fg-inactive",
          "route-layer-fg-active",
          "route-layer-leg-focused-fg",
        ]}
        onClick={(e) => {
          if (e.features && e.features.length > 0) {
            onRouteClick?.(e.features[0].properties);
          }
        }}
      >
        <NavigationControl position="top-right" />

        {/* 3. DISTINCT ORIGIN / START PIN ('S' / Start) */}
        {resolvedSourceCoords && (
          <Marker longitude={resolvedSourceCoords[0]} latitude={resolvedSourceCoords[1]} anchor="bottom">
            <div className="flex flex-col items-center group cursor-pointer" title={`Origin: ${sourceName}`}>
              <div className="px-2 py-0.5 rounded-full bg-emerald-500 text-slate-950 text-[10px] font-extrabold tracking-wider shadow-lg mb-1 whitespace-nowrap flex items-center gap-1 border border-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-950 animate-pulse" />
                <span>START</span>
              </div>
              <div className="relative flex items-center justify-center">
                <div className="absolute -inset-1.5 rounded-full bg-emerald-500/30 animate-ping opacity-75" />
                <div className="w-7 h-7 bg-emerald-500 rounded-full border-2 border-white shadow-xl flex items-center justify-center text-slate-950 font-black text-xs">
                  S
                </div>
              </div>
              <div className="w-1 h-2 bg-emerald-600 rounded-b shadow-xs" />
            </div>
          </Marker>
        )}

        {/* 4. DISTINCT DESTINATION PIN ('D' / Destination) */}
        {resolvedDestCoords && (
          <Marker longitude={resolvedDestCoords[0]} latitude={resolvedDestCoords[1]} anchor="bottom">
            <div className="flex flex-col items-center group cursor-pointer" title={`Destination: ${destinationName}`}>
              <div className="px-2 py-0.5 rounded-full bg-rose-500 text-white text-[10px] font-extrabold tracking-wider shadow-lg mb-1 whitespace-nowrap flex items-center gap-1 border border-rose-400">
                <span>DESTINATION</span>
              </div>
              <div className="relative flex items-center justify-center">
                <div className="absolute -inset-1.5 rounded-full bg-rose-500/20 opacity-75" />
                <div className="w-7 h-7 bg-rose-600 rounded-full border-2 border-white shadow-xl flex items-center justify-center text-white font-black text-xs">
                  D
                </div>
              </div>
              <div className="w-1 h-2 bg-rose-700 rounded-b shadow-xs" />
            </div>
          </Marker>
        )}

        {/* 4B. TRANSIT STATION TRANSFER MARKERS */}
        {layerVisibility.transit && activeTransitStations.map((st, i) => (
          <Marker
            key={`transit-st-${i}`}
            longitude={st.coords[0]}
            latitude={st.coords[1]}
            anchor="bottom"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              mapRef.current?.easeTo({ center: st.coords, offset: [0, -90], duration: 350 });
            }}
          >
            <div
              className="flex flex-col items-center group cursor-pointer transition-transform hover:scale-110"
              title={`${st.type === "board" ? "Boarding Station" : "Alighting Station"}: ${st.name} (${st.mode})`}
            >
              <div className="px-2 py-0.5 rounded-full bg-indigo-600 text-white text-[9px] font-bold tracking-wider shadow-lg mb-1 whitespace-nowrap border border-indigo-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span>{st.type === "board" ? "BOARD" : "ALIGHT"}: {st.name}</span>
              </div>
              <div className="w-6 h-6 bg-indigo-600 rounded-full border-2 border-white shadow-xl flex items-center justify-center text-white text-[11px] font-bold">
                🚆
              </div>
              <div className="w-1 h-1.5 bg-indigo-700 rounded-b shadow-xs" />
            </div>
          </Marker>
        ))}

        {/* 4C-CLUSTER. COMMERCIAL SHOP CLUSTERS (Zoom < 14.5) */}
        {layerVisibility.commercial && shopClusters.map((cluster) => (
          <Marker
            key={cluster.id}
            longitude={cluster.longitude}
            latitude={cluster.latitude}
            anchor="center"
            style={{ zIndex: 12 }}
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              mapRef.current?.easeTo({
                center: [cluster.longitude, cluster.latitude],
                zoom: Math.min(viewState.zoom + 2, 16),
                duration: 350,
              });
            }}
          >
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                mapRef.current?.easeTo({
                  center: [cluster.longitude, cluster.latitude],
                  zoom: Math.min(viewState.zoom + 2, 16),
                  duration: 350,
                });
              }}
              className="px-1.5 py-0.5 rounded-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-[10px] border border-amber-600 shadow-md ring-2 ring-amber-400/40 cursor-pointer transition-transform hover:scale-110 flex items-center gap-1"
              title={`${cluster.pois.length} commercial establishments clustered nearby. Click to zoom in.`}
              aria-label={`${cluster.pois.length} mapped shops cluster`}
            >
              <Store className="w-2.5 h-2.5 shrink-0" />
              <span>{cluster.pois.length}</span>
            </button>
          </Marker>
        ))}

        {/* 4C. VERIFIED SAFETY FACILITY & UNCLUSTERED SHOP POI MARKERS */}
        {nonClusteredPois.map((poi) => {
          const cfg = POI_CATEGORY_CONFIG[poi.category] || {
            label: poi.category,
            icon: "📍",
            pinBg: "bg-slate-700",
            pinBorder: "border-slate-400",
          };
          const isEmergency = poi.is_emergency || EMERGENCY_CATEGORIES.has(poi.category);
          const isLandmark = LANDMARK_CATEGORIES.has(poi.category);
          const isSelected = selectedPoi?.poi_id === poi.poi_id;

          return (
            <Marker
              key={poi.poi_id}
              longitude={poi.longitude}
              latitude={poi.latitude}
              anchor={isLandmark ? "bottom" : "center"}
              style={{ zIndex: isSelected ? 40 : isEmergency ? 25 : isLandmark ? 15 : 5 }}
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                handlePoiSelect(poi);
              }}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePoiSelect(poi);
                }}
                className={`group cursor-pointer flex flex-col items-center transition-all focus:outline-none focus-visible:scale-125 ${
                  isSelected
                    ? "scale-140 z-30 drop-shadow-[0_0_12px_rgba(34,211,238,0.9)]"
                    : isEmergency
                    ? "hover:scale-120 z-20"
                    : "hover:scale-125 z-10"
                }`}
                aria-label={`${poi.name} (${cfg.label}), ${poi.distance_to_route_m} meters from route`}
                title={`${poi.name} (${cfg.label}) — ${poi.distance_to_route_m}m from route${poi.opening_status ? ` [${poi.opening_status}]` : ""}`}
              >
                {isEmergency ? (
                  /* Prominent Emergency Service Pin (Highest Visual Priority) */
                  <>
                    <div
                      className={`w-7 h-7 rounded-xl ${cfg.pinBg} border-2 ${
                        isSelected ? "border-cyan-400 ring-4 ring-cyan-400/70" : `${cfg.pinBorder} ring-2 ring-black/50`
                      } shadow-lg flex items-center justify-center text-xs text-white transition-all`}
                    >
                      <span className="text-[13px]">{cfg.icon}</span>
                    </div>
                    <div className="w-1 h-1 bg-black/60 rounded-b shadow-xs" />
                  </>
                ) : isLandmark ? (
                  /* Distinct Major Landmark Badge */
                  <div className="flex flex-col items-center group cursor-pointer transition-transform">
                    <div
                      className={`px-2 py-0.5 rounded-lg ${cfg.pinBg} border-2 ${
                        isSelected ? "border-cyan-400 ring-4 ring-cyan-400/70" : cfg.pinBorder
                      } shadow-xl flex items-center gap-1.5 text-white max-w-[150px] truncate`}
                    >
                      <span className="text-xs">{cfg.icon}</span>
                      <span className="text-[10px] font-bold truncate">{poi.name}</span>
                    </div>
                    <div className="w-1.5 h-1.5 rotate-45 bg-fuchsia-700 -mt-1 shadow-sm" />
                  </div>
                ) : (
                  /* Refined, compact yellow/amber circular marker for individual mapped commercial businesses */
                  <div className="relative flex items-center justify-center p-1 min-w-[20px] min-h-[20px] cursor-pointer">
                    <div
                      className={`${
                        viewState.zoom < 13
                          ? "w-1.5 h-1.5"
                          : viewState.zoom < 15
                          ? "w-2 h-2"
                          : "w-2.5 h-2.5"
                      } rounded-full border border-amber-600 bg-amber-400 shadow-sm transition-transform ${
                        isSelected
                          ? "ring-4 ring-cyan-400 scale-140 bg-cyan-400 border-cyan-500"
                          : poi.opening_status === "OPEN"
                          ? "ring-2 ring-emerald-500/70"
                          : poi.opening_status === "CLOSED"
                          ? "ring-2 ring-rose-500/70"
                          : "ring-1.5 ring-amber-400/40"
                      }`}
                    />
                  </div>
                )}
              </button>
            </Marker>
          );
        })}

        {/* 4C2. MAPPED ACTIVITY ZONES (Priority C: Calm translucent boundary overlays without obscuring text pills) */}
        {layerVisibility.activity && (activityZones || []).map((zone) => {
          const isSelected = selectedZone?.zone_id === zone.zone_id;
          return (
            <Marker
              key={zone.zone_id}
              longitude={zone.longitude}
              latitude={zone.latitude}
              anchor="center"
              style={{ zIndex: isSelected ? 30 : 6 }}
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                handleZoneSelect(zone);
              }}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleZoneSelect(zone);
                }}
                className={`group relative flex items-center justify-center cursor-pointer transition-transform focus:outline-none ${
                  isSelected ? "scale-110 z-30 drop-shadow-[0_0_12px_rgba(251,191,36,0.9)]" : "hover:scale-105"
                }`}
                title={`${zone.name} — ${zone.activity_level.toLowerCase()} activity area (${zone.shop_count} mapped shops)`}
                aria-label={zone.name}
              >
                <div
                  className={`rounded-full border transition-all pointer-events-none ${
                    zone.activity_level === "HIGH"
                      ? isSelected
                        ? "w-20 h-20 bg-amber-400/20 border-amber-400/80 ring-4 ring-amber-400/40"
                        : "w-16 h-16 bg-amber-400/10 border-amber-400/40 ring-2 ring-amber-400/20"
                      : isSelected
                      ? "w-16 h-16 bg-blue-400/20 border-blue-400/80 ring-4 ring-blue-400/40"
                      : "w-12 h-12 bg-blue-400/10 border-blue-400/40 ring-2 ring-blue-400/20"
                  }`}
                />
              </button>
            </Marker>
          );
        })}

        {/* 5. LIVE GPS POSITION MARKER */}
        {liveLocation && typeof liveLocation.lat === "number" && typeof liveLocation.lng === "number" && (
          <Marker longitude={liveLocation.lng} latitude={liveLocation.lat} anchor="center">
            <div className="flex flex-col items-center group relative pointer-events-none" aria-label="Current Live Position">
              <div className="absolute -inset-2 rounded-full bg-cyan-400/25 animate-ping opacity-75" />
              <div className="w-5 h-5 rounded-full bg-cyan-500 border-2 border-white shadow-lg flex items-center justify-center ring-4 ring-cyan-500/30">
                <div className="w-2 h-2 rounded-full bg-white shadow-xs" />
              </div>
              <div className="mt-1 px-1.5 py-0.5 rounded bg-cyan-950/90 text-cyan-200 text-[9px] font-bold border border-cyan-500/40 shadow-sm backdrop-blur-xs whitespace-nowrap">
                Live Position
              </div>
            </div>
          </Marker>
        )}

        {/* 6. ROUTE LAYERS (ACTIVE HIGHLIGHTED, INACTIVE SUBDUED) */}
        {routeGeometry && (
          <Source id="route-source" type="geojson" data={routeGeometry}>
            {/* Inactive Alternative Routes (Subdued, lower opacity) */}
            <Layer
              id="route-layer-bg-inactive"
              type="line"
              filter={["!=", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#0f172a", "line-width": 6, "line-opacity": 0.4 }}
            />
            <Layer
              id="route-layer-fg-inactive"
              type="line"
              filter={["!=", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 4, "line-opacity": 0.35 }}
            />

            {/* Active Selected Route (Prominent Glow & Shadow) */}
            <Layer
              id="route-layer-glow-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 16, "line-opacity": 0.25 }}
            />
            {/* Active Selected Route (Dark Casing) */}
            <Layer
              id="route-layer-outline-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#020617", "line-width": 10, "line-opacity": 0.9 }}
            />
            {/* Active Selected Route (Foreground Colored Stroke) */}
            <Layer
              id="route-layer-fg-active"
              type="line"
              filter={["==", ["get", "isActive"], true]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 6, "line-opacity": 1.0 }}
            />

            {/* Hovered Leg Halo */}
            <Layer
              id="route-layer-leg-hover"
              type="line"
              filter={[
                "all",
                ["==", ["get", "isActive"], true],
                ["==", ["get", "isLegHovered"], true],
                ["!=", ["get", "isLegFocused"], true],
              ]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#38bdf8", "line-width": 12, "line-opacity": 0.6 }}
            />

            {/* Focused Leg Glow & Highlighting */}
            <Layer
              id="route-layer-leg-focused-glow"
              type="line"
              filter={[
                "all",
                ["==", ["get", "isActive"], true],
                ["==", ["get", "isLegFocused"], true],
              ]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#38bdf8", "line-width": 18, "line-opacity": 0.4 }}
            />
            <Layer
              id="route-layer-leg-focused-casing"
              type="line"
              filter={[
                "all",
                ["==", ["get", "isActive"], true],
                ["==", ["get", "isLegFocused"], true],
              ]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": "#ffffff", "line-width": 10, "line-opacity": 1.0 }}
            />
            <Layer
              id="route-layer-leg-focused-fg"
              type="line"
              filter={[
                "all",
                ["==", ["get", "isActive"], true],
                ["==", ["get", "isLegFocused"], true],
              ]}
              layout={{ "line-join": "round", "line-cap": "round" }}
              paint={{ "line-color": ["get", "color"], "line-width": 6, "line-opacity": 1.0 }}
            />
          </Source>
        )}
      </Map>

      {/* 4D. RIGHT-DOCKED DEDICATED POI DETAIL PANEL (GOOGLE MAPS STYLE, AVOIDS CLUTTERING ROUTE) */}
      {selectedPoi && (isDesktop || !onPoiSelect) && (
        <div className="fixed sm:absolute bottom-4 sm:bottom-auto sm:top-16 left-4 right-4 sm:left-auto sm:right-4 z-40 sm:w-84 max-w-[calc(100vw-2rem)] bg-slate-950/95 backdrop-blur-md text-slate-100 rounded-2xl border border-slate-700 shadow-2xl p-4 space-y-3 text-xs animate-in fade-in slide-in-from-right-2 duration-200">
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">
                {POI_CATEGORY_CONFIG[selectedPoi.category]?.icon || "📍"}
              </span>
              <span className="font-extrabold text-slate-200 uppercase tracking-wider text-[11px]">
                {selectedPoi.category_label || selectedPoi.category}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              {selectedPoi.is_emergency ? (
                <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  EMERGENCY SERVICE
                </span>
              ) : selectedPoi.opening_status === "OPEN" ? (
                <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  OPEN
                </span>
              ) : selectedPoi.opening_status === "CLOSED" ? (
                <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  CLOSED
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  UNKNOWN HOURS
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  setInternalSelectedPoi(null);
                  onPoiSelect?.(null);
                }}
                className="w-6 h-6 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors ml-1 cursor-pointer"
                aria-label="Close POI details"
                title="Close (Esc)"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-white text-sm leading-snug">
              {selectedPoi.name}
            </h4>
            {selectedPoi.address && (
              <p className="text-[10.5px] text-slate-300 mt-1 flex items-start gap-1">
                <span className="shrink-0 text-slate-400">📍</span>
                <span className="line-clamp-2">{selectedPoi.address}</span>
              </p>
            )}
            {selectedPoi.operator && (
              <p className="text-[10px] text-slate-400 mt-0.5">
                Operator: {selectedPoi.operator}
              </p>
            )}
          </div>

          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400 font-medium">Distance to Route:</span>
              <span className="font-bold text-cyan-400 font-mono">
                {selectedPoi.distance_to_route_m} m
              </span>
            </div>
            <div className="flex justify-between items-center text-[10.5px]">
              <span className="text-slate-400">Pass-Through Time:</span>
              <span className="font-semibold text-slate-200">
                {selectedPoi.estimated_pass_through_time || "En route"}
              </span>
            </div>
            <div className="flex justify-between items-center text-[10.5px]">
              <span className="text-slate-400">Opening Hours:</span>
              <span className="font-mono text-[10px] text-emerald-300 truncate max-w-[170px]" title={selectedPoi.opening_hours || "Hours not published in OpenStreetMap"}>
                {selectedPoi.opening_hours || "Unknown (Not published)"}
              </span>
            </div>
            <div className="flex justify-between items-center text-[10.5px]">
              <span className="text-slate-400">Phone:</span>
              {selectedPoi.phone ? (
                <a href={`tel:${selectedPoi.phone}`} className="font-semibold text-cyan-400 hover:underline">
                  {selectedPoi.phone}
                </a>
              ) : (
                <span className="text-slate-500 italic">Not available</span>
              )}
            </div>
            <div className="flex justify-between items-center text-[10.5px]">
              <span className="text-slate-400">Website:</span>
              {selectedPoi.website ? (
                <a
                  href={selectedPoi.website.startsWith("http") ? selectedPoi.website : `https://${selectedPoi.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:underline truncate max-w-[170px]"
                >
                  {selectedPoi.website.replace(/^https?:\/\//, "")}
                </a>
              ) : (
                <span className="text-slate-500 italic">Not available</span>
              )}
            </div>
            <div className="flex justify-between items-center text-[10px]">
              <span className="text-slate-400">Proximity Tier:</span>
              <span className="font-semibold text-slate-300">
                {selectedPoi.proximity_tier === "IMMEDIATELY_BESIDE"
                  ? "Directly beside route (≤ 100m)"
                  : "Within 800m corridor"}
              </span>
            </div>
          </div>

          <div className="text-[9.5px] text-slate-400 space-y-0.5 border-t border-slate-800 pt-2">
            <div className="flex justify-between">
              <span>Source Attribution:</span>
              <span className="font-semibold text-slate-300">{selectedPoi.source || "OpenStreetMap (ODbL)"}</span>
            </div>
            <div className="flex justify-between">
              <span>Trust Level:</span>
              <span className="font-semibold text-slate-300">
                {selectedPoi.is_verified_safety_facility
                  ? "Independently Verified Safe Haven"
                  : selectedPoi.is_emergency
                  ? "Mapped Public Emergency Facility"
                  : selectedPoi.is_shop
                  ? "Mapped Commercial Context"
                  : "Mapped Geographic Record"}
              </span>
            </div>
            <p className="italic text-slate-500 text-[8.5px] leading-tight mt-0.5">
              Coordinates derived from OpenStreetMap. Geographic mapping identifies facility location, but does not guarantee continuous operations or emergency shelter.
            </p>
          </div>
        </div>
      )}

      {/* 4D2. RIGHT-DOCKED DEDICATED ACTIVITY ZONE PANEL */}
      {selectedZone && (isDesktop || !onZoneSelect) && (
        <div className="fixed sm:absolute bottom-4 sm:bottom-auto sm:top-16 left-4 right-4 sm:left-auto sm:right-4 z-40 sm:w-80 max-w-[calc(100vw-2rem)] bg-slate-950/95 backdrop-blur-md text-slate-100 rounded-2xl border border-amber-500/50 shadow-2xl p-4 space-y-3 text-xs animate-in fade-in slide-in-from-right-2 duration-200">
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex items-center gap-1.5">
              <span className="text-base">✨</span>
              <span className="font-extrabold text-amber-300 uppercase tracking-wider text-[11px]">
                Activity Zone
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                {selectedZone.activity_level} ACTIVITY
              </span>
              <button
                type="button"
                onClick={() => {
                  setInternalSelectedZone(null);
                  onZoneSelect?.(null);
                }}
                className="w-6 h-6 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition-colors ml-1 cursor-pointer"
                aria-label="Close Activity Zone details"
                title="Close (Esc)"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-white text-sm leading-snug">
              {selectedZone.name}
            </h4>
            <p className="text-[11px] text-slate-300 mt-1">
              {selectedZone.shop_count} mapped commercial establishments clustered along corridor
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-400">Cluster Radius:</span>
              <span className="font-semibold text-slate-200 font-mono">~{selectedZone.radius_m} m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Data Source:</span>
              <span className="font-semibold text-slate-200">{selectedZone.source}</span>
            </div>
          </div>

          <div className="text-[9px] text-slate-400 border-t border-slate-800 pt-2 leading-relaxed">
            <p className="italic text-slate-400">
              {selectedZone.disclosure}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
