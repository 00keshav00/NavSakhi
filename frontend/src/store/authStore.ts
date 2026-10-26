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
  updateUser: (updatedUser: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      login: (user, token) => {
        if (typeof document !== "undefined") {
          document.cookie = `navsakhi_token=${token}; path=/; max-age=86400; SameSite=Lax`;
          document.cookie = `safeshe_token=${token}; path=/; max-age=86400; SameSite=Lax`;
        }
        set({ user, accessToken: token, isAuthenticated: true });
      },
      
      logout: () => {
        if (typeof document !== "undefined") {
          document.cookie = "navsakhi_token=; path=/; max-age=0; SameSite=Lax";
          document.cookie = "safeshe_token=; path=/; max-age=0; SameSite=Lax";
        }
        set({ user: null, accessToken: null, isAuthenticated: false });
      },

      updateUser: (updatedUser) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...updatedUser } : null,
        }));
      },
    }),
    {
      name: "safeshe-auth-storage", // localStorage key
      // We only persist the auth state, not everything
    }
  )
);

