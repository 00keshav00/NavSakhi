"use client";

import { Suspense, useEffect, useState, useTransition } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck, AlertTriangle, Bot, Navigation, Activity, Clock,
  MapPin, CloudRain, Eye, Sun, Users, Radio, AlertOctagon,
  Play, Pause, Square, CheckCircle2, RotateCcw
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import SafeMap from "@/components/map/SafeMap";
import { useLiveMonitor } from "@/hooks/useLiveMonitor";
import { useLiveJourneyTracking } from "@/hooks/useLiveJourneyTracking";
import { useActiveJourneyStore } from "@/store/activeJourneyStore";
import { journeyService } from "@/api/services/journeyService";
import Link from "next/link";

function LiveMonitorContent() {
  const searchParams = useSearchParams();
  const urlJourneyId = searchParams.get("journeyId");
  const { activeJourneyId, setActiveJourney, clearActiveJourney } = useActiveJourneyStore();

  const [resolvedJourneyId, setResolvedJourneyId] = useState<string | null>(
    urlJourneyId || activeJourneyId || null
  );
  const [isResolvingActive, setIsResolvingActive] = useState<boolean>(!urlJourneyId && !activeJourneyId);

  const tracking = useLiveJourneyTracking();
  const { data, isLoading, error, refetch } = useLiveMonitor(resolvedJourneyId);

  // Synchronize URL journeyId with store
  useEffect(() => {
    if (urlJourneyId && urlJourneyId !== activeJourneyId) {
      setActiveJourney(urlJourneyId);
      setResolvedJourneyId(urlJourneyId);
    }
  }, [urlJourneyId, activeJourneyId, setActiveJourney]);

  // If no journeyId in URL or store, query backend for any active/paused journey
  useEffect(() => {
    let isSubscribed = true;
    if (!urlJourneyId && !activeJourneyId) {
      setIsResolvingActive(true);
      journeyService
        .getActiveJourney()
        .then((active) => {
          if (isSubscribed && active && active.id) {
            const jId = String(active.id);
            setResolvedJourneyId(jId);
            setActiveJourney(jId, active.selected_route_id ? String(active.selected_route_id) : undefined);
          }
        })
        .catch(() => {
          // No active journey on backend
        })
        .finally(() => {
          if (isSubscribed) {
            setIsResolvingActive(false);
          }
        });
    } else {
      setIsResolvingActive(false);
    }
    return () => {
      isSubscribed = false;
    };
  }, [urlJourneyId, activeJourneyId, setActiveJourney]);

  // Auto-scroll timeline effect
  useEffect(() => {
    const timelineElement = document.getElementById("agent-timeline-scroll");
    if (timelineElement) {
      timelineElement.scrollTop = timelineElement.scrollHeight;
    }
  }, [data?.agent_timeline]);

  // Loading state
  if (isResolvingActive || (isLoading && !data && !error)) {
    return <LiveMonitorSkeleton />;
  }

  // State: IDLE — No active journey in progress
  if (!resolvedJourneyId) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center p-6 text-center bg-background">
        <div className="w-16 h-16 rounded-3xl bg-secondary/80 flex items-center justify-center mb-6 shadow-sm border border-border">
          <Bot size={36} className="text-muted-foreground" />
        </div>
        <h2 className="text-2xl font-[family-name:var(--font-jakarta)] font-extrabold text-foreground tracking-tight">
          No Journey in Progress
        </h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-md font-light mb-8 leading-relaxed">
          No journey is currently running. Plan a route in the SafeJourney planner and select{" "}
          <strong className="font-semibold text-foreground">Start Monitored Journey</strong> to activate live tracking and telemetry.
        </p>
        <Link href="/journey">
          <Button className="rounded-full gap-2 px-8 h-12 shadow-lg shadow-primary/20 font-bold">
            <Navigation size={18} /> Plan a Journey
          </Button>
        </Link>
      </div>
    );
  }

  // State: INVALID_JOURNEY / CONNECTION_ERROR
  if (error || !data) {
    const isNotFound = error?.includes("404") || error?.toLowerCase().includes("not found");
    const userFacingMessage = isNotFound
      ? "No active journey was found for this session. The previous journey has either completed or concluded. You can start a new monitored route anytime."
      : "Unable to connect to live monitoring stream. Please check your network connection or try refreshing.";

    return (
      <div className="flex h-screen w-full flex-col items-center justify-center p-6 text-center bg-background">
        <div className="w-16 h-16 rounded-3xl bg-amber-500/10 flex items-center justify-center mb-6 shadow-sm border border-amber-500/20 text-amber-600">
          <AlertTriangle size={36} />
        </div>
        <h2 className="text-2xl font-[family-name:var(--font-jakarta)] font-extrabold text-foreground tracking-tight">
          {isNotFound ? "No Active Journey" : "Connection Issue"}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground max-w-md font-light mb-8 leading-relaxed">
          {userFacingMessage}
        </p>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => {
              clearActiveJourney();
              setResolvedJourneyId(null);
            }}
            className="rounded-full px-6 h-11"
          >
            Clear Active Session
          </Button>
          <Link href="/journey">
            <Button className="rounded-full gap-2 px-6 h-11 shadow-md shadow-primary/20 font-bold">
              <Navigation size={16} /> Plan a New Journey
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // Determine active status and metrics
  const isTracking = tracking.lifecycleState === "TRACKING";
  const isPaused = tracking.lifecycleState === "PAUSED" || (!data.is_active && data.status_summary.status === "paused");
  const isStarting = tracking.lifecycleState === "STARTING";
  const isCompleted = data.status_summary.status === "completed" || tracking.lifecycleState === "COMPLETED";
  const isCancelled = data.status_summary.status === "cancelled" || tracking.lifecycleState === "CANCELLED";

  // Derive genuine telemetry coordinates (prefers browser GPS, falls back to server snapshot, never mock)
  const currentCoords = tracking.latestTelemetry
    ? { lat: tracking.latestTelemetry.lat, lng: tracking.latestTelemetry.lng }
    : data.current_location && Number.isFinite(data.current_location.lat) && Number.isFinite(data.current_location.lng)
    ? { lat: data.current_location.lat, lng: data.current_location.lng }
    : null;

  // Real or derived progress
  const progressPct = tracking.serverProgress
    ? tracking.serverProgress.progressPercentage
    : data.status_summary.progress_percentage || 0;

  const distanceRemaining = tracking.serverProgress
    ? tracking.serverProgress.distanceRemainingM
    : data.status_summary.distance_remaining || 0;

  const currentSegment = tracking.serverProgress
    ? tracking.serverProgress.statusLabel
    : data.status_summary.current_segment || "En Route";

  // Handle lifecycle actions
  const handlePause = async () => {
    await tracking.pauseTracking();
    refetch();
  };

  const handleResume = async () => {
    await tracking.resumeTracking();
    refetch();
  };

  const handleComplete = async () => {
    await tracking.completeTracking();
    clearActiveJourney();
    refetch();
  };

  const handleCancel = async () => {
    await tracking.cancelTracking();
    clearActiveJourney();
    refetch();
  };

  const handleStartMonitoring = async () => {
    if (resolvedJourneyId) {
      await tracking.startTracking(resolvedJourneyId);
      refetch();
    }
  };

  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12">
      {/* Left Panel: Telemetry & Agent Status */}
      <aside className="relative z-10 flex h-full flex-col border-r border-border bg-card/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] backdrop-blur-3xl lg:col-span-5 dark:shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
        <div className="flex shrink-0 flex-col p-6 border-b border-border/30">
          <div className="flex items-center justify-between">
            <h1 className="font-[family-name:var(--font-jakarta)] text-2xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
              <Radio size={24} className="text-primary animate-pulse" /> Live Monitor
            </h1>
            
            {/* Status Badges */}
            {isTracking ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full text-xs font-bold uppercase tracking-wider border border-emerald-500/20">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Streaming GPS
              </div>
            ) : isPaused ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-amber-500/10 text-amber-600 rounded-full text-xs font-bold uppercase tracking-wider border border-amber-500/20">
                <Pause size={12} /> Paused
              </div>
            ) : isCompleted ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-bold uppercase tracking-wider border border-primary/20">
                <CheckCircle2 size={12} /> Completed
              </div>
            ) : isCancelled ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-destructive/10 text-destructive rounded-full text-xs font-bold uppercase tracking-wider border border-destructive/20">
                <Square size={12} /> Cancelled
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1 bg-secondary text-muted-foreground rounded-full text-xs font-bold uppercase tracking-wider">
                Planned
              </div>
            )}
          </div>
        </div>

        <ScrollArea className="flex-1 p-6">
          <div className="flex flex-col gap-6">
            {/* Permission / Stale Warnings */}
            {tracking.permissionError && (
              <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
                <div className="space-y-1">
                  <p className="font-bold">Location Permission Required</p>
                  <p className="text-[11px] opacity-90 leading-relaxed">{tracking.permissionError}</p>
                </div>
              </div>
            )}

            {tracking.isStale && isTracking && (
              <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span className="font-semibold text-[11px]">GPS signal has not updated in over 60 seconds.</span>
              </div>
            )}

            {/* Ready-to-connect Banner for already started journeys */}
            {!isTracking && !isPaused && !isCompleted && !isCancelled && (
              <div className="glass-card rounded-3xl p-5 border-primary/30 bg-primary/5 space-y-3">
                <div className="flex items-center gap-2 text-primary font-bold text-sm">
                  <Radio size={16} className="animate-pulse" />
                  <span>Connect Device Telemetry</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Journey is active on the server. Connect your browser&apos;s GPS to stream authentic real-time coordinates.
                </p>
                <Button
                  onClick={handleStartMonitoring}
                  disabled={isStarting}
                  className="w-full h-10 rounded-xl font-bold gap-2 text-xs shadow-md shadow-primary/20"
                >
                  <Play size={14} className="fill-current" />
                  <span>{isStarting ? "Requesting Location..." : "Start Streaming Telemetry"}</span>
                </Button>
              </div>
            )}

            {/* Environmental Safety Proxy Score */}
            <div className="glass-card flex flex-col rounded-3xl p-6 bg-secondary/10 relative overflow-hidden group border border-border/50">
              <div className="flex items-center justify-between">
                <div className="flex flex-col z-10">
                  <span className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">
                    Safety Score
                  </span>
                  <span className={`text-sm font-semibold flex items-center gap-1 mt-1 ${
                    data.safety_score.current && data.safety_score.current >= 70 ? 'text-emerald-500' : 'text-amber-500'
                  }`}>
                    <ShieldCheck size={16} /> Risk Level: {data.safety_score.risk_level || "Calculated"}
                  </span>
                  <span className="text-xs text-muted-foreground mt-0.5">Trend: {data.safety_score.trend || "Stable"}</span>
                </div>
                <div className="flex flex-col items-end z-10">
                  {data.safety_score.current != null ? (
                    <span className={`text-5xl font-black ${
                      data.safety_score.current >= 70 ? 'text-emerald-500' : 'text-amber-500'
                    }`}>
                      {Math.round(data.safety_score.current)}
                      <span className="text-2xl opacity-70">/100</span>
                    </span>
                  ) : (
                    <span className="text-xs font-bold text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-lg">
                      Unavailable
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-border/40 text-[10px] text-muted-foreground/80 leading-tight">
                * Environmental safety risk proxy derived from OSM infrastructure tags. Does not measure active crime probability.
              </div>
            </div>

            {/* AI Recommendation Card */}
            <AnimatePresence mode="wait">
              <motion.div
                key={data.ai_recommendation.recommendation}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="glass-card flex flex-col gap-3 rounded-3xl border-primary/20 bg-primary/5 p-6 relative overflow-hidden"
              >
                <div className="flex items-center gap-2 relative z-10 mb-1">
                  <Activity size={18} className="text-primary animate-pulse" />
                  <span className="font-[family-name:var(--font-jakarta)] text-sm font-bold text-foreground uppercase tracking-wider">
                    Agent Intelligence
                  </span>
                </div>
                <h3 className="font-bold text-base text-primary relative z-10 leading-tight">
                  {data.ai_recommendation.recommendation}
                </h3>
                <p className="text-xs font-medium leading-relaxed text-muted-foreground relative z-10">
                  {data.ai_recommendation.reason}
                </p>

                {data.ai_recommendation.warnings && data.ai_recommendation.warnings.map((w, idx) => (
                  <div key={idx} className="flex items-start gap-2 mt-1 pt-2 border-t border-primary/10 text-amber-600 dark:text-amber-400 text-xs font-semibold relative z-10">
                    <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </div>
                ))}
              </motion.div>
            </AnimatePresence>

            {/* Agent Timeline */}
            <div className="flex flex-col">
              <div className="flex items-center gap-2 mb-4 px-2">
                <Radio size={16} className="text-muted-foreground" />
                <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-xs uppercase tracking-wider text-muted-foreground">
                  Action Feed
                </h3>
              </div>

              <div id="agent-timeline-scroll" className="glass-card rounded-3xl p-5 h-[200px] overflow-y-auto flex flex-col gap-3.5 relative border border-border/50">
                {data.agent_timeline && data.agent_timeline.length > 0 ? (
                  data.agent_timeline.map((item) => (
                    <div key={item.id} className="relative flex items-start gap-3 z-10">
                      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary border border-border text-primary shadow-xs mt-0.5">
                        <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-xs font-medium text-foreground truncate">{item.action}</span>
                        <span className="text-[10px] text-muted-foreground">{item.time}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-xs text-muted-foreground">
                    Awaiting telemetry updates...
                  </div>
                )}
              </div>
            </div>

            {/* Lifecycle Controls */}
            <div className="flex flex-col gap-3 pt-2 pb-6">
              {isTracking ? (
                <div className="grid grid-cols-3 gap-2">
                  <Button variant="outline" size="sm" onClick={handlePause} className="rounded-xl h-10 text-xs font-bold gap-1.5">
                    <Pause size={14} /> Pause
                  </Button>
                  <Button size="sm" onClick={handleComplete} className="rounded-xl h-10 text-xs font-bold gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs">
                    <CheckCircle2 size={14} /> Complete
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleCancel} className="rounded-xl h-10 text-xs font-bold gap-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                    <Square size={14} /> Stop
                  </Button>
                </div>
              ) : isPaused ? (
                <div className="grid grid-cols-2 gap-2">
                  <Button size="sm" onClick={handleResume} className="rounded-xl h-10 text-xs font-bold gap-1.5 shadow-xs">
                    <Play size={14} className="fill-current" /> Resume
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleCancel} className="rounded-xl h-10 text-xs font-bold gap-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                    <Square size={14} /> Stop
                  </Button>
                </div>
              ) : (isCompleted || isCancelled) ? (
                <Link href="/journey">
                  <Button className="w-full rounded-xl h-11 text-xs font-bold gap-2">
                    <RotateCcw size={14} /> Plan Another Journey
                  </Button>
                </Link>
              ) : null}

              {/* Emergency SOS Button */}
              <Link href="/emergency">
                <Button className="h-11 w-full rounded-xl bg-red-600 hover:bg-red-700 text-white gap-2 font-bold shadow-lg shadow-red-600/20 text-xs">
                  <AlertOctagon size={16} /> Trigger SOS Emergency
                </Button>
              </Link>
            </div>
          </div>
        </ScrollArea>
      </aside>

      {/* Right Panel: Progress & Map */}
      <main className="relative flex flex-col h-full w-full bg-background lg:col-span-7">
        {/* Top Overlay HUD */}
        <div className="absolute top-4 left-4 right-4 z-20 flex flex-col gap-3 pointer-events-none">
          {/* Progress Bar HUD */}
          <div className="glass-card rounded-2xl p-4 flex flex-col gap-2.5 pointer-events-auto border border-border/80 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status / Milestone</span>
                <span className="text-xs font-extrabold text-foreground truncate max-w-[200px]">{currentSegment}</span>
              </div>
              <div className="flex items-center gap-4 text-right">
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Remaining</span>
                  <span className="text-xs font-bold flex items-center gap-1 justify-end">
                    <MapPin size={12} />
                    {distanceRemaining >= 1000
                      ? `${(distanceRemaining / 1000).toFixed(1)} km`
                      : `${Math.round(distanceRemaining)} m`}
                  </span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">ETA</span>
                  <span className="text-xs font-bold flex items-center gap-1 justify-end">
                    <Clock size={12} /> {Math.ceil(data.status_summary.eta / 60)} min
                  </span>
                </div>
              </div>
            </div>

            <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary/50">
              <motion.div
                className="absolute left-0 top-0 h-full bg-primary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </div>

          {/* Environment Summary HUD */}
          {data.environment_summary && (
            <div className="flex gap-2 pointer-events-auto overflow-x-auto pb-1">
              <EnvironmentPill icon={CloudRain} label="Weather" value={data.environment_summary.weather_condition || "Clear"} />
              <EnvironmentPill icon={Eye} label="Visibility" value={data.environment_summary.visibility || "Normal"} />
              <EnvironmentPill icon={Sun} label="Lighting" value={data.environment_summary.lighting || "Optimal"} />
              <EnvironmentPill icon={Users} label="Crowds" value={data.environment_summary.crowd_density || "Moderate"} />
            </div>
          )}
        </div>

        {/* Live Tracking Map */}
        <div className="flex-1 w-full h-full relative z-0">
          <SafeMap
            routeGeometry={data.current_route?.geometry}
            liveLocation={currentCoords}
          />
        </div>
      </main>
    </div>
  );
}

function EnvironmentPill({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="glass-card flex items-center gap-2 rounded-xl px-3 py-1.5 bg-background/80 backdrop-blur-md border border-border/50 shadow-xs">
      <Icon size={13} className="text-muted-foreground shrink-0" />
      <div className="flex flex-col">
        <span className="text-[8px] uppercase font-bold tracking-widest text-muted-foreground leading-none mb-0.5">{label}</span>
        <span className="text-[11px] font-semibold text-foreground leading-none">{value}</span>
      </div>
    </div>
  );
}

function LiveMonitorSkeleton() {
  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12 animate-pulse">
      <aside className="border-r border-border bg-card/60 lg:col-span-5 p-6 flex flex-col gap-6">
        <div className="h-8 w-48 bg-secondary rounded-xl mb-4"></div>
        <div className="h-32 bg-secondary/50 rounded-3xl"></div>
        <div className="h-48 bg-secondary/50 rounded-3xl"></div>
        <div className="flex-1 bg-secondary/30 rounded-3xl"></div>
      </aside>
      <main className="lg:col-span-7 bg-secondary/20 p-6 flex flex-col gap-4">
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
        <div className="h-10 w-3/4 bg-secondary/50 rounded-xl"></div>
        <div className="flex-1 rounded-3xl"></div>
      </main>
    </div>
  );
}

export default function LiveMonitorPage() {
  return (
    <Suspense fallback={<LiveMonitorSkeleton />}>
      <LiveMonitorContent />
    </Suspense>
  );
}