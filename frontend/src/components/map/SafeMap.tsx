"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Map, { Source, Layer, Marker, NavigationControl, Popup, MapRef } from "react-map-gl/maplibre";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Loader2, Layers, X, ChevronDown, ChevronUp } from "lucide-react";
import { RoutePOI } from "@/types/journey";

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
};

interface SafeMapProps {
  source?: { coordinates?: number[] };
  destination?: { coordinates?: number[] };
  sourceName?: string;
  destinationName?: string;
  routeGeometry?: GeoJSON.FeatureCollection | null;
  hasSearched?: boolean;
  isLoading?: boolean;
  activeRouteId?: string | null;
  focusedLegIndex?: number | null;
  hoveredLegIndex?: number | null;
  isDesktop?: boolean;
  reports?: unknown[];
  liveLocation?: { lat: number; lng: number; accuracy?: number | null } | null;
  nearbyPois?: RoutePOI[];
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
  activeRouteId = null,
  focusedLegIndex = null,
  isDesktop = false,
  liveLocation = null,
  nearbyPois,
  onRouteClick,
}: SafeMapProps) {
  const mapRef = useRef<MapRef | null>(null);
  const [viewState, setViewState] = useState({
    longitude: 80.2090, // Chennai Default
    latitude: 13.0827,
    zoom: 12,
  });
  const lastFitKeyRef = useRef<string>("");
  const [selectedPoi, setSelectedPoi] = useState<RoutePOI | null>(null);
  const [activeCategoryFilters, setActiveCategoryFilters] = useState<Set<string>>(
    () => new Set(["police", "hospital", "clinic", "pharmacy", "fire_station"])
  );
  const [showLegend, setShowLegend] = useState<boolean>(false);

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

  // Category counts and visible POIs
  const poiCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    (nearbyPois || []).forEach((p) => {
      counts[p.category] = (counts[p.category] || 0) + 1;
    });
    return counts;
  }, [nearbyPois]);

  const visiblePois = useMemo(() => {
    if (!nearbyPois) return [];
    return nearbyPois.filter((p) => activeCategoryFilters.has(p.category));
  }, [nearbyPois, activeCategoryFilters]);

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
    hasSearched &&
    (!routeGeometry || !routeGeometry.features || routeGeometry.features.length === 0);

  return (
    <div className="relative w-full h-full bg-slate-950 overflow-hidden">
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

      {/* 2B. POI CATEGORY FILTER TOGGLES */}
      {nearbyPois && nearbyPois.length > 0 && !isLoading && (
        <div className="absolute top-4 right-14 z-20 flex items-center gap-1.5 p-1 rounded-2xl bg-slate-900/90 backdrop-blur-md border border-slate-700 shadow-xl max-w-[calc(100vw-5rem)] overflow-x-auto">
          {Object.entries(POI_CATEGORY_CONFIG).map(([key, cfg]) => {
            const count = poiCounts[key] || 0;
            if (count === 0) return null; // Honest empty state: omit empty categories
            const isActive = activeCategoryFilters.has(key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleCategory(key)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-bold transition-all border shrink-0 ${
                  isActive
                    ? `${cfg.bg} ${cfg.border} text-white shadow-xs`
                    : "bg-slate-800/60 text-slate-400 border-slate-700 hover:bg-slate-800"
                }`}
                title={`Toggle ${cfg.label} markers (${count} found along route)`}
              >
                <span>{cfg.icon}</span>
                <span className="hidden sm:inline">{cfg.label}</span>
                <span className="px-1 py-0.2 rounded-full text-[9px] bg-black/40 font-extrabold">{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* 2C. ACCESSIBLE MAP LEGEND */}
      <div className="absolute top-4 right-4 z-20 flex flex-col items-end">
        {showLegend && (
          <div className="mt-2 p-3 bg-slate-950/95 backdrop-blur-md border border-slate-800 rounded-2xl shadow-2xl text-xs text-slate-200 w-64 space-y-2.5 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
              <span className="font-extrabold uppercase tracking-wider text-[11px] text-white flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" />
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
              </div>
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

        <button
          type="button"
          onClick={() => setShowLegend(!showLegend)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 shadow-xl text-xs font-bold transition-all"
          title="Toggle map symbols and transport legend"
        >
          <Layers className="w-3.5 h-3.5 text-primary" />
          <span>Legend</span>
          {showLegend ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </button>
      </div>

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
        {activeTransitStations.map((st, i) => (
          <Marker key={`transit-st-${i}`} longitude={st.coords[0]} latitude={st.coords[1]} anchor="bottom">
            <div className="flex flex-col items-center group cursor-pointer" title={`${st.type === "board" ? "Boarding Station" : "Alighting Station"}: ${st.name} (${st.mode})`}>
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

        {/* 4C. VERIFIED SAFETY FACILITY POI MARKERS */}
        {visiblePois.map((poi) => {
          const cfg = POI_CATEGORY_CONFIG[poi.category] || {
            label: poi.category,
            icon: "📍",
            pinBg: "bg-slate-700",
            pinBorder: "border-slate-400",
          };
          return (
            <Marker
              key={poi.poi_id}
              longitude={poi.longitude}
              latitude={poi.latitude}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                setSelectedPoi(poi);
              }}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedPoi(poi);
                }}
                className="group cursor-pointer flex flex-col items-center transition-transform hover:scale-125 focus:outline-none focus-visible:scale-125 z-10"
                aria-label={`${poi.name} (${cfg.label}), ${poi.distance_to_route_m} meters from route`}
                title={`${poi.name} (${cfg.label}) — ${poi.distance_to_route_m}m from route`}
              >
                <div
                  className={`w-7 h-7 rounded-xl ${cfg.pinBg} border-2 ${cfg.pinBorder} shadow-lg flex items-center justify-center text-xs text-white ring-2 ring-black/50 transition-shadow`}
                >
                  <span className="text-[13px]">{cfg.icon}</span>
                </div>
                <div className="w-1 h-1 bg-black/60 rounded-b shadow-xs" />
              </button>
            </Marker>
          );
        })}

        {/* 4D. INTERACTIVE POI POPUP */}
        {selectedPoi && (
          <Popup
            longitude={selectedPoi.longitude}
            latitude={selectedPoi.latitude}
            anchor="bottom"
            offset={18}
            onClose={() => setSelectedPoi(null)}
            closeButton={true}
            closeOnClick={false}
            className="safeshe-poi-popup z-40"
          >
            <div className="p-3 max-w-[280px] bg-slate-950 text-slate-100 rounded-xl border border-slate-700 shadow-2xl space-y-2 text-xs">
              <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">
                    {POI_CATEGORY_CONFIG[selectedPoi.category]?.icon || "📍"}
                  </span>
                  <span className="font-extrabold text-slate-100 uppercase tracking-wider text-[10px]">
                    {selectedPoi.category_label || selectedPoi.category}
                  </span>
                </div>
                {selectedPoi.is_emergency && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                    EMERGENCY
                  </span>
                )}
              </div>
              <div>
                <h4 className="font-bold text-white text-sm leading-tight">
                  {selectedPoi.name}
                </h4>
                {selectedPoi.operator && (
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Operator: {selectedPoi.operator}
                  </p>
                )}
              </div>
              <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-slate-400 font-medium">Distance to Route:</span>
                  <span className="font-bold text-cyan-400">
                    {selectedPoi.distance_to_route_m} m
                  </span>
                </div>
                <div className="flex justify-between items-center text-[10px]">
                  <span className="text-slate-400">Proximity:</span>
                  <span className="font-semibold text-slate-300">
                    {selectedPoi.proximity_tier === "IMMEDIATELY_BESIDE"
                      ? "Immediately beside route (≤ 100m)"
                      : "Along 800m route corridor"}
                  </span>
                </div>
                {selectedPoi.nearest_route_leg_id && (
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-slate-400">Nearest Leg:</span>
                    <span className="font-mono text-slate-300">
                      {selectedPoi.nearest_route_leg_id}
                    </span>
                  </div>
                )}
              </div>
              <div className="text-[9px] text-slate-400 space-y-0.5 border-t border-slate-800 pt-1.5">
                <div className="flex justify-between">
                  <span>Source:</span>
                  <span className="font-semibold text-slate-300">{selectedPoi.source}</span>
                </div>
                <p className="italic text-slate-500 text-[8.5px] leading-tight mt-1">
                  Verified location from OpenStreetMap. NavSakhi does not monitor real-time staffing or live emergency queue times.
                </p>
              </div>
            </div>
          </Popup>
        )}

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
    </div>
  );
}
