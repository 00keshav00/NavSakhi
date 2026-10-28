import axios from "axios";

export interface StandardResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

/**
 * Resolves the backend API base URL with defensive multi-environment fallback.
 * 
 * Precedence:
 * 1. Explicit `NEXT_PUBLIC_API_URL` environment variable (if defined at build or runtime).
 * 2. Client-side browser runtime inspection:
 *    - If running on `nav-sakhi.vercel.app` or any remote hostname (not localhost / 127.0.0.1):
 *      Defaults to the authoritative production/staging Render backend:
 *      `https://navsakhi-api-staging.onrender.com`
 * 3. Local development fallback: `http://localhost:8000`.
 */
export function resolveApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (typeof envUrl === "string" && envUrl.trim().length > 0) {
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    // If the configured URL is the obsolete/dormant un-suffixed Render service,
    // automatically migrate to the authoritative staging service for Phase 51.
    if (trimmed === "https://navsakhi-api.onrender.com" || trimmed === "http://navsakhi-api.onrender.com") {
      return "https://navsakhi-api-staging.onrender.com";
    }
    return trimmed;
  }

  // Client-side browser execution fallback for deployed frontends
  if (typeof window !== "undefined" && window.location?.hostname) {
    const host = window.location.hostname.toLowerCase();
    if (host !== "localhost" && host !== "127.0.0.1" && host !== "0.0.0.0") {
      return "https://navsakhi-api-staging.onrender.com";
    }
  }

  return "http://localhost:8000";
}

// This creates a reusable Axios instance with dynamic base URL resolution.
export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000, // 60s timeout
});

// Request interceptor to attach JWT token and ensure valid remote baseURL in browser
apiClient.interceptors.request.use((config) => {
  try {
    if (typeof window !== "undefined") {
      // Dynamically repair baseURL if it defaulted to localhost or the legacy dormant service on a remote host
      const currentBase = config.baseURL || apiClient.defaults.baseURL || "";
      if (
        (!currentBase ||
          currentBase.includes("localhost") ||
          currentBase.includes("127.0.0.1") ||
          currentBase === "https://navsakhi-api.onrender.com" ||
          currentBase === "http://navsakhi-api.onrender.com") &&
        window.location.hostname !== "localhost" &&
        window.location.hostname !== "127.0.0.1"
      ) {
        const resolved = resolveApiBaseUrl();
        config.baseURL = resolved;
        apiClient.defaults.baseURL = resolved;
      }
    }

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

/**
 * Safely extracts a user-facing error message from an unknown error,
 * prioritizing FastAPI's `detail` field, nested API envelope errors,
 * top-level response messages, and standard Error.message.
 */
export function extractApiErrorMessage(
  error: unknown,
  fallback: string = "An unexpected error occurred."
): string {
  if (!error) return fallback;

  // 0. If input error is already a non-empty string
  if (typeof error === "string" && error.trim().length > 0) {
    return error.trim();
  }

  const errObj = error as {
    response?: {
      data?: {
        detail?: unknown;
        error?: { message?: unknown };
        message?: unknown;
      };
    };
    message?: unknown;
  };

  const data = errObj?.response?.data;

  // 1. FastAPI detail field (string or validation array)
  if (data?.detail !== undefined && data?.detail !== null) {
    if (typeof data.detail === "string" && data.detail.trim().length > 0) {
      return data.detail.trim();
    }
    if (Array.isArray(data.detail) && data.detail.length > 0) {
      const messages = data.detail
        .map((item) => {
          if (typeof item === "string" && item.trim().length > 0) return item.trim();
          if (item && typeof item === "object" && typeof (item as { msg?: unknown }).msg === "string") {
            const locArr = Array.isArray((item as { loc?: unknown[] }).loc)
              ? (item as { loc: unknown[] }).loc.filter((l) => l !== "body")
              : [];
            const locStr = locArr.join(".");
            const msgStr = (item as { msg: string }).msg.trim();
            return locStr ? `${locStr}: ${msgStr}` : msgStr;
          }
          return null;
        })
        .filter((msg): msg is string => Boolean(msg && msg.length > 0));

      if (messages.length > 0) {
        return messages.join("; ");
      }
    }
    if (typeof data.detail === "object" && data.detail !== null) {
      const nestedMsg = (data.detail as { message?: unknown }).message;
      if (typeof nestedMsg === "string" && nestedMsg.trim().length > 0) {
        return nestedMsg.trim();
      }
    }
  }

  // 2. Nested error envelope (e.g. StandardResponse format: { error: { message: "..." } })
  if (typeof data?.error?.message === "string" && data.error.message.trim().length > 0) {
    return data.error.message.trim();
  }

  // 3. Top-level response message (e.g. { message: "..." })
  if (typeof data?.message === "string" && data.message.trim().length > 0) {
    return data.message.trim();
  }

  // 4. Standard JavaScript / Axios Error.message
  if (typeof errObj?.message === "string" && errObj.message.trim().length > 0) {
    const msg = errObj.message.trim();
    if (msg.toLowerCase() === "network error") {
      return "Unable to connect to the NavSakhi backend service. The server may be waking up from sleep. Please try again in a few moments.";
    }
    if (msg !== "[object Object]") {
      return msg;
    }
  }

  // 5. Fallback
  return fallback;
}

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
    
    // Suppress console.error on intentional cancellations, and expected unauthenticated / not-found states
    const isCanceled = axios.isCancel(error) || error?.code === "ERR_CANCELED" || error?.name === "CanceledError";
    if (!isCanceled && error.response?.status !== 404 && error.response?.status !== 401) {
      console.error("API Error:", extractApiErrorMessage(error));
    }
    return Promise.reject(error);
  }
);