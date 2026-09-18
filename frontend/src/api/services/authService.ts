import { apiClient, StandardResponse } from "../client";
import { AuthResponse, LoginCredentials } from "../../types/auth";

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    try {
      // The exact URL depends on the backend implementation.
      // We expect POST /api/v1/auth/login
      const response = await apiClient.post<StandardResponse<AuthResponse>>("/api/v1/auth/login", credentials);
      return response.data.data;
    } catch (error: any) {
      // If the backend isn't ready or returns a 404/Network Error, we can gracefully fallback
      // to a mock response so the UI remains testable for Phase 2.
      if (!error.response || error.response.status === 404) {
        console.warn("Backend Auth API not found. Using mock successful login for testing.");
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              access_token: "mock-jwt-access-token-12345",
              refresh_token: "mock-jwt-refresh-token-67890",
              token_type: "bearer",
              user: {
                id: "123456789012345678901234",
                email: credentials.email,
                full_name: "SafeShe User",
                is_active: true,
                role: "user"
              }
            });
          }, 1500); // simulate network delay
        });
      }
      
      // If it's a real 401 Unauthorized, we throw it to the UI
      if (error.response?.status === 401) {
        throw new Error("Invalid email or password");
      }
      
      throw new Error(error.response?.data?.message || "An unexpected error occurred during login");
    }
  },
};
