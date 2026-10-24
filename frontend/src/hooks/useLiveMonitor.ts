import { useState, useEffect, useCallback, useRef } from "react";
import { liveMonitorService } from "../api/services/liveMonitorService";
import { LiveMonitorResponse } from "../types/liveMonitor";

export const useLiveMonitor = (journeyId: string | null) => {
  const [data, setData] = useState<LiveMonitorResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(journeyId));
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const fetchStatus = useCallback(async () => {
    if (!journeyId) {
      if (isMountedRef.current) {
        setData(null);
        setError(null);
        setIsLoading(false);
      }
      return;
    }
    try {
      const responseData = await liveMonitorService.getMonitorStatus(journeyId);
      if (isMountedRef.current) {
        setData(responseData);
        setError(null);
      }
    } catch (err: any) {
      if (isMountedRef.current) {
        setError(err.response?.data?.message || err.message || "Failed to load live monitor data.");
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [journeyId]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!journeyId) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
    }, 5000);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [journeyId, fetchStatus]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchStatus,
  };
};
