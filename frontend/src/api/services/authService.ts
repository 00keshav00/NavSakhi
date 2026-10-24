import { apiClient, StandardResponse } from "../client";
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
      const apiMessage = error.response?.data?.error?.message || error.response?.data?.message;
      if (apiMessage) {
        throw new Error(apiMessage);
      }
      throw new Error(error.message || "An unexpected network error occurred during login.");
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
      if (error.response?.status === 409) {
        throw new Error("An account with this email address already exists.");
      }
      if (error.response?.status === 503) {
        throw new Error("Database configuration unavailable. Account creation requires a configured database. Please continue exploring as a guest.");
      }
      const apiMessage = error.response?.data?.error?.message || error.response?.data?.message;
      if (apiMessage) {
        throw new Error(apiMessage);
      }
      throw new Error(error.message || "An unexpected network error occurred during registration.");
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
      const apiMessage = error.response?.data?.error?.message || error.response?.data?.message;
      if (apiMessage) {
        throw new Error(apiMessage);
      }
      throw new Error(error.message || "Unable to complete development test-user login.");
    }
  },
};
