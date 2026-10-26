import { useState, useRef, useCallback } from "react";
import { journeyService } from "../api/services/journeyService";
import { useAuthStore } from "../store/authStore";
import { extractApiErrorMessage } from "../api/client";
import { JourneyCreateRequest, JourneyPlanResponse } from "../types/journey";
import { toast } from "sonner";

export type JourneyPlannerStatus = "IDLE" | "LOADING" | "SUCCESS" | "EMPTY" | "ERROR";

export const useJourney = () => {
  const [data, setData] = useState<JourneyPlanResponse | null>(null);
  const [status, setStatus] = useState<JourneyPlannerStatus>("IDLE");
  const [error, setError] = useState<string | null>(null);

  // Monotonically increasing request counter to reject stale out-of-order asynchronous responses
  const requestIdRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  const planJourney = useCallback(async (request: JourneyCreateRequest) => {
    // Abort any previous pending search request immediately to free network & server resources
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const currentRequestId = ++requestIdRef.current;
    setStatus("LOADING");
    setError(null);

    try {
      const responseData = await journeyService.planJourney(request, controller.signal);

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
      // If request was aborted because user submitted a newer search, silently ignore
      const errName = (err as { name?: string })?.name;
      const isCanceled = errName === "CanceledError" || errName === "AbortError" || (err as { code?: string })?.code === "ERR_CANCELED";
      if (isCanceled || currentRequestId !== requestIdRef.current) {
        return;
      }
      const errorMsg = extractApiErrorMessage(err, "An unexpected error occurred while planning your journey.");
      setStatus("ERROR");
      setError(errorMsg);
      toast.error("Journey Planning Failed", {
        description: errorMsg,
      });
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  }, []);

  const resetJourney = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    requestIdRef.current += 1; // Invalidate any in-flight requests
    setData(null);
    setStatus("IDLE");
    setError(null);
  }, []);

  const restoreJourney = useCallback((responseData: JourneyPlanResponse) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    requestIdRef.current += 1;
    setData(responseData);
    setStatus("SUCCESS");
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
    restoreJourney,
  };
};
