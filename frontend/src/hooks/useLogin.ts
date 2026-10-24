import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authService } from "../api/services/authService";
import { useAuthStore } from "../store/authStore";
import { LoginCredentials } from "../types/auth";
import { toast } from "sonner";

export const useLogin = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.login);

  const login = async (credentials: LoginCredentials, customRedirect?: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await authService.login(credentials);
      
      // Update global auth store (which also synchronizes document.cookie)
      setAuth(response.user, response.access_token);
      
      toast.success("Welcome back!", {
        description: "Successfully authenticated into NavSakhi.",
      });
      
      // Navigate to requested destination or default to /home
      const redirectTarget = customRedirect || searchParams.get("redirect") || "/home";
      // Ensure target is a relative safe path
      const safeTarget = redirectTarget.startsWith("/") ? redirectTarget : "/home";
      router.push(safeTarget);
      
    } catch (err: unknown) {
      const errorMsg = (err as Error).message || "An unexpected error occurred. Please try again.";
      setError(errorMsg);
      toast.error("Authentication Failed", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsTestUser = async (customRedirect?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authService.testUserLogin();
      setAuth(response.user, response.access_token);
      toast.success("Test Account Authenticated", {
        description: "Logged in as local development test user.",
      });
      const redirectTarget = customRedirect || searchParams.get("redirect") || "/home";
      const safeTarget = redirectTarget.startsWith("/") ? redirectTarget : "/home";
      router.push(safeTarget);
    } catch (err: unknown) {
      const errorMsg = (err as Error).message || "Development test-user login failed.";
      setError(errorMsg);
      toast.error("Test Login Failed", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    login,
    loginAsTestUser,
    isLoading,
    error,
  };
};
