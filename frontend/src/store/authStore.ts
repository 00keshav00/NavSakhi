import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "../types/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  
  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      login: (user, token) => set({ user, accessToken: token, isAuthenticated: true }),
      
      logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
    }),
    {
      name: "safeshe-auth-storage", // localStorage key
      // We only persist the auth state, not everything
    }
  )
);
