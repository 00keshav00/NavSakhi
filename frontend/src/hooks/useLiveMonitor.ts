import { useState, useEffect, useCallback } from "react";
import { liveMonitorService } from "../api/services/liveMonitorService";
import { LiveMonitorResponse } from "../types/liveMonitor";

export const useLiveMonitor = (journeyId: string | null) => {
  const [data, setData] = useState<LiveMonitorResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!journeyId) return;
    try {
      const responseData = await liveMonitorService.getMonitorStatus(journeyId);
      setData(responseData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to sync live monitor.");
    } finally {
      setIsLoading(false);
    }
  }, [journeyId]);

  // Initial fetch and WebSocket placeholder
  useEffect(() => {
    if (!journeyId) {
      setIsLoading(false);
      return;
    }
    
    // Initial fetch
    fetchStatus();

    // In the future, this is where the WebSocket /api/v1/ws/journey/{journey_id} connection goes.
    // For now, we simulate real-time updates via a 3-second polling interval.
    const interval = setInterval(fetchStatus, 3000);
    
    return () => clearInterval(interval);
  }, [journeyId, fetchStatus]);

  return {
    data,
    isLoading,
    error,
  };
};
