"use client";

import { ShieldCheck, ShieldAlert, Info } from "lucide-react";

/**
 * Strictly monotonic, piecewise linear calibration for user-facing Environmental Guidance Index.
 * Preserves the raw LightGBM continuous model output internally and in explainability disclosures.
 * 
 * Formula:
 * - [0.0, 20.0]  -> [25.0, 50.0] (slope 1.25)
 * - [20.0, 50.0] -> [50.0, 75.0] (slope 0.8333)
 * - [50.0, 100.0]-> [75.0, 97.0] (slope 0.44)
 * 
 * Guarantee: Monotonic (slope > 0 everywhere). Higher raw model output strictly yields higher display index.
 */
export function calculateEnvironmentalIndex(rawScore: number | null | undefined): {
  index: number;
  label: string;
  bg: string;
} | null {
  if (rawScore === null || rawScore === undefined || isNaN(rawScore)) return null;
  const s = Math.max(0.0, Math.min(100.0, rawScore));
  let idx = 25.0;
  if (s <= 20.0) {
    idx = 25.0 + 1.25 * s;
  } else if (s <= 50.0) {
    idx = 50.0 + 0.83333 * (s - 20.0);
  } else {
    idx = 75.0 + 0.44 * (s - 50.0);
  }
  const rounded = Math.round(idx * 10) / 10;
  
  if (rounded >= 75.0) {
    return {
      index: rounded,
      label: "Enhanced Infrastructure Support",
      bg: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
    };
  }
  if (rounded >= 50.0) {
    return {
      index: rounded,
      label: "Standard Infrastructure Support",
      bg: "bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/20",
    };
  }
  return {
    index: rounded,
    label: "Baseline Infrastructure Support",
    bg: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  };
}

interface RouteScoreBadgeProps {
  score: number | null | undefined;
  scoreStatus?: string | null;
  coverageRatio?: number | null;
  size?: "sm" | "md" | "lg";
  showCoverage?: boolean;
}

export function RouteScoreBadge({
  score,
  scoreStatus,
  coverageRatio,
  size = "md",
  showCoverage = true,
}: RouteScoreBadgeProps) {
  const isReady = scoreStatus === "READY" && score !== null && score !== undefined && !isNaN(score);

  // Status human-readable explanation mapping
  const getStatusLabel = (status?: string | null) => {
    switch (status) {
      case "READY":
        return "Environmental Data Verified";
      case "INSUFFICIENT_COVERAGE":
        return "Coverage < 70%";
      case "NO_SCOREABLE_SEGMENTS":
        return "No Scoreable Roads";
      case "UNSUPPORTED_GEOGRAPHY":
        return "Outside Indexed Area";
      case "FEATURE_DATA_UNAVAILABLE":
        return "Features Unavailable";
      case "TRANSIT_UNSCORED":
        return "Transit Rights-of-Way";
      case "PREDICTOR_ERROR":
        return "Model Error";
      default:
        return "Index Unavailable";
    }
  };

  const coveragePercent = typeof coverageRatio === "number" && !isNaN(coverageRatio)
    ? Math.round(coverageRatio * 100)
    : null;

  if (isReady && score !== null && score !== undefined) {
    const calibrated = calculateEnvironmentalIndex(score);
    const rawFormatted = (Math.round(score * 10) / 10).toFixed(1);

    if (calibrated) {
      return (
        <div className="flex flex-col gap-1">
          <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-semibold ${calibrated.bg} ${size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm"}`}>
            <ShieldCheck className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} />
            <span>Environmental Index: {calibrated.index.toFixed(1)}/100</span>
            <span className="text-[10px] opacity-80 font-normal ml-1">({calibrated.label})</span>
          </div>
          {showCoverage && (
            <div className="text-[11px] text-muted-foreground flex items-center justify-between pl-0.5 max-w-sm">
              <span className="flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>{coveragePercent !== null ? `${coveragePercent}% scoreable road coverage` : "Verified road coverage"}</span>
              </span>
              <span className="text-[10px] text-muted-foreground/75" title="Uncalibrated raw prediction output from the frozen LightGBM decision-tree model. Describes physical infrastructure, not personal crime probability.">
                Raw model score: {rawFormatted}/100
              </span>
            </div>
          )}
        </div>
      );
    }
  }

  // Unavailable / Non-ready status: explicitly render N/A with status reason
  const statusLabel = getStatusLabel(scoreStatus);
  return (
    <div className="flex flex-col gap-1">
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border bg-muted/60 text-muted-foreground border-border font-medium ${size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm"}`}>
        <ShieldAlert className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} />
        <span>Environmental Index: N/A</span>
        <span className="text-[10px] bg-background/80 px-1.5 py-0.5 rounded border border-border/60 ml-1">
          {statusLabel}
        </span>
      </div>
      {showCoverage && coveragePercent !== null && (
        <div className="text-[11px] text-muted-foreground flex items-center gap-1 pl-0.5">
          <Info className="w-3 h-3 text-muted-foreground/70" />
          <span>{coveragePercent}% road coverage {coveragePercent < 70 ? "(insufficient road data to provide reliable index)" : ""}</span>
        </div>
      )}
    </div>
  );
}
