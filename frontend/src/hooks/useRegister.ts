import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authService, RegisterCredentials } from "../api/services/authService";
import { useAuthStore } from "../store/authStore";
import { toast } from "sonner";
import { getSafeRedirectUrl } from "../utils/safeRedirect";

export const useRegister = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.login);

  const register = async (credentials: RegisterCredentials, customRedirect?: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authService.register(credentials);

      // Update global auth store (which also synchronizes document.cookie)
      setAuth(response.user, response.access_token);

      toast.success("Account created successfully!", {
        description: "Welcome to NavSakhi — Safer Journeys • Stronger Women.",
      });

      // Navigate to requested destination safely or default to /home
      const targetParam = customRedirect || searchParams.get("redirect");
      const safeTarget = getSafeRedirectUrl(targetParam, "/home");
      router.push(safeTarget);

    } catch (err: unknown) {
      const errorMsg = (err as Error).message || "An unexpected error occurred during registration.";
      setError(errorMsg);
      toast.error("Registration Unsuccessful", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    register,
    isLoading,
    error,
  };
};
