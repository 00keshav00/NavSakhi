import { apiClient, StandardResponse, extractApiErrorMessage } from "../client";
import { AuthResponse, LoginCredentials } from "../../types/auth";

export interface RegisterCredentials {
  fullName: string;
  email: string;
  password: string;
  confirmPassword?: string;
  emergencyContactName?: string;
  emergencyContactRelationship?: string;
  emergencyContactPhone?: string;
  acknowledgedLimitations?: boolean;
}

export const authService = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<StandardResponse<AuthResponse>>("/api/v1/auth/login", {
        email: credentials.email,
        password: credentials.password
      });
      return response.data.data;
    } catch (error: any) {
      if (error.response?.status === 401) {
        throw new Error("Invalid email or password.");
      }
      const apiMessage = extractApiErrorMessage(error, "An unexpected network error occurred during login.");
      throw new Error(apiMessage);
    }
  },

  register: async (credentials: RegisterCredentials): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<StandardResponse<AuthResponse>>("/api/v1/auth/register", {
        full_name: credentials.fullName,
        username: credentials.fullName,
        email: credentials.email,
        password: credentials.password,
        confirm_password: credentials.confirmPassword,
        emergency_contact_name: credentials.emergencyContactName,
        emergency_contact_relationship: credentials.emergencyContactRelationship,
        emergency_contact_phone: credentials.emergencyContactPhone,
        acknowledged_limitations: credentials.acknowledgedLimitations ?? true,
      });
      return response.data.data;
    } catch (error: any) {
      if (error.code === 'ECONNABORTED' || (typeof error.message === 'string' && error.message.includes('timeout')) || error.response?.status === 504) {
        const timeoutErr = new Error("Registration request timed out. The server may have already created your account while processing. Please try signing in with your email and password, or wait a moment.");
        (timeoutErr as any).isTimeout = true;
        (timeoutErr as any).email = credentials.email;
        throw timeoutErr;
      }
      if (error.response?.status === 409) {
        const conflictErr = new Error("An account with this email address already exists. If a previous attempt timed out, your account was likely created successfully. Please sign in below.");
        (conflictErr as any).isDuplicate = true;
        (conflictErr as any).email = credentials.email;
        throw conflictErr;
      }
      if (error.response?.status === 503) {
        throw new Error("Database configuration unavailable. Account creation requires a configured database. Please continue exploring as a guest.");
      }
      const apiMessage = extractApiErrorMessage(error, "An unexpected network error occurred during registration.");
      throw new Error(apiMessage);
    }
  },

  testUserLogin: async (): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<StandardResponse<AuthResponse>>("/api/v1/auth/test-user-login");
      return response.data.data;
    } catch (error: any) {
      if (error.response?.status === 403) {
        throw new Error("Test user login is disabled in production environments.");
      }
      const apiMessage = extractApiErrorMessage(error, "Unable to complete development test-user login.");
      throw new Error(apiMessage);
    }
  },
};
