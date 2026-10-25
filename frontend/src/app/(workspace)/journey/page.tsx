"use client";

import { useState, useMemo, useEffect } from "react";
import { motion } from "framer-motion";
import SafeMap, { POI_CATEGORY_CONFIG } from "@/components/map/SafeMap";
import { useJourney } from "@/hooks/useJourney";
import { MultimodalRoute, RoutePOI, ActivityZone } from "@/types/journey";
import { JourneySearchPanel } from "@/components/journey/JourneySearchPanel";
import { RouteCard } from "@/components/journey/RouteCard";
import { RouteDetailPanel } from "@/components/journey/RouteDetailPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Navigation, Shield, AlertTriangle, ChevronUp, ChevronDown,
  SlidersHorizontal, CheckCircle2, PanelLeftClose, PanelLeftOpen,
  RotateCcw, SearchX, Info, X, MapPin, Phone, ExternalLink, Minimize2, Maximize2
} from "lucide-react";

import { enrichGeoJsonWithSelection, filterJourneyWarnings } from "@/components/journey/route-sync-utils";
import { useLiveJourneyTracking } from "@/hooks/useLiveJourneyTracking";
import { useActiveJourneyStore } from "@/store/activeJourneyStore";

export default function JourneyPage() {
  const { data, isLoading, isError, isEmpty, error, planJourney, resetJourney } = useJourney();
  const liveTracking = useLiveJourneyTracking();

  // Internal Navigation & Synchronized Selection States
  const [activeRouteId, setActiveRouteId] = useState<string | null>(null);
  const [focusedLegIndex, setFocusedLegIndex] = useState<number | null>(null);
  const [hoveredLegIndex, setHoveredLegIndex] = useState<number | null>(null);
  const [viewState, setViewState] = useState<"SEARCH" | "RESULTS" | "DETAIL">("SEARCH");
  const [isDesktopPanelCollapsed, setIsDesktopPanelCollapsed] = useState(false);
  const [mobileSheetSnap, setMobileSheetSnap] = useState<"PEEK" | "HALF" | "EXPANDED">("HALF");
  const [hasSearched, setHasSearched] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [selectedPoi, setSelectedPoi] = useState<RoutePOI | null>(null);
  const [selectedZone, setSelectedZone] = useState<ActivityZone | null>(null);

  // Form Inputs Cache for Pill Display
  const [lastSearchSource, setLastSearchSource] = useState("");
  const [lastSearchDest, setLastSearchDest] = useState("");

  const routes: MultimodalRoute[] = useMemo(
    () => data?.recommended_routes || [],
    [data?.recommended_routes]
  );
  const zeroDistance = data?.zero_distance || false;
  const warnings = useMemo(
    () => filterJourneyWarnings(data?.warnings),
    [data?.warnings]
  );

  const handlePoiSelect = (poi: RoutePOI | null) => {
    setSelectedPoi(poi);
    if (poi) {
      setSelectedZone(null);
      if (!isDesktop) {
        // Auto-collapse bottom sheet to PEEK so map and POI details are unobstructed!
        setMobileSheetSnap("PEEK");
      }
    }
  };

  const handleZoneSelect = (zone: ActivityZone | null) => {
    setSelectedZone(zone);
    if (zone) {
      setSelectedPoi(null);
      if (!isDesktop) {
        setMobileSheetSnap("PEEK");
      }
    }
  };

  // Responsive desktop detection for layout-aware camera bounds padding
  useEffect(() => {
    const updateLayout = () => {
      setIsDesktop(typeof window !== "undefined" && window.innerWidth >= 768);
    };
    updateLayout();
    window.addEventListener("resize", updateLayout);
    return () => window.removeEventListener("resize", updateLayout);
  }, []);

  // Deterministically derived selected route (prevents stale selection without effect churn)
  const effectiveRouteId = useMemo(() => {
    if (!routes || routes.length === 0) return null;
    if (activeRouteId && routes.some((r) => r.id === activeRouteId)) {
      return activeRouteId;
    }
    return routes[0].id;
  }, [routes, activeRouteId]);

  const activeRoute = useMemo(() => {
    if (!routes || routes.length === 0) return null;
    return routes.find((r) => r.id === effectiveRouteId) || routes[0];
  }, [routes, effectiveRouteId]);

  // Construct GeoJSON FeatureCollection with enriched selection and leg focus
  const activeGeoJson = useMemo(() => {
    return enrichGeoJsonWithSelection(
      routes,
      effectiveRouteId,
      focusedLegIndex,
      hoveredLegIndex
    );
  }, [routes, effectiveRouteId, focusedLegIndex, hoveredLegIndex]);

  const handlePlanSearch = (params: {
    source: string;
    destination: string;
    preferences: string[];
    travelTime?: string;
  }) => {
    setHasSearched(true);
    setLastSearchSource(params.source);
    setLastSearchDest(params.destination);
    setActiveRouteId(null);
    setFocusedLegIndex(null);
    setHoveredLegIndex(null);
    setViewState("RESULTS");
    planJourney(params);
  };

  const handleReset = () => {
    liveTracking.cancelTracking();
    useActiveJourneyStore.getState().clearActiveJourney();
    resetJourney();
    setActiveRouteId(null);
    setFocusedLegIndex(null);
    setHoveredLegIndex(null);
    setViewState("SEARCH");
    setHasSearched(false);
  };

  const handleRouteSelect = (routeId: string) => {
    if (routeId !== effectiveRouteId) {
      setActiveRouteId(routeId);
      setFocusedLegIndex(null);
      setHoveredLegIndex(null);
    }
  };

  const handleViewDetails = (routeId: string) => {
    handleRouteSelect(routeId);
    setViewState("DETAIL");
    setMobileSheetSnap("EXPANDED");
  };

  const handleBackToResults = () => {
    setViewState("RESULTS");
    setFocusedLegIndex(null);
    setHoveredLegIndex(null);
  };

  const handleLegSelect = (legIndex: number | null) => {
    setFocusedLegIndex(legIndex);
  };

  const handleLegHover = (legIndex: number | null) => {
    setHoveredLegIndex(legIndex);
  };

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] overflow-hidden bg-background">
      {/* 1. PERSISTENT FULL-BLEED MAP CANVAS */}
      <div className="absolute inset-0 w-full h-full z-0">
        <SafeMap
          source={{ coordinates: data?.source_loc }}
          destination={{ coordinates: data?.dest_loc }}
          sourceName={lastSearchSource}
          destinationName={lastSearchDest}
          routeGeometry={activeGeoJson}
          hasSearched={hasSearched}
          isLoading={isLoading}
          hasError={isError}
          activeRouteId={effectiveRouteId}
          focusedLegIndex={focusedLegIndex}
          hoveredLegIndex={hoveredLegIndex}
          isDesktop={isDesktop}
          liveLocation={liveTracking.latestTelemetry}
          nearbyPois={activeRoute?.nearby_pois}
          activityZones={activeRoute?.activity_zones}
          selectedPoi={selectedPoi}
          selectedZone={selectedZone}
          onPoiSelect={handlePoiSelect}
          onZoneSelect={handleZoneSelect}
          onRouteClick={(props: Record<string, unknown>) => {
            if (typeof props?.routeId === "string") {
              handleRouteSelect(props.routeId);
            }
          }}
        />
      </div>

      {/* 2. DESKTOP FLOATING MOBILITY PANEL (Hidden on Mobile) */}
      <div className="hidden md:flex absolute top-4 left-4 bottom-4 z-20 pointer-events-none">
        <motion.div
          animate={{
            width: isDesktopPanelCollapsed ? 56 : 420,
            opacity: 1,
          }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="relative h-full flex flex-col rounded-2xl border border-border bg-card/95 backdrop-blur-xl shadow-2xl pointer-events-auto overflow-hidden"
        >
          {/* Header Bar */}
          <div className="p-3.5 border-b border-border flex items-center justify-between shrink-0 bg-secondary/30">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <Navigation className="w-4 h-4" />
              </div>
              {!isDesktopPanelCollapsed && (
                <div>
                  <h2 className="font-extrabold text-foreground text-sm tracking-tight leading-tight">
                    NavSakhi Journey Planner
                  </h2>
                  <p className="text-[10px] text-muted-foreground font-medium">
                    Environmental Safety Risk Proxy
                  </p>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => setIsDesktopPanelCollapsed(!isDesktopPanelCollapsed)}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              title={isDesktopPanelCollapsed ? "Expand panel" : "Collapse panel"}
              aria-label={isDesktopPanelCollapsed ? "Expand panel" : "Collapse panel"}
            >
              {isDesktopPanelCollapsed ? (
                <PanelLeftOpen className="w-4 h-4" />
              ) : (
                <PanelLeftClose className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Collapsed State Bar */}
          {isDesktopPanelCollapsed ? (
            <div className="flex-1 flex flex-col items-center py-4 gap-4">
              <button
                type="button"
                onClick={() => setIsDesktopPanelCollapsed(false)}
                className="w-10 h-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center shadow-md hover:opacity-90"
                title="Open Journey Planner"
              >
                <SlidersHorizontal className="w-5 h-5" />
              </button>
            </div>
          ) : (
            /* Expanded Desktop Content */
            <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
              {/* Top View Selector / Status Bar */}
              {viewState !== "SEARCH" && (
                <div className="px-4 py-2 border-b border-border/80 bg-muted/30 flex items-center justify-between text-xs font-semibold shrink-0">
                  <div className="flex items-center gap-1.5 text-muted-foreground truncate max-w-[280px]">
                    <span className="truncate">{lastSearchSource || "Origin"}</span>
                    <span>→</span>
                    <span className="truncate">{lastSearchDest || "Destination"}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (viewState === "DETAIL") {
                        handleBackToResults();
                      } else {
                        setViewState("SEARCH");
                      }
                    }}
                    className="text-primary hover:underline text-[11px] font-bold shrink-0 ml-2"
                  >
                    {viewState === "DETAIL" ? "View All" : "Edit Inputs"}
                  </button>
                </div>
              )}

              {/* View 1: Search Form */}
              {viewState === "SEARCH" && (
                <ScrollArea className="flex-1 min-h-0">
                  <JourneySearchPanel
                    isLoading={isLoading}
                    hasRoutes={routes.length > 0}
                    onSearch={handlePlanSearch}
                    onReset={handleReset}
                    initialSource={lastSearchSource}
                    initialDest={lastSearchDest}
                  />

                  {/* Informational Guidance Box */}
                  <div className="mx-4 mb-4 p-3 rounded-xl bg-secondary/30 border border-border/70 text-xs text-muted-foreground space-y-1.5">
                    <div className="flex items-center gap-1.5 font-bold text-foreground">
                      <Shield className="w-3.5 h-3.5 text-primary" />
                      <span>Environmental Risk Assessment</span>
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      NavSakhi assesses candidate road segments using historical spatial features and infrastructure proxies via a frozen LightGBM model. NavSakhi does not provide personal safety guarantees.
                    </p>
                  </div>
                </ScrollArea>
              )}

              {/* View 2: Route Alternatives List */}
              {viewState === "RESULTS" && (
                <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                  <div className="px-4 py-3 flex items-center justify-between border-b border-border/60 bg-card shrink-0">
                    <div>
                      <h3 className="font-bold text-foreground text-sm">
                        Recommended Routes
                      </h3>
                      <p className="text-[11px] text-muted-foreground">
                        {isLoading
                          ? "Calculating route candidates..."
                          : `${routes.length} options calculated`}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setViewState("SEARCH")}
                      className="text-xs font-semibold text-primary hover:text-primary/80"
                    >
                      New Search
                    </button>
                  </div>

                  {/* Loading Skeleton State */}
                  {isLoading && (
                    <div className="flex-1 min-h-0 flex flex-col p-4 items-center justify-center space-y-4 text-center">
                      <div className="relative">
                        <div className="w-10 h-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
                        <Navigation className="w-4 h-4 text-primary absolute inset-0 m-auto" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-bold text-xs text-foreground">Evaluating Route Alternatives</h4>
                        <p className="text-[11px] text-muted-foreground max-w-[260px]">
                          Generating road geometry and evaluating environmental risk factors...
                        </p>
                      </div>
                      <div className="w-full space-y-2.5 pt-2">
                        {[1, 2].map((i) => (
                          <div key={i} className="w-full h-24 rounded-xl border border-border/60 bg-muted/20 animate-pulse p-3 flex flex-col justify-between">
                            <div className="flex justify-between items-center">
                              <div className="w-28 h-3.5 rounded bg-muted/60" />
                              <div className="w-12 h-4 rounded bg-muted/60" />
                            </div>
                            <div className="w-36 h-2.5 rounded bg-muted/40" />
                            <div className="w-28 h-3 rounded bg-muted/50" />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error State */}
                  {!isLoading && isError && (
                    <div className="flex-1 min-h-0 flex flex-col p-6 items-center justify-center space-y-3 text-center">
                      <div className="w-10 h-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-bold text-xs text-foreground">Route Search Failed</h4>
                        <p className="text-[11px] text-muted-foreground max-w-[260px]">
                          {error || "An error occurred while finding safe route options."}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => {
                            if (lastSearchSource && lastSearchDest) {
                              handlePlanSearch({ source: lastSearchSource, destination: lastSearchDest, preferences: [] });
                            } else {
                              setViewState("SEARCH");
                            }
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:opacity-90"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Retry
                        </button>
                        <button
                          type="button"
                          onClick={() => setViewState("SEARCH")}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-border hover:bg-secondary text-foreground"
                        >
                          Edit
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Empty State */}
                  {!isLoading && !isError && isEmpty && (
                    <div className="flex-1 min-h-0 flex flex-col p-6 items-center justify-center space-y-3 text-center">
                      <div className="w-10 h-10 rounded-full bg-amber-500/10 text-amber-600 flex items-center justify-center">
                        <SearchX className="w-5 h-5" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-bold text-xs text-foreground">No Route Available</h4>
                        <p className="text-[11px] text-muted-foreground max-w-[260px]">
                          The routing engine could not find valid road geometry between the specified endpoints.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setViewState("SEARCH")}
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:opacity-90"
                      >
                        Adjust Coordinates
                      </button>
                    </div>
                  )}

                  {/* Zero Distance Notice */}
                  {!isLoading && zeroDistance && (
                    <div className="m-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                      <span>You are already at your destination. Distance: 0 km.</span>
                    </div>
                  )}

                  {/* Warnings Notice */}
                  {!isLoading && warnings.length > 0 && (
                    <div className="mx-4 mt-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs space-y-1">
                      {warnings.map((w, idx) => (
                        <div key={idx} className="flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-600" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* All Routes Low Night Indicators Notice */}
                  {!isLoading && !isError && routes.length > 0 && routes.every(r => r.night_activity_score && r.night_activity_score.overall_score < 30 && r.night_activity_score.status !== "OUT_OF_BOUNDS") && (
                    <div className="mx-4 mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2">
                      <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                      <div className="space-y-0.5">
                        <span className="font-bold">Comparative Route Guidance:</span>
                        <p className="text-[11px] leading-relaxed">
                          All available routes exhibit limited nighttime activity indicators (&lt; 30 raw score). The system highlights the strongest relative option, but please review leg-level lighting, road type, and transit access before travelling.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Routes Scroll Area */}
                  {!isLoading && !isError && routes.length > 0 && (
                    <ScrollArea className="flex-1 min-h-0 p-4 overscroll-contain">
                      <div className="space-y-3 pb-2">
                        {routes.map((route) => (
                          <RouteCard
                            key={route.id}
                            route={route}
                            isSelected={route.id === effectiveRouteId}
                            onSelect={handleRouteSelect}
                            onViewDetails={handleViewDetails}
                          />
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </div>
              )}

              {/* View 3: Selected Route Deep Detail */}
              {viewState === "DETAIL" && activeRoute && (
                <RouteDetailPanel
                  route={activeRoute}
                  journeyId={data?.journey_id}
                  focusedLegIndex={focusedLegIndex}
                  hoveredLegIndex={hoveredLegIndex}
                  onLegSelect={handleLegSelect}
                  onLegHover={handleLegHover}
                  onBack={handleBackToResults}
                  tracking={liveTracking}
                />
              )}
            </div>
          )}
        </motion.div>
      </div>

      {/* 3. MOBILE RESPONSIVE BOTTOM SHEET & POI DETAILS (< 768px) */}
      <div className="md:hidden">
        {/* Top Floating Origin/Dest Bar */}
        <div className="absolute top-3 inset-x-3 z-20 pointer-events-auto">
          <div
            onClick={() => {
              setViewState("SEARCH");
              setMobileSheetSnap("EXPANDED");
              setSelectedPoi(null);
            }}
            className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/95 backdrop-blur-xl shadow-lg cursor-pointer"
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2.5 h-2.5 rounded-full bg-primary shrink-0 ring-2 ring-primary/20" />
              <span className="text-xs font-bold text-foreground truncate">
                {lastSearchDest || "Where to? Plan safe route"}
              </span>
            </div>
            <span className="text-[11px] font-semibold text-primary shrink-0 pl-2">
              {viewState === "SEARCH" ? "Edit" : "Search"}
            </span>
          </div>
        </div>

        {/* Priority A2: Mobile POI Detail Sheet (Stacked ABOVE collapsed journey bottom sheet at z-50) */}
        {!isDesktop && selectedPoi && (
          <div className="absolute inset-x-3 bottom-20 z-50 max-h-[55vh] flex flex-col bg-slate-950/98 backdrop-blur-2xl text-slate-100 rounded-2xl border border-slate-700 shadow-2xl p-4 space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2 shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xl shrink-0">
                  {POI_CATEGORY_CONFIG[selectedPoi.category]?.icon || "📍"}
                </span>
                <div className="min-w-0">
                  <span className="font-extrabold text-slate-300 uppercase tracking-wider text-[10px] block">
                    {selectedPoi.category_label || selectedPoi.category}
                  </span>
                  <h4 className="font-bold text-white text-sm leading-snug truncate">
                    {selectedPoi.name}
                  </h4>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {selectedPoi.is_emergency ? (
                  <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                    EMERGENCY
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
                  onClick={() => setSelectedPoi(null)}
                  className="w-7 h-7 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors ml-1 cursor-pointer"
                  aria-label="Close POI details"
                  title="Close POI details"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Scrollable details */}
            <ScrollArea className="flex-1 min-h-0 pr-1">
              <div className="space-y-2.5 text-xs">
                {selectedPoi.address && (
                  <p className="text-[11px] text-slate-300 flex items-start gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
                    <span>{selectedPoi.address}</span>
                  </p>
                )}

                <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1.5">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Distance to Route:</span>
                    <span className="font-bold text-cyan-400 font-mono">
                      {selectedPoi.distance_to_route_m} m
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Estimated Pass-Through:</span>
                    <span className="font-semibold text-slate-200">
                      {selectedPoi.estimated_pass_through_time || "En route"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-400">Hours:</span>
                    <span className="font-mono text-[10.5px] text-emerald-300 truncate max-w-[190px]">
                      {selectedPoi.opening_hours || "Schedule unknown (Not published)"}
                    </span>
                  </div>
                  {selectedPoi.phone && (
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-slate-400">Phone:</span>
                      <a href={`tel:${selectedPoi.phone}`} className="font-semibold text-cyan-400 hover:underline flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        <span>{selectedPoi.phone}</span>
                      </a>
                    </div>
                  )}
                  {selectedPoi.website && (
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-slate-400">Website:</span>
                      <a
                        href={selectedPoi.website.startsWith("http") ? selectedPoi.website : `https://${selectedPoi.website}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:underline truncate max-w-[190px] flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3 shrink-0" />
                        <span>{selectedPoi.website.replace(/^https?:\/\//, "")}</span>
                      </a>
                    </div>
                  )}
                </div>

                <div className="text-[10px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-1.5">
                  <span>Source: OpenStreetMap (ODbL)</span>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedPoi(null);
                      setMobileSheetSnap("HALF");
                    }}
                    className="text-cyan-400 hover:underline font-bold"
                  >
                    View Route Options →
                  </button>
                </div>
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Mobile Activity Zone Sheet */}
        {!isDesktop && selectedZone && (
          <div className="absolute inset-x-3 bottom-20 z-50 max-h-[45vh] flex flex-col bg-slate-950/98 backdrop-blur-2xl text-slate-100 rounded-2xl border border-amber-500/50 shadow-2xl p-4 space-y-2.5 animate-in fade-in slide-in-from-bottom-4 duration-200">
            <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2 shrink-0">
              <div className="flex items-center gap-1.5">
                <span className="text-lg">✨</span>
                <span className="font-extrabold text-amber-300 uppercase tracking-wider text-[11px]">
                  Activity Area
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="px-2 py-0.5 rounded-full text-[9.5px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  {selectedZone.activity_level}
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedZone(null)}
                  className="w-7 h-7 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors ml-1 cursor-pointer"
                  aria-label="Close Activity Zone details"
                  title="Close Activity Zone details"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-1">
              <h4 className="font-bold text-white text-sm leading-snug">
                {selectedZone.name}
              </h4>
              <p className="text-[11px] text-slate-300">
                Spatial commercial cluster along the corridor.
              </p>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Cluster Radius:</span>
                <span className="font-semibold text-slate-200 font-mono">~{selectedZone.radius_m} m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Data Source:</span>
                <span className="font-semibold text-slate-200">{selectedZone.source}</span>
              </div>
            </div>

            <p className="italic text-slate-400 text-[9.5px] leading-tight border-t border-slate-800 pt-1.5">
              {selectedZone.disclosure}
            </p>
          </div>
        )}

        {/* Priority A1: Coordinated Collapsible Bottom Sheet (Collapsed: 64px, Compact: 38vh, Expanded: 80vh) */}
        <motion.div
          animate={{
            height:
              mobileSheetSnap === "PEEK"
                ? "64px"
                : mobileSheetSnap === "HALF"
                ? "38vh"
                : "80vh",
          }}
          transition={{ type: "spring", damping: 28, stiffness: 280 }}
          className="absolute inset-x-0 bottom-0 z-30 flex flex-col rounded-t-3xl border-t border-border bg-card/98 backdrop-blur-2xl shadow-2xl overflow-hidden pb-safe"
        >
          {/* Action Header / Minimize / Restore Bar */}
          <div className="w-full pt-2.5 pb-2 px-4 flex items-center justify-between shrink-0 select-none bg-secondary/30 border-b border-border/50">
            {/* Left Status / Category indicator */}
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2 h-2 rounded-full bg-primary shrink-0 animate-pulse" />
              <span className="text-xs font-bold text-foreground truncate">
                {viewState === "SEARCH"
                  ? "Route Planner"
                  : viewState === "DETAIL"
                  ? (activeRoute?.route_name || "Route Details")
                  : `${routes.length} Route Options`}
              </span>
              {activeRoute && mobileSheetSnap === "PEEK" && viewState !== "SEARCH" && (
                <span className="text-[11px] font-semibold text-muted-foreground truncate hidden xs:inline">
                  • {activeRoute.eta} ({activeRoute.distance})
                </span>
              )}
            </div>

            {/* Center Drag Handle */}
            <div
              onClick={() => {
                setMobileSheetSnap(
                  mobileSheetSnap === "PEEK"
                    ? "HALF"
                    : mobileSheetSnap === "HALF"
                    ? "EXPANDED"
                    : "HALF"
                );
              }}
              className="w-10 h-1.5 rounded-full bg-muted-foreground/40 cursor-pointer hover:bg-muted-foreground/60 transition-colors mx-2"
              title="Drag or tap to adjust sheet height"
            />

            {/* Right Explicit Minimize / Expand Controls */}
            <div className="flex items-center gap-1.5 shrink-0">
              {mobileSheetSnap !== "PEEK" ? (
                <button
                  type="button"
                  onClick={() => setMobileSheetSnap("PEEK")}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-secondary hover:bg-secondary/80 text-[11px] font-bold text-foreground border border-border shadow-xs transition-colors cursor-pointer"
                  title="Minimize panel to inspect map"
                  aria-label="Minimize panel to map"
                >
                  <Minimize2 className="w-3 h-3 text-muted-foreground" />
                  <span>Map View</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setMobileSheetSnap(viewState === "DETAIL" ? "EXPANDED" : "HALF")}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary hover:bg-primary/90 text-[11px] font-bold text-primary-foreground shadow-xs transition-colors cursor-pointer"
                  title="Expand route options"
                  aria-label="Expand route options"
                >
                  <span>{viewState === "SEARCH" ? "Plan" : `Routes (${routes.length})`}</span>
                  <ChevronUp className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* Sheet Body (Rendered when expanded or half) */}
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
            {viewState === "SEARCH" && (
              <ScrollArea className="flex-1 min-h-0">
                <JourneySearchPanel
                  isLoading={isLoading}
                  hasRoutes={routes.length > 0}
                  onSearch={(params) => {
                    handlePlanSearch(params);
                    setMobileSheetSnap("HALF");
                  }}
                  onReset={handleReset}
                  initialSource={lastSearchSource}
                  initialDest={lastSearchDest}
                />
              </ScrollArea>
            )}

            {viewState === "RESULTS" && (
              <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                <div className="px-4 py-2 border-b border-border flex items-center justify-between text-xs shrink-0 bg-muted/20">
                  <span className="font-bold text-foreground">
                    {isLoading ? "Searching..." : `${routes.length} Available Routes`}
                  </span>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setMobileSheetSnap("PEEK")}
                      className="font-medium text-muted-foreground hover:text-foreground text-[11px]"
                    >
                      Hide to Map
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setViewState("SEARCH");
                        setMobileSheetSnap("EXPANDED");
                      }}
                      className="font-semibold text-primary text-[11px]"
                    >
                      Edit Search
                    </button>
                  </div>
                </div>

                {isLoading && (
                  <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 space-y-3">
                    <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
                    <p className="text-xs text-muted-foreground">Calculating routes...</p>
                  </div>
                )}

                {!isLoading && isError && (
                  <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 space-y-2 text-center">
                    <AlertTriangle className="w-6 h-6 text-destructive" />
                    <p className="text-xs text-foreground font-semibold">Route calculation failed</p>
                    <p className="text-[11px] text-muted-foreground">{error}</p>
                  </div>
                )}

                {!isLoading && !isError && isEmpty && (
                  <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-6 space-y-2 text-center">
                    <SearchX className="w-6 h-6 text-amber-500" />
                    <p className="text-xs text-foreground font-semibold">No routes found</p>
                    <p className="text-[11px] text-muted-foreground">Try adjusting your origin or destination.</p>
                  </div>
                )}

                {!isLoading && !isError && routes.length > 0 && (
                  <ScrollArea className="flex-1 min-h-0 p-3 overscroll-contain touch-pan-y">
                    <div className="space-y-2.5 pb-8">
                      {routes.map((route) => (
                        <RouteCard
                          key={route.id}
                          route={route}
                          isSelected={route.id === effectiveRouteId}
                          onSelect={handleRouteSelect}
                          onViewDetails={handleViewDetails}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </div>
            )}

            {viewState === "DETAIL" && activeRoute && (
              <RouteDetailPanel
                route={activeRoute}
                journeyId={data?.journey_id}
                focusedLegIndex={focusedLegIndex}
                hoveredLegIndex={hoveredLegIndex}
                onLegSelect={handleLegSelect}
                onLegHover={handleLegHover}
                onBack={handleBackToResults}
                tracking={liveTracking}
              />
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
