import { useState } from "react";
import { journeyService } from "../api/services/journeyService";
import { JourneyCreateRequest, JourneyPlanResponse } from "../types/journey";
import { toast } from "sonner";

export const useJourney = () => {
  const [data, setData] = useState<JourneyPlanResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const planJourney = async (request: JourneyCreateRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const responseData = await journeyService.planJourney(request);
      setData(responseData);
      toast.success("Safe Route Calculated", {
        description: `AI recommended route selected with ${responseData.safety_score}% safety score.`,
      });
    } catch (err: any) {
      const errorMsg = err.message || "An unexpected error occurred while planning your journey.";
      setError(errorMsg);
      toast.error("Journey Planning Failed", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const resetJourney = () => {
    setData(null);
    setError(null);
  };

  return {
    data,
    isLoading,
    error,
    planJourney,
    resetJourney
  };
};
