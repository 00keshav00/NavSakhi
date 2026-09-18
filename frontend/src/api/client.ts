import axios from "axios";

export interface StandardResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

// This creates a reusable Axios instance.
// When your backend team finishes the FastAPI server, it will likely run on port 8000.
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000, // 60s timeout
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use((config) => {
  // We need to dynamically import the store to avoid circular dependencies during initialization
  // For client side, we can read from localStorage or Zustand state
  // We'll use the safe approach for Zustand outside React
  try {
    // Attempt to get token from localStorage directly since Zustand persists it
    const storageData = localStorage.getItem("safeshe-auth-storage");
    if (storageData) {
      const parsedData = JSON.parse(storageData);
      const token = parsedData?.state?.accessToken;
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
  } catch (e) {
    // Ignore localStorage errors during SSR
  }
  
  // For Phase 1 fallback / dummy authentication if no token is found
  if (config.headers && !config.headers.Authorization) {
    config.headers["x-user-id"] = "123456789012345678901234";
  }
  
  return config;
});

// Response interceptor for basic error handling & 401s
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Future: Handle token refresh or redirect to login
      console.warn("Unauthorized access detected (401)");
    }
    
    // Basic error logging
    if (error.response?.status !== 404) {
        console.error("API Error:", error.response?.data?.message || error.message || error);
    }
    return Promise.reject(error);
  }
);