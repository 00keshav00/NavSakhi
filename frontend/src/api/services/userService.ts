import { apiClient, StandardResponse, extractApiErrorMessage } from "../client";
import { User, EmergencyContact } from "../../types/auth";

export interface ProfileUpdatePayload {
  full_name?: string;
  phone_number?: string;
  age?: number;
}

export interface EmergencyContactInput {
  name: string;
  phone_number: string;
  relationship?: string;
  email?: string;
  is_primary?: boolean;
}

export const userService = {
  getProfile: async (): Promise<User> => {
    try {
      const response = await apiClient.get<StandardResponse<User>>("/api/v1/users/me");
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to fetch user profile.");
      throw new Error(message);
    }
  },

  updateProfile: async (payload: ProfileUpdatePayload): Promise<User> => {
    try {
      const response = await apiClient.patch<StandardResponse<User>>("/api/v1/users/me", payload);
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to update profile.");
      throw new Error(message);
    }
  },

  getEmergencyContacts: async (): Promise<EmergencyContact[]> => {
    try {
      const response = await apiClient.get<StandardResponse<EmergencyContact[]>>("/api/v1/users/me/emergency-contacts");
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to fetch emergency contacts.");
      throw new Error(message);
    }
  },

  addEmergencyContact: async (contact: EmergencyContactInput): Promise<User> => {
    try {
      const response = await apiClient.post<StandardResponse<User>>("/api/v1/users/me/emergency-contacts", contact);
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to add emergency contact.");
      throw new Error(message);
    }
  },

  updateEmergencyContact: async (contactId: string, contact: Partial<EmergencyContactInput>): Promise<User> => {
    try {
      const response = await apiClient.put<StandardResponse<User>>(`/api/v1/users/me/emergency-contacts/${contactId}`, contact);
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to update emergency contact.");
      throw new Error(message);
    }
  },

  deleteEmergencyContact: async (contactId: string): Promise<User> => {
    try {
      const response = await apiClient.delete<StandardResponse<User>>(`/api/v1/users/me/emergency-contacts/${contactId}`);
      return response.data.data;
    } catch (error: any) {
      const message = extractApiErrorMessage(error, "Failed to delete emergency contact.");
      throw new Error(message);
    }
  },
};
