import { useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "../api/services/authService";
import { useAuthStore } from "../store/authStore";
import { LoginCredentials } from "../types/auth";
import { toast } from "sonner";

export const useLogin = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.login);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await authService.login(credentials);
      
      // Update global auth store
      setAuth(response.user, response.access_token);
      
      // Set a cookie for Next.js middleware route protection
      document.cookie = `safeshe_token=${response.access_token}; path=/; max-age=86400; SameSite=Lax`;
      
      toast.success("Welcome back!", {
        description: "Successfully authenticated into SafeShe.",
      });
      
      // Navigate to protected workspace
      router.push("/home");
      
    } catch (err: any) {
      const errorMsg = err.message || "An unexpected error occurred. Please try again.";
      setError(errorMsg);
      toast.error("Authentication Failed", {
        description: errorMsg,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return {
    login,
    isLoading,
    error,
  };
};
