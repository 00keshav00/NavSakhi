import { useState, useEffect, useCallback } from "react";
import { emergencyService } from "../api/services/emergencyService";
import { EmergencyResponse } from "../types/emergency";
import { toast } from "sonner";

export const useEmergencySession = (sessionId: string | null) => {
  const [data, setData] = useState<EmergencyResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!sessionId) return;
    try {
      const responseData = await emergencyService.getEmergencyStatus(sessionId);
      setData(responseData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to sync emergency status.");
      toast.error("Emergency Sync Failed", { description: err.message });
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setData(null);
      return;
    }
    
    setIsLoading(true);
    fetchStatus().finally(() => setIsLoading(false));

    // Polling acts as a placeholder for the future WebSocket implementation.
    const interval = setInterval(fetchStatus, 2500);
    return () => clearInterval(interval);
  }, [sessionId, fetchStatus]);

  return { data, isLoading, error };
};
