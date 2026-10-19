import { useQuery } from "@tanstack/react-query";
import { healthService } from "../api/services/healthService";

export const useHealth = () => {
  return useQuery({
    queryKey: ["health"],
    queryFn: healthService.checkHealth,
    retry: 2,
    refetchInterval: 5000, // Poll every 5 seconds for live status
  });
};
