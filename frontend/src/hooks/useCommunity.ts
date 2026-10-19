import { useState, useEffect, useCallback } from "react";
import { communityService } from "../api/services/communityService";
import { CommunityIntelligenceResponse, CommunityReportCreate } from "../types/community";
import { toast } from "sonner";

export const useCommunityIntelligence = (filters: { type: string; verification: string; }) => {
  const [data, setData] = useState<CommunityIntelligenceResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIntelligence = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const responseData = await communityService.getIntelligence(filters);
      setData(responseData);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred loading community intelligence.");
      toast.error("Intelligence Sync Failed", {
        description: err.message,
      });
    } finally {
      setIsLoading(false);
    }
  }, [filters.type, filters.verification]);

  useEffect(() => {
    fetchIntelligence();
  }, [fetchIntelligence]);

  return { data, isLoading, error, refresh: fetchIntelligence };
};

export const useCreateReport = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitReport = async (data: CommunityReportCreate, onSuccess?: () => void) => {
    setIsSubmitting(true);
    try {
      await communityService.createReport(data);
      toast.success("Anomaly Reported", {
        description: "Your report has been submitted to the community verification queue.",
      });
      if (onSuccess) onSuccess();
    } catch (err: any) {
      toast.error("Submission Failed", {
        description: err.message || "Failed to submit anomaly report.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return { submitReport, isSubmitting };
};
