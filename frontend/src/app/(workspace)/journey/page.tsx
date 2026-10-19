"use client";

import { useState, useMemo, useEffect } from "react";
import { motion } from "framer-motion";
import SafeMap from "@/components/map/SafeMap";
import { useJourney } from "@/hooks/useJourney";
import { MultimodalRoute } from "@/types/journey";
import { JourneySearchPanel } from "@/components/journey/JourneySearchPanel";
import { RouteCard } from "@/components/journey/RouteCard";
import { RouteDetailPanel } from "@/components/journey/RouteDetailPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Navigation, Shield, AlertTriangle, ChevronUp, ChevronDown, 
  SlidersHorizontal, CheckCircle2, PanelLeftClose, PanelLeftOpen,
  RotateCcw, SearchX
} from "lucide-react";

import { enrichGeoJsonWithSelection } from "@/components/journey/route-sync-utils";
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

  // Form Inputs Cache for Pill Display
  const [lastSearchSource, setLastSearchSource] = useState("");
  const [lastSearchDest, setLastSearchDest] = useState("");

  const routes: MultimodalRoute[] = useMemo(
    () => data?.recommended_routes || [],
    [data?.recommended_routes]
  );
  const zeroDistance = data?.zero_distance || false;
  const warnings = data?.warnings || [];

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

      {/* 3. MOBILE RESPONSIVE BOTTOM SHEET (< 768px) */}
      <div className="md:hidden">
        {/* Top Floating Origin/Dest Bar */}
        <div className="absolute top-3 inset-x-3 z-20 pointer-events-auto">
          <div 
            onClick={() => {
              setViewState("SEARCH");
              setMobileSheetSnap("EXPANDED");
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

        {/* Draggable Bottom Sheet */}
        <motion.div
          animate={{
            height:
              mobileSheetSnap === "PEEK"
                ? "90px"
                : mobileSheetSnap === "HALF"
                ? "52vh"
                : "85vh",
          }}
          transition={{ type: "spring", damping: 28, stiffness: 280 }}
          className="absolute inset-x-0 bottom-0 z-30 flex flex-col rounded-t-3xl border-t border-border bg-card/98 backdrop-blur-2xl shadow-2xl overflow-hidden pb-safe"
        >
          {/* Pull Handle / Header */}
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
            className="w-full pt-3 pb-2 flex flex-col items-center justify-center cursor-pointer shrink-0 select-none bg-secondary/20"
          >
            <div className="w-10 h-1.5 rounded-full bg-muted-foreground/30 mb-1" />
            <div className="flex items-center gap-1 text-[11px] font-bold text-muted-foreground">
              <span>{viewState === "SEARCH" ? "Route Planner" : viewState === "DETAIL" ? "Route Details" : "Route Options"}</span>
              {mobileSheetSnap === "EXPANDED" ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronUp className="w-3.5 h-3.5" />
              )}
            </div>
          </div>

          {/* Sheet Body */}
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
                <div className="px-4 py-2 border-b border-border flex items-center justify-between text-xs shrink-0">
                  <span className="font-bold text-foreground">
                    {isLoading ? "Searching..." : `${routes.length} Available Routes`}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setViewState("SEARCH");
                      setMobileSheetSnap("EXPANDED");
                    }}
                    className="font-semibold text-primary"
                  >
                    Edit Search
                  </button>
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