import { useState, useRef, useCallback } from "react";
import { journeyService } from "../api/services/journeyService";
import { useAuthStore } from "../store/authStore";
import { JourneyCreateRequest, JourneyPlanResponse } from "../types/journey";
import { toast } from "sonner";

export type JourneyPlannerStatus = "IDLE" | "LOADING" | "SUCCESS" | "EMPTY" | "ERROR";

export const useJourney = () => {
  const [data, setData] = useState<JourneyPlanResponse | null>(null);
  const [status, setStatus] = useState<JourneyPlannerStatus>("IDLE");
  const [error, setError] = useState<string | null>(null);

  // Monotonically increasing request counter to reject stale out-of-order asynchronous responses
  const requestIdRef = useRef<number>(0);

  const planJourney = useCallback(async (request: JourneyCreateRequest) => {
    const currentRequestId = ++requestIdRef.current;
    setStatus("LOADING");
    setError(null);

    try {
      const responseData = await journeyService.planJourney(request);

      // If a newer search was submitted in the meantime, ignore this stale response
      if (currentRequestId !== requestIdRef.current) {
        return;
      }

      const routes = responseData?.recommended_routes || [];
      const hasValidGeometry = routes.some(
        (r) =>
          (r.segments && r.segments.length > 0 && r.segments.some((s) => s.polyline?.geometry)) ||
          r.distance !== "0 km"
      );

      if (routes.length === 0 || !hasValidGeometry) {
        setData(responseData);
        setStatus("EMPTY");
        return;
      }

      setData(responseData);
      setStatus("SUCCESS");

      const primaryRoute = routes[0];
      const scoreDesc = primaryRoute?.safety_score != null
        ? `Calculated route with ${Math.round(primaryRoute.safety_score)}/100 environmental safety proxy.`
        : `Calculated route (safety score unavailable: ${primaryRoute?.score_status?.replace(/_/g, " ") || "UNAVAILABLE"}).`;
      toast.success("Route Options Calculated", {
        description: scoreDesc,
      });
    } catch (err: unknown) {
      if (currentRequestId !== requestIdRef.current) {
        return;
      }
      const errorMsg = (err as Error).message || "An unexpected error occurred while planning your journey.";
      setStatus("ERROR");
      setError(errorMsg);
      toast.error("Journey Planning Failed", {
        description: errorMsg,
      });
    }
  }, []);

  const resetJourney = useCallback(() => {
    requestIdRef.current += 1; // Invalidate any in-flight requests
    setData(null);
    setStatus("IDLE");
    setError(null);
  }, []);

  return {
    data,
    status,
    isLoading: status === "LOADING",
    isError: status === "ERROR",
    isEmpty: status === "EMPTY",
    isSuccess: status === "SUCCESS",
    error,
    planJourney,
    resetJourney,
  };
};
