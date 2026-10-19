"use client";

import { useState } from "react";
import { MultimodalRoute } from "@/types/journey";
import { RouteScoreBadge } from "./RouteScoreBadge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { journeyService } from "@/api/services/journeyService";
import { toast } from "sonner";
import Link from "next/link";
import { useActiveJourneyStore } from "@/store/activeJourneyStore";
import { useAuthStore } from "@/store/authStore";
import { 
  ArrowLeft, ShieldCheck, Footprints, Train, Bus, Car, Bike, 
  Leaf, Info, Navigation, Play, Pause, Square, CheckCircle2, Layers,
  AlertTriangle, Radio, TrendingUp, TrendingDown, Building2, Check
} from "lucide-react";

interface RouteDetailPanelProps {
  route: MultimodalRoute;
  journeyId?: string;
  focusedLegIndex?: number | null;
  hoveredLegIndex?: number | null;
  onBack: () => void;
  onLegSelect?: (legIndex: number | null) => void;
  onLegHover?: (legIndex: number | null) => void;
  onSegmentFocus?: (segmentIndex: number) => void;
  tracking?: {
    lifecycleState: string;
    permissionState: string;
    permissionError: string | null;
    latestTelemetry: { lat: number; lng: number; accuracy: number | null; timestamp: number } | null;
    serverProgress: {
      progressPercentage: number;
      distanceRemainingM: number;
      distanceFromRouteM: number | null;
      isOnRoute: boolean;
      statusLabel: string;
      lastUpdated: string;
    } | null;
    isStale: boolean;
    startTracking: (journeyId: string, selectedRouteId?: string) => Promise<void>;
    pauseTracking: () => Promise<void>;
    resumeTracking: () => Promise<void>;
    completeTracking: () => Promise<void>;
    cancelTracking: () => Promise<void>;
  };
}

export function RouteDetailPanel({
  route,
  journeyId,
  focusedLegIndex = null,
  hoveredLegIndex = null,
  onBack,
  onLegSelect,
  onLegHover,
  onSegmentFocus,
  tracking,
}: RouteDetailPanelProps) {
  const [isStartingInternal, setIsStartingInternal] = useState(false);
  const [hasStartedInternal, setHasStartedInternal] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const getModeIcon = (mode: string) => {
    const m = mode.toLowerCase();
    if (m.includes("walk") || m.includes("foot")) return <Footprints className="w-4 h-4" />;
    if (m.includes("metro") || m.includes("train") || m.includes("rail") || m.includes("mrts") || m.includes("suburban")) {
      return <Train className="w-4 h-4" />;
    }
    if (m.includes("bus")) return <Bus className="w-4 h-4" />;
    if (m.includes("bike") || m.includes("two_wheeler") || m.includes("scooter")) {
      return <Bike className="w-4 h-4" />;
    }
    return <Car className="w-4 h-4" />;
  };

  const isTracking = tracking ? tracking.lifecycleState === "TRACKING" : hasStartedInternal;
  const isPaused = tracking ? tracking.lifecycleState === "PAUSED" : false;
  const isStarting = tracking ? tracking.lifecycleState === "STARTING" : isStartingInternal;

  const handleStartJourney = async () => {
    if (tracking) {
      if (journeyId) {
        useActiveJourneyStore.getState().setActiveJourney(journeyId, route.id);
        await tracking.startTracking(journeyId, route.id);
      } else {
        toast.info("Preview route mode active.");
      }
      return;
    }

    if (!journeyId) {
      toast.info("Journey preview mode active.");
      setHasStartedInternal(true);
      return;
    }

    setIsStartingInternal(true);
    try {
      useActiveJourneyStore.getState().setActiveJourney(journeyId, route.id);
      await journeyService.startJourney(journeyId, route.id);
      setHasStartedInternal(true);
      toast.success("Journey Started", {
        description: "Live safety monitoring and WebSocket telemetry active.",
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Could not register journey start.";
      toast.error("Failed to start journey", {
        description: message,
      });
    } finally {
      setIsStartingInternal(false);
    }
  };

  const coveragePercent = typeof route.scoreable_coverage_ratio === "number"
    ? Math.round(route.scoreable_coverage_ratio * 100)
    : null;

  return (
    <div className="flex flex-col h-full bg-card overflow-hidden">
      {/* Top Header */}
      <div className="p-3.5 border-b border-border flex items-center justify-between shrink-0 bg-secondary/30">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={onBack}
            className="h-8 w-8 text-foreground hover:bg-secondary"
            aria-label="Back to route list"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h3 className="font-bold text-foreground text-sm truncate max-w-[220px]">
              {route.route_name || "Route Details"}
            </h3>
            <p className="text-[11px] text-muted-foreground capitalize">
              {route.travel_mode_chain || route.mode}
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-base font-black text-foreground">{route.eta}</span>
          <span className="text-xs text-muted-foreground block">{route.distance}</span>
        </div>
      </div>

      {/* Scrollable Content */}
      <ScrollArea className="flex-1 min-h-0 p-4">
        <div className="space-y-4 pb-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-secondary/40 border border-border/70 p-3 rounded-xl flex flex-col justify-between">
              <div className="flex items-center justify-between gap-1 flex-wrap">
                <span className="text-[11px] text-muted-foreground font-semibold flex items-center gap-1">
                  <Navigation className="w-3.5 h-3.5 text-primary" /> Journey Cost
                </span>
                {route.fare ? (
                  route.fare.fare_type === "OFFICIAL_FARE" ? (
                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Official Fare
                    </span>
                  ) : route.fare.fare_type === "ESTIMATED_FARE" ? (
                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Estimated
                    </span>
                  ) : route.fare.fare_type === "METERED_VARIABLE" ? (
                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      Metered
                    </span>
                  ) : route.fare.fare_type === "NOT_APPLICABLE" ? (
                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">
                      Variable
                    </span>
                  ) : (
                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      Unavailable
                    </span>
                  )
                ) : null}
              </div>
              <div className="mt-1">
                <span className="text-base font-black text-foreground block">
                  {route.fare?.display_text || route.cost || "Fare unavailable"}
                </span>
                {route.fare?.source_label && (
                  <span className="text-[10px] text-muted-foreground/80 block mt-0.5 truncate" title={route.fare.source_label}>
                    {route.fare.source_label}
                  </span>
                )}
              </div>
            </div>

            <div className="bg-secondary/40 border border-border/70 p-3 rounded-xl flex flex-col justify-between">
              <span className="text-[11px] text-muted-foreground font-semibold flex items-center gap-1">
                <Leaf className="w-3.5 h-3.5 text-emerald-600" /> Env Risk
              </span>
              <span className="text-lg font-black text-foreground mt-1">
                {route.environmental_risk ?? 50}/100
              </span>
            </div>
          </div>

          {/* Machine Learning Safety Score Breakdown */}
          <div className="bg-card border border-border rounded-xl p-3.5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <ShieldCheck className="w-4 h-4 text-primary" />
                <span>Environmental Safety Assessment</span>
              </div>
              {route.model_version && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                  v{route.model_version}
                </span>
              )}
            </div>

            {/* Score Badge & Status */}
            <div>
              <RouteScoreBadge
                score={route.safety_score}
                scoreStatus={route.score_status}
                coverageRatio={route.scoreable_coverage_ratio}
                size="lg"
                showCoverage={false}
              />
            </div>

            {/* Scoreable Coverage Progress Bar */}
            {coveragePercent !== null && (
              <div className="space-y-1 pt-1">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-muted-foreground">Evaluated Road Coverage</span>
                  <span className={`font-semibold ${coveragePercent >= 70 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                    {coveragePercent}% {coveragePercent < 70 ? "(Insufficient for Score)" : "(Meets Policy)"}
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 rounded-full ${
                      coveragePercent >= 70 ? "bg-emerald-500" : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, coveragePercent))}%` }}
                  />
                </div>
                <p className="text-[10px] text-muted-foreground/80">
                  Model requires $\ge 70\%$ scoreable road length to issue verified route score.
                </p>
              </div>
            )}

            {/* Synthetic Environmental Proxy Disclosure */}
            <div className="text-[11px] leading-relaxed bg-muted/40 border border-border/60 p-2.5 rounded-lg text-muted-foreground space-y-1">
              <div className="flex items-center gap-1 font-semibold text-foreground text-xs">
                <Info className="w-3.5 h-3.5 text-primary shrink-0" />
                <span>Synthetic Model Limitation Notice</span>
              </div>
              <p>
                {route.target_disclosure ||
                  "Score is a synthetic environmental proxy (100.0 - risk_score_raw) trained on OSM road features. It does not reflect verified crime or victimization ground truth and does not guarantee personal safety."}
              </p>
            </div>

            {/* Verified Facilities Near Selected Journey */}
            <div className="space-y-2 pt-1 border-t border-border/60">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-primary" />
                  <span>Verified Nearby Facilities</span>
                </h4>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground border border-border">
                  {route.nearby_pois?.length || 0} mapped
                </span>
              </div>

              {route.nearby_pois && route.nearby_pois.length > 0 ? (
                <div className="space-y-1.5">
                  {/* Category counts overview */}
                  <div className="flex flex-wrap gap-1.5">
                    {(() => {
                      const counts: Record<string, number> = {};
                      route.nearby_pois.forEach((p) => {
                        counts[p.category] = (counts[p.category] || 0) + 1;
                      });
                      const labels: Record<string, string> = {
                        police: "🛡️ Police",
                        hospital: "🏥 Hospital",
                        clinic: "🩺 Clinic",
                        pharmacy: "💊 Pharmacy",
                        fire_station: "🚒 Fire",
                      };
                      return Object.entries(counts).map(([cat, cnt]) => (
                        <span
                          key={cat}
                          className="px-2 py-0.5 rounded-lg bg-secondary/80 border border-border text-[11px] font-semibold text-foreground flex items-center gap-1"
                        >
                          <span>{labels[cat] || cat}</span>
                          <span className="text-primary font-bold">({cnt})</span>
                        </span>
                      ));
                    })()}
                  </div>

                  {/* Top nearest facilities list */}
                  <div className="space-y-1">
                    {route.nearby_pois.slice(0, 4).map((poi) => (
                      <div
                        key={poi.poi_id}
                        className="flex items-center justify-between p-2 rounded-lg bg-card border border-border/70 text-xs hover:border-primary/50 transition-colors"
                      >
                        <div className="min-w-0 pr-2">
                          <p className="font-semibold text-foreground truncate text-[11px]">{poi.name}</p>
                          <span className="text-[10px] text-muted-foreground capitalize">
                            {poi.category_label || poi.category}
                          </span>
                        </div>
                        <div className="text-right shrink-0">
                          <span className="font-bold text-primary text-[11px] block">{poi.distance_to_route_m} m</span>
                          <span className="text-[9px] text-muted-foreground">from route</span>
                        </div>
                      </div>
                    ))}
                    {route.nearby_pois.length > 4 && (
                      <p className="text-[10px] text-muted-foreground text-center pt-0.5">
                        + {route.nearby_pois.length - 4} additional verified facilities along route (interactive on map)
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-3 text-center text-xs text-muted-foreground bg-muted/20 border border-border/40 rounded-xl">
                  No verified facilities recorded within the 800m route corridor.
                </div>
              )}
            </div>

            {/* Machine Learning Feature Attribution (Genuine LightGBM TreeSHAP) */}
            <div className="space-y-2 pt-1 border-t border-border/60">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                  <span>ML Feature Attribution</span>
                </h4>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                  LightGBM TreeSHAP
                </span>
              </div>

              {route.model_attribution && route.model_attribution.status === "VALIDATED_ATTRIBUTION" ? (
                <div className="space-y-2 p-3 rounded-xl bg-secondary/30 border border-border/80 text-xs">
                  {/* Reconstruction Verification */}
                  <div className="flex items-center justify-between text-[11px] pb-1.5 border-b border-border/60">
                    <span className="text-muted-foreground">Baseline Expected Score:</span>
                    <span className="font-mono font-bold text-foreground">
                      {route.model_attribution.base_value.toFixed(2)}
                    </span>
                  </div>

                  {route.model_attribution.is_mathematically_reconstructed && (
                    <div className="flex items-center gap-1.5 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                      <Check className="w-3 h-3 shrink-0" />
                      <span>Mathematical TreeSHAP Reconstruction Validated (Error &lt; 0.05)</span>
                    </div>
                  )}

                  {/* Positive Factors (Safety Enhancing) */}
                  {route.model_attribution.top_positive_factors && route.model_attribution.top_positive_factors.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        <span>Safety-Enhancing Factors</span>
                      </span>
                      <div className="space-y-1">
                        {route.model_attribution.top_positive_factors.slice(0, 3).map((f, fi) => (
                          <div key={fi} className="flex justify-between items-center text-[11px] pl-2 border-l-2 border-emerald-500/50">
                            <span className="text-foreground">{f.feature}</span>
                            <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                              +{f.attribution.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Negative Factors (Risk Depressing) */}
                  {route.model_attribution.top_negative_factors && route.model_attribution.top_negative_factors.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1">
                        <TrendingDown className="w-3 h-3" />
                        <span>Risk-Increasing Factors</span>
                      </span>
                      <div className="space-y-1">
                        {route.model_attribution.top_negative_factors.slice(0, 2).map((f, fi) => (
                          <div key={fi} className="flex justify-between items-center text-[11px] pl-2 border-l-2 border-rose-500/50">
                            <span className="text-foreground">{f.feature}</span>
                            <span className="font-mono font-bold text-rose-600 dark:text-rose-400">
                              {f.attribution.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-[9.5px] text-muted-foreground/90 italic pt-1 border-t border-border/40">
                    Attributions are computed directly from frozen LightGBM decision trees. They explain the synthetic environmental safety proxy, not empirical crime causation.
                  </p>
                </div>
              ) : (
                <div className="p-3 text-center text-xs text-muted-foreground bg-muted/20 border border-border/40 rounded-xl space-y-1">
                  <p className="font-semibold text-foreground">Feature attribution unavailable</p>
                  <p className="text-[11px]">
                    {route.score_status === "NOT_SCORED"
                      ? "Transit infrastructure is not modeled by the road-segment LightGBM pipeline."
                      : route.score_status === "INSUFFICIENT_COVERAGE"
                      ? "Route has insufficient scoreable road coverage (< 70%) for model evaluation."
                      : "Feature contributions are not available for this route configuration."}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Sequential Multimodal Segments Timeline */}
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary" />
                <span>Step-by-Step Leg Details</span>
              </h4>
              {focusedLegIndex !== null && (
                <button
                  type="button"
                  onClick={() => {
                    onLegSelect?.(null);
                  }}
                  className="text-[11px] font-bold text-primary hover:underline flex items-center gap-1"
                >
                  <span>Reset to Full Route</span>
                </button>
              )}
            </div>

            {focusedLegIndex !== null && (
              <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-primary font-bold">
                  <Navigation className="w-3.5 h-3.5 shrink-0" />
                  <span>
                    Focusing Leg {(focusedLegIndex ?? 0) + 1} of{" "}
                    {route.segments?.length || 1} on map
                  </span>
                </div>
                <span className="text-[10px] text-muted-foreground">
                  Click leg again to unfocus
                </span>
              </div>
            )}

            <div className="space-y-1">
              {route.segments && route.segments.length > 0 ? (
                route.segments.map((seg, idx) => {
                  const isFocused = focusedLegIndex === idx;
                  const isHovered = hoveredLegIndex === idx;
                  const hasGeometry = Boolean(
                    seg?.polyline?.geometry &&
                    "coordinates" in seg.polyline.geometry &&
                    Array.isArray(seg.polyline.geometry.coordinates) &&
                    seg.polyline.geometry.coordinates.length > 0
                  );

                  const handleLegClick = () => {
                    const nextIndex = isFocused ? null : idx;
                    onLegSelect?.(nextIndex);
                    onSegmentFocus?.(idx);
                  };

                  const handleKeyDown = (e: React.KeyboardEvent) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleLegClick();
                    }
                  };

                  return (
                    <div
                      key={idx}
                      role="button"
                      tabIndex={0}
                      aria-pressed={isFocused}
                      aria-label={`Leg ${idx + 1}: ${seg.segment_name}, mode ${seg.transport_mode}, duration ${seg.eta}${isFocused ? ", focused on map" : ""}`}
                      onClick={handleLegClick}
                      onKeyDown={handleKeyDown}
                      onMouseEnter={() => onLegHover?.(idx)}
                      onMouseLeave={() => onLegHover?.(null)}
                      className={`flex gap-3 p-2.5 rounded-xl border transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                        isFocused
                          ? "bg-primary/10 border-primary ring-1 ring-primary/30 shadow-sm"
                          : isHovered
                          ? "bg-secondary/70 border-border"
                          : "bg-card border-transparent hover:bg-secondary/40"
                      }`}
                    >
                      {/* Timeline icon & connector */}
                      <div className="flex flex-col items-center">
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-sm z-10 shrink-0 transition-transform ${
                            isFocused ? "scale-110 ring-2 ring-primary ring-offset-2 ring-offset-background" : ""
                          }`}
                          style={{ backgroundColor: seg.color || "#8B5CF6" }}
                        >
                          {getModeIcon(seg.transport_mode)}
                        </div>
                        {idx < route.segments.length - 1 && (
                          <div className="w-0.5 flex-1 bg-border my-1 min-h-[2.5rem]" />
                        )}
                      </div>

                      {/* Leg Details */}
                      <div className="flex-1 min-w-0 pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <h5 className="font-semibold text-foreground text-xs leading-snug">
                                {seg.segment_name}
                              </h5>
                              {isFocused && (
                                <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded bg-primary text-primary-foreground">
                                  Focused
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-muted-foreground capitalize font-medium">
                              {seg.transport_mode}
                            </span>
                          </div>
                          <div className="text-right shrink-0">
                            <span className="text-xs font-bold text-foreground">{seg.eta}</span>
                            <span className="text-[10px] text-muted-foreground block">{seg.distance}</span>
                          </div>
                        </div>

                        {!hasGeometry && (
                          <div className="mt-1 text-[10px] text-amber-600 dark:text-amber-400 italic">
                            (Corridor geometry not mapped)
                          </div>
                        )}

                        {/* Per-Leg Truthful Safety Assessment Badge */}
                        {seg.safety_score != null ? (
                          <div className="mt-1.5 flex flex-col gap-0.5">
                            <div className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded w-fit">
                              <ShieldCheck className="w-3 h-3" />
                              <span>Leg Safety Score: {seg.safety_score.toFixed(1)}/100</span>
                              {seg.scoreable_coverage_ratio != null && (
                                <span className="opacity-75">
                                  ({Math.round(seg.scoreable_coverage_ratio * 100)}% coverage)
                                </span>
                              )}
                            </div>
                            {seg.score_disclosure && (
                              <span className="text-[9px] text-muted-foreground/80 leading-tight">
                                {seg.score_disclosure}
                              </span>
                            )}
                          </div>
                        ) : Boolean(seg.transport_mode && ["metro", "suburban", "train", "mrts", "bus"].some(m => seg.transport_mode.toLowerCase().includes(m))) ? (
                          <div className="mt-1.5 flex flex-col gap-0.5">
                            <div className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground bg-muted/60 px-2 py-0.5 rounded w-fit border border-border/40">
                              <Info className="w-3 h-3 text-muted-foreground/80" />
                              <span>Not scored by current model</span>
                            </div>
                            <span className="text-[9px] text-muted-foreground/80 leading-tight">
                              Transit safety data unavailable (road ML model not applied to rail tracks)
                            </span>
                          </div>
                        ) : seg.score_status === "INSUFFICIENT_COVERAGE" ? (
                          <div className="mt-1.5 flex flex-col gap-0.5">
                            <div className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded w-fit">
                              <AlertTriangle className="w-3 h-3" />
                              <span>Score unavailable</span>
                            </div>
                            <span className="text-[9px] text-muted-foreground/80 leading-tight">
                              Insufficient scoreable road coverage (&lt; 70%)
                            </span>
                          </div>
                        ) : (
                          seg.reason && seg.reason !== "VALID" && seg.reason !== "Direct route" && (
                            <div className="mt-1 text-[11px] text-muted-foreground bg-muted/60 p-1.5 rounded border border-border/50">
                              {seg.reason}
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-muted-foreground bg-muted/30 rounded-xl">
                  Single direct road corridor.
                </div>
              )}
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Bottom Sticky Action Bar & Live Telemetry Experience */}
      <div className="p-3.5 border-t border-border bg-card shrink-0 space-y-3">
        {/* Permission Error Guidance Banner */}
        {tracking?.permissionError && (
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
            <div className="space-y-1">
              <p className="font-semibold">Location Access Required</p>
              <p className="text-[11px] opacity-90">{tracking.permissionError}</p>
            </div>
          </div>
        )}

        {/* Active Telemetry & Monitoring Display */}
        {isTracking || isPaused ? (
          <div className="space-y-3">
            {/* Status & Progress Bar */}
            <div className="p-3 rounded-xl bg-secondary/50 border border-border/80 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    {isTracking && !tracking?.isStale ? (
                      <>
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                      </>
                    ) : (
                      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${tracking?.isStale ? "bg-amber-500" : "bg-muted-foreground"}`} />
                    )}
                  </span>
                  <span className="text-xs font-bold text-foreground">
                    {isPaused
                      ? "Monitoring Paused"
                      : tracking?.isStale
                      ? "GPS Signal Stale"
                      : "Live Monitored Journey"}
                  </span>
                </div>

                {/* On-Route vs Deviation Badge */}
                {tracking?.serverProgress && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      tracking.serverProgress.isOnRoute
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                    }`}
                  >
                    {tracking.serverProgress.isOnRoute
                      ? "On Route"
                      : `Deviating (${Math.round(tracking.serverProgress.distanceFromRouteM || 0)}m)`}
                  </span>
                )}
              </div>

              {/* Progress Bar */}
              {tracking?.serverProgress && (
                <div className="space-y-1">
                  <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-primary h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(0, tracking.serverProgress.progressPercentage))}%` }}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[10px] text-muted-foreground font-medium">
                    <span>
                      {tracking.serverProgress.distanceRemainingM >= 1000
                        ? `${(tracking.serverProgress.distanceRemainingM / 1000).toFixed(1)} km remaining`
                        : `${Math.round(tracking.serverProgress.distanceRemainingM)} m remaining`}
                    </span>
                    <span>{Math.round(tracking.serverProgress.progressPercentage)}% completed</span>
                  </div>
                </div>
              )}
            </div>

            {/* Lifecycle Controls */}
            <div className="flex items-center gap-2">
              {isTracking ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => tracking?.pauseTracking()}
                    className="flex-1 h-9 text-xs font-bold gap-1.5"
                  >
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause</span>
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      useActiveJourneyStore.getState().clearActiveJourney();
                      tracking?.completeTracking();
                    }}
                    className="flex-1 h-9 text-xs font-bold gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Complete</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      useActiveJourneyStore.getState().clearActiveJourney();
                      tracking?.cancelTracking();
                    }}
                    className="h-9 px-3 text-xs font-semibold text-muted-foreground hover:text-danger hover:bg-danger/10"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>Stop</span>
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    size="sm"
                    onClick={() => tracking?.resumeTracking()}
                    className="flex-1 h-9 text-xs font-bold gap-1.5 shadow-xs"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Resume Monitoring</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      useActiveJourneyStore.getState().clearActiveJourney();
                      tracking?.cancelTracking();
                    }}
                    className="h-9 px-3 text-xs font-semibold text-muted-foreground hover:text-danger hover:bg-danger/10"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>Stop</span>
                  </Button>
                </>
              )}
            </div>

            {journeyId && (
              <Link href={`/live?journeyId=${journeyId}`} className="block w-full">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full h-8 text-[11px] font-bold gap-1.5 border-primary/30 text-primary hover:bg-primary/10"
                >
                  <Radio className="w-3.5 h-3.5 text-primary animate-pulse" />
                  <span>Open Fullscreen Live Monitor</span>
                </Button>
              </Link>
            )}

            <p className="text-[10px] text-muted-foreground text-center">
              Normal route deviation does not trigger SOS or external dispatch.
            </p>
          </div>
        ) : !isAuthenticated ? (
          <div className="space-y-2">
            <Link href="/login?redirect=/journey" className="block w-full">
              <Button
                className="w-full h-11 text-sm font-bold shadow-md shadow-primary/20 flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Sign In to Start Live Tracking</span>
              </Button>
            </Link>
            <p className="text-[10px] text-muted-foreground text-center">
              Guest preview active. Sign in to start personalized GPS telemetry & alert contacts.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <Button
              onClick={handleStartJourney}
              disabled={isStarting}
              className="w-full h-11 text-sm font-bold shadow-md shadow-primary/20 flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{isStarting ? "Requesting Location..." : "Start Monitored Journey"}</span>
            </Button>
            <p className="text-[10px] text-muted-foreground text-center">
              Requires browser location permission. Telemetry streams strictly while active.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
