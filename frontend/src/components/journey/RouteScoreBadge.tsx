"use client";

import { ShieldCheck, ShieldAlert, Info } from "lucide-react";

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
        return "Score Verified";
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
        return "Score Unavailable";
    }
  };

  // Score calibration color and category (for synthetic environmental proxy)
  const getScoreColor = (numericScore: number) => {
    if (numericScore >= 75) {
      return {
        bg: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
        badge: "bg-emerald-500 text-white",
        label: "Higher Relative Safety",
      };
    }
    if (numericScore >= 50) {
      return {
        bg: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
        badge: "bg-amber-500 text-white",
        label: "Moderate Environmental Risk",
      };
    }
    return {
      bg: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20",
      badge: "bg-rose-500 text-white",
      label: "Elevated Environmental Risk",
    };
  };

  const formattedScore = isReady ? (Math.round((score as number) * 10) / 10).toFixed(1) : null;
  const coveragePercent = typeof coverageRatio === "number" && !isNaN(coverageRatio)
    ? Math.round(coverageRatio * 100)
    : null;

  if (isReady && formattedScore !== null) {
    const { bg, label } = getScoreColor(Number(formattedScore));
    return (
      <div className="flex flex-col gap-1">
        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-semibold ${bg} ${size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm"}`}>
          <ShieldCheck className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} />
          <span>Safety Proxy: {formattedScore}/100</span>
          <span className="text-[10px] opacity-75 font-normal ml-1">({label})</span>
        </div>
        {showCoverage && coveragePercent !== null && (
          <div className="text-[11px] text-muted-foreground flex items-center gap-1 pl-0.5">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>{coveragePercent}% scoreable road coverage</span>
          </div>
        )}
      </div>
    );
  }

  // Unavailable / Non-ready status: explicitly render N/A with status reason
  const statusLabel = getStatusLabel(scoreStatus);
  return (
    <div className="flex flex-col gap-1">
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border bg-muted/60 text-muted-foreground border-border font-medium ${size === "sm" ? "text-xs" : size === "lg" ? "text-base" : "text-sm"}`}>
        <ShieldAlert className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} />
        <span>Safety Score: N/A</span>
        <span className="text-[10px] bg-background/80 px-1.5 py-0.5 rounded border border-border/60 ml-1">
          {statusLabel}
        </span>
      </div>
      {showCoverage && coveragePercent !== null && (
        <div className="text-[11px] text-muted-foreground flex items-center gap-1 pl-0.5">
          <Info className="w-3 h-3 text-muted-foreground/70" />
          <span>{coveragePercent}% road coverage {coveragePercent < 70 ? "(below 70% threshold)" : ""}</span>
        </div>
      )}
    </div>
  );
}
