import { useState, useEffect, useCallback } from "react";
import { dashboardService } from "../api/services/dashboardService";
import { DashboardOverviewResponse } from "../types/dashboard";
import { toast } from "sonner";

export const useDashboard = () => {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const responseData = await dashboardService.getOverview();
      setData(responseData);
    } catch (err: any) {
      const errorMsg = err.message || "An unexpected error occurred loading the dashboard.";
      setError(errorMsg);
      toast.error("Dashboard Sync Failed", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return {
    data,
    isLoading,
    error,
    refresh: fetchDashboard,
  };
};
