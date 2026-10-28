import { useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authService, RegisterCredentials } from "../api/services/authService";
import { useAuthStore } from "../store/authStore";
import { toast } from "sonner";
import { getSafeRedirectUrl } from "../utils/safeRedirect";

export type RegistrationStep = "idle" | "creating_account" | "authenticating" | "initializing_workspace";

export const useRegister = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<RegistrationStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [isTimeoutRecovery, setIsTimeoutRecovery] = useState(false);
  const isSubmittingRef = useRef(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.login);

  const register = async (credentials: RegisterCredentials, customRedirect?: string) => {
    // 1. Guard against duplicate concurrent submissions
    if (isSubmittingRef.current || isLoading) {
      return;
    }
    isSubmittingRef.current = true;
    setIsLoading(true);
    setError(null);
    setIsTimeoutRecovery(false);
    setStep("creating_account");

    try {
      // 2. Execute registration
      const response = await authService.register(credentials);

      let user = response?.user;
      let token = response?.access_token;

      // 3. If backend returned user but no direct session token, execute at most one login attempt
      if (!token && user) {
        setStep("authenticating");
        try {
          const loginResp = await authService.login({
            email: credentials.email,
            password: credentials.password,
          });
          user = loginResp.user;
          token = loginResp.access_token;
        } catch (loginErr) {
          // Account was created, but automatic sign-in failed. Inform user and route to sign-in.
          toast.info("Account Created", {
            description: "Your account was successfully registered. Please sign in with your email and password to access your workspace.",
            duration: 6000,
          });
          const targetParam = customRedirect || searchParams.get("redirect");
          const safeTarget = targetParam ? `/login?redirect=${encodeURIComponent(targetParam)}` : "/login";
          router.push(safeTarget);
          return;
        }
      }

      if (user && token) {
        setStep("initializing_workspace");
        // Update global auth store and cookie
        setAuth(user, token);

        toast.success("Account created successfully!", {
          description: "Welcome to NavSakhi — Safer Journeys • Stronger Women.",
        });

        // Refresh server-side router state to ensure middleware has immediate visibility of the new cookies
        router.refresh();
        const targetParam = customRedirect || searchParams.get("redirect");
        const safeTarget = getSafeRedirectUrl(targetParam, "/home");
        router.push(safeTarget);
      } else {
        throw new Error("Unable to establish secure session after account creation. Please sign in manually.");
      }
    } catch (err: unknown) {
      const errorObj = err as Error & { isTimeout?: boolean; isDuplicate?: boolean; email?: string };
      const errorMsg = errorObj.message || "An unexpected error occurred during registration.";
      setError(errorMsg);

      if (errorObj.isTimeout) {
        setIsTimeoutRecovery(true);
        toast.error("Server Response Delayed", {
          description: errorMsg,
          duration: 8000,
          action: {
            label: "Try Sign In",
            onClick: () => router.push(`/login?email=${encodeURIComponent(credentials.email)}`),
          },
        });
      } else if (errorObj.isDuplicate) {
        setIsTimeoutRecovery(true);
        toast.info("Account Already Exists", {
          description: errorMsg,
          duration: 7000,
          action: {
            label: "Sign In",
            onClick: () => router.push(`/login?email=${encodeURIComponent(credentials.email)}`),
          },
        });
      } else {
        toast.error("Registration Notice", {
          description: errorMsg,
        });
      }
    } finally {
      setIsLoading(false);
      setStep("idle");
      isSubmittingRef.current = false;
    }
  };

  return {
    register,
    isLoading,
    step,
    error,
    isTimeoutRecovery,
  };
};
