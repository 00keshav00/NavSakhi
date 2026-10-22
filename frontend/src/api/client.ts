import axios from "axios";

export interface StandardResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const normalizedBaseUrl = rawBaseUrl.endsWith("/") ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

// This creates a reusable Axios instance.
export const apiClient = axios.create({
  baseURL: normalizedBaseUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000, // 60s timeout
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use((config) => {
  try {
    let token: string | null = null;
    if (typeof window !== "undefined") {
      const storageData = localStorage.getItem("safeshe-auth-storage");
      if (storageData) {
        try {
          const parsedData = JSON.parse(storageData);
          token = parsedData?.state?.accessToken || null;
        } catch {
          token = null;
        }
      }
      // Cookie fallback in case of storage desync
      if (!token && typeof document !== "undefined") {
        const match = document.cookie.match(/(?:^|;\s*)navsakhi_token=([^;]+)/) || document.cookie.match(/(?:^|;\s*)safeshe_token=([^;]+)/);
        if (match) {
          token = decodeURIComponent(match[1]);
        }
      }
    }
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Ignore storage/cookie parsing errors during SSR
  }
  
  return config;
});

// Response interceptor for basic error handling & 401s
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      try {
        if (typeof window !== "undefined") {
          localStorage.removeItem("safeshe-auth-storage");
          if (typeof document !== "undefined") {
            document.cookie = "safeshe_token=; path=/; max-age=0; SameSite=Lax";
            document.cookie = "navsakhi_token=; path=/; max-age=0; SameSite=Lax";
          }
        }
      } catch {
        // Ignore storage errors
      }
    }
    
    // Suppress console.error on expected unauthenticated / not-found states
    if (error.response?.status !== 404 && error.response?.status !== 401) {
      console.error("API Error:", error.response?.data?.error?.message || error.response?.data?.message || error.message || error);
    }
    return Promise.reject(error);
  }
);