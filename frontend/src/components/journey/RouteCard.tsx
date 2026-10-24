"use client";

import { MultimodalRoute } from "@/types/journey";
import { RouteScoreBadge } from "./RouteScoreBadge";
import { Footprints, Train, Bus, Car, Bike, ChevronRight, Check, Moon, Camera, AlertTriangle } from "lucide-react";

import { motion } from "framer-motion";

interface RouteCardProps {
  route: MultimodalRoute;
  isSelected: boolean;
  onSelect: (routeId: string) => void;
  onViewDetails?: (routeId: string) => void;
}

export function RouteCard({
  route,
  isSelected,
  onSelect,
  onViewDetails,
}: RouteCardProps) {
  const getModeIcon = (mode: string) => {
    const m = mode.toLowerCase();
    if (m.includes("walk") || m.includes("foot")) return <Footprints className="w-3.5 h-3.5" />;
    if (m.includes("metro") || m.includes("train") || m.includes("rail") || m.includes("mrts") || m.includes("suburban")) {
      return <Train className="w-3.5 h-3.5" />;
    }
    if (m.includes("bus")) return <Bus className="w-3.5 h-3.5" />;
    if (m.includes("bike") || m.includes("two_wheeler") || m.includes("scooter")) {
      return <Bike className="w-3.5 h-3.5" />;
    }
    return <Car className="w-3.5 h-3.5" />;
  };

  const handleClick = () => {
    onSelect(route.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(route.id);
    }
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(route.id);
    onViewDetails?.(route.id);
  };

  return (
    <motion.div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`${route.route_name || route.mode || "Route"}, ETA ${route.eta}, distance ${route.distance}${isSelected ? ", currently selected" : ""}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.99 }}
      transition={{ duration: 0.2 }}
      className={`group relative rounded-xl border p-4 transition-colors duration-200 cursor-pointer text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        isSelected
          ? "bg-card border-primary ring-2 ring-primary/25 shadow-md shadow-primary/5"
          : "bg-card/80 hover:bg-card border-border hover:border-primary/40 hover:shadow-sm"
      }`}
    >
      {/* Top Header: Route Title + ETA */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-bold text-foreground text-sm tracking-tight truncate">
              {route.route_name || route.mode || "Alternative Route"}
            </h4>
            {isSelected && (
              <span className="inline-flex items-center gap-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary text-primary-foreground">
                <Check className="w-3 h-3" /> Selected
              </span>
            )}
          </div>

          {/* Sequential Mode Chain */}
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap text-xs text-muted-foreground font-medium">
            {route.segments && route.segments.length > 0 ? (
              route.segments.map((seg, idx) => (
                <div key={idx} className="flex items-center gap-1">
                  <span className="p-1 rounded bg-secondary text-foreground">
                    {getModeIcon(seg.transport_mode)}
                  </span>
                  <span className="capitalize text-[11px]">{seg.transport_mode}</span>
                  {idx < route.segments.length - 1 && (
                    <span className="text-muted-foreground/60 text-[10px]">→</span>
                  )}
                </div>
              ))
            ) : (
              <span className="capitalize">{route.travel_mode_chain || route.mode}</span>
            )}
          </div>
        </div>

        {/* ETA, Distance & Fare Provenance */}
        <div className="text-right shrink-0">
          <div className="text-lg font-black text-foreground tracking-tight">
            {route.eta}
          </div>
          <div className="text-xs text-muted-foreground font-medium">
            {route.distance}
          </div>
          {route.fare ? (
            <div className="mt-1 flex flex-col items-end">
              <span className={`text-[11px] font-bold ${
                route.fare.fare_type === "OFFICIAL_FARE"
                  ? "text-emerald-500 dark:text-emerald-400"
                  : route.fare.fare_type === "METERED_VARIABLE"
                  ? "text-sky-500 dark:text-sky-400"
                  : "text-foreground/80"
              }`}>
                {route.fare.display_text}
              </span>
              <span className="text-[9.5px] text-muted-foreground font-medium">
                {route.fare.fare_type === "OFFICIAL_FARE"
                  ? "Official fare"
                  : route.fare.fare_type === "ESTIMATED_FARE"
                  ? "Estimated"
                  : route.fare.fare_type === "METERED_VARIABLE"
                  ? "Metered"
                  : route.fare.fare_type === "NOT_APPLICABLE"
                  ? "Personal vehicle"
                  : "Fare unavailable"}
              </span>
            </div>
          ) : route.cost ? (
            <div className="text-[11px] font-bold text-foreground/80 mt-0.5">
              {route.cost}
            </div>
          ) : null}
        </div>
      </div>

      {/* Safety Score Section */}
      <div className="mt-3 pt-3 border-t border-border/60 flex flex-col gap-2">
        <RouteScoreBadge
          score={route.safety_score}
          scoreStatus={route.score_status}
          coverageRatio={route.scoreable_coverage_ratio}
          size="sm"
          showCoverage={true}
        />

        {route.night_activity_score && route.night_activity_score.status !== "OUT_OF_BOUNDS" && (
          <div className="flex items-center justify-between text-xs pt-1 border-t border-border/40">
            <div className="flex items-center gap-1.5 text-muted-foreground font-medium">
              <Moon className="w-3.5 h-3.5 text-indigo-500" />
              <span>Night Activity Index:</span>
              <span className="font-bold text-foreground">
                {Math.round(route.night_activity_score.normalized_score ?? route.night_activity_score.overall_score)}
              </span>
              <span className="text-[10px] text-muted-foreground">
                (raw {Math.round(route.night_activity_score.overall_score)})
              </span>
            </div>

            <div className="flex items-center gap-1">
              {route.night_activity_score.concern_level === "HIGH_CONCERN" && (
                <span className="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                  <AlertTriangle className="w-2.5 h-2.5" /> High Concern
                </span>
              )}
              {route.night_activity_score.concern_level === "LIMITED_INDICATORS" && (
                <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                  Limited Indicators
                </span>
              )}
              {route.night_activity_score.surveillance_cameras_count && route.night_activity_score.surveillance_cameras_count > 0 ? (
                <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold px-1.5 py-0.5 rounded bg-secondary text-muted-foreground border border-border">
                  <Camera className="w-2.5 h-2.5" /> {route.night_activity_score.surveillance_cameras_count}
                </span>
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Footer: Ranking Badges & Detail Button */}
      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          {route.ranking_labels && route.ranking_labels.length > 0 ? (
            route.ranking_labels.map((label, i) => (
              <span
                key={i}
                className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-secondary text-foreground border border-border"
              >
                {label}
              </span>
            ))
          ) : route.is_recommended ? (
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
              Recommended
            </span>
          ) : null}
        </div>

        <button
          type="button"
          onClick={handleDetailsClick}
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary/80 transition-colors py-1 px-1.5 rounded-md hover:bg-primary/5"
        >
          <span>Details</span>
          <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
}
