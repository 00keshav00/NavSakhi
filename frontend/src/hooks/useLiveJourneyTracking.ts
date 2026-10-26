"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { journeyService } from "@/api/services/journeyService";
import { toast } from "sonner";

export type TrackingLifecycleState =
  | "IDLE"
  | "STARTING"
  | "TRACKING"
  | "PAUSED"
  | "COMPLETED"
  | "CANCELLED"
  | "ERROR";

export type GeolocationPermissionState = "prompt" | "granted" | "denied" | "unsupported";

export interface LiveTelemetrySnapshot {
  lat: number;
  lng: number;
  accuracy: number | null;
  timestamp: number;
}

export interface ServerDerivedProgress {
  progressPercentage: number;
  distanceRemainingM: number;
  distanceFromRouteM: number | null;
  isOnRoute: boolean;
  statusLabel: string;
  lastUpdated: string;
}

export interface TelemetryWebSocketPayload {
  type?: string;
  status?: string;
  progress_percentage?: number;
  distance_remaining_m?: number;
  distance_from_route_m?: number | null;
  is_on_route?: boolean;
  status_label?: string;
  timestamp?: string;
  error?: string;
}

export function useLiveJourneyTracking() {
  const [lifecycleState, setLifecycleState] = useState<TrackingLifecycleState>("IDLE");
  const [permissionState, setPermissionState] = useState<GeolocationPermissionState>("prompt");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [latestTelemetry, setLatestTelemetry] = useState<LiveTelemetrySnapshot | null>(null);
  const [serverProgress, setServerProgress] = useState<ServerDerivedProgress | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);

  const activeJourneyIdRef = useRef<string | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastFixTimestampRef = useRef<number>(0);
  const staleCheckTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up all watchers and sockets
  const cleanupTracking = useCallback(() => {
    if (watchIdRef.current !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        // Safe disposal
      }
      wsRef.current = null;
    }
    if (staleCheckTimerRef.current) {
      clearInterval(staleCheckTimerRef.current);
      staleCheckTimerRef.current = null;
    }
    setIsStale(false);
  }, []);

  // Check staleness periodically (stale if no fix received for >60s while tracking)
  useEffect(() => {
    if (lifecycleState === "TRACKING") {
      staleCheckTimerRef.current = setInterval(() => {
        const elapsed = Date.now() - lastFixTimestampRef.current;
        if (lastFixTimestampRef.current > 0 && elapsed > 60000) {
          setIsStale(true);
        } else {
          setIsStale(false);
        }
      }, 5000);
    } else {
      if (staleCheckTimerRef.current) {
        clearInterval(staleCheckTimerRef.current);
        staleCheckTimerRef.current = null;
      }
    }

    return () => {
      if (staleCheckTimerRef.current) {
        clearInterval(staleCheckTimerRef.current);
        staleCheckTimerRef.current = null;
      }
    };
  }, [lifecycleState]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      cleanupTracking();
    };
  }, [cleanupTracking]);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback((data: TelemetryWebSocketPayload) => {
    if (!data || typeof data !== "object") return;

    if (data.type === "telemetry_ack" || data.status === "acknowledged") {
      setServerProgress({
        progressPercentage: typeof data.progress_percentage === "number" ? data.progress_percentage : 0,
        distanceRemainingM: typeof data.distance_remaining_m === "number" ? data.distance_remaining_m : 0,
        distanceFromRouteM: typeof data.distance_from_route_m === "number" ? data.distance_from_route_m : null,
        isOnRoute: data.is_on_route !== false,
        statusLabel: data.status_label || "on_route",
        lastUpdated: data.timestamp || new Date().toISOString(),
      });
      setIsStale(false);
    } else if (data.type === "error" || data.error) {
      console.warn("Journey WS error received:", data.error);
    }
  }, []);

  // Connect to protected WebSocket
  const establishWebSocket = useCallback(
    async (journeyId: string) => {
      try {
        const ws = await journeyService.connectToJourneyWebSocket(
          journeyId,
          (msg: TelemetryWebSocketPayload) => handleWebSocketMessage(msg),
          () => {
            // WS closed
            if (activeJourneyIdRef.current === journeyId && lifecycleState === "TRACKING") {
              console.log("Journey WebSocket disconnected.");
              toast.info("Telemetry Stream Disconnected", {
                description: "Live telemetry connection closed. Reconnecting when connection restores."
              });
            }
          },
          (err: unknown) => {
            console.warn("Journey WebSocket transport error:", err);
            toast.error("Telemetry Transport Error", {
              description: "WebSocket connection error. Real-time server telemetry stream degraded."
            });
          }
        );
        wsRef.current = ws;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "WebSocket connection error";
        console.warn("Could not establish live journey WebSocket stream:", message);
        toast.error("Live Monitoring Stream Unavailable", {
          description: `Could not connect to live WebSocket server: ${message}`
        });
      }

    },
    [handleWebSocketMessage, lifecycleState]
  );

  // Send location update over established WebSocket
  const transmitLocation = useCallback((lat: number, lng: number, accuracy: number | null, timestamp: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = {
        type: "location_update",
        lat,
        lng,
        accuracy,
        timestamp,
      };
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  // Explicit user action to start monitoring
  const startTracking = useCallback(
    async (journeyId: string, selectedRouteId?: string) => {
      if (typeof window === "undefined" || !("geolocation" in navigator)) {
        setPermissionState("unsupported");
        setPermissionError("Geolocation is not supported by your browser.");
        toast.error("Location Tracking Unavailable", {
          description: "Your browser does not support the Geolocation API.",
        });
        return;
      }

      setLifecycleState("STARTING");
      setPermissionError(null);
      activeJourneyIdRef.current = journeyId;

      try {
        // 1. Authenticate and start journey on backend
        await journeyService.startJourney(journeyId, selectedRouteId);

        // 2. Establish single-use ticketed WebSocket connection
        await establishWebSocket(journeyId);

        // 3. Request genuine browser geolocation with explicit user action
        const watchId = navigator.geolocation.watchPosition(
          (pos) => {
            setPermissionState("granted");
            setPermissionError(null);
            setLifecycleState("TRACKING");

            const reading: LiveTelemetrySnapshot = {
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              accuracy: pos.coords.accuracy ?? null,
              timestamp: pos.timestamp || Date.now(),
            };

            lastFixTimestampRef.current = Date.now();
            setLatestTelemetry(reading);
            setIsStale(false);

            // Transmit genuine observation
            transmitLocation(reading.lat, reading.lng, reading.accuracy, reading.timestamp);
          },
          (err) => {
            if (err.code === err.PERMISSION_DENIED) {
              setPermissionState("denied");
              setPermissionError("Location permission denied. Enable location access in your browser settings to track route progress.");
              setLifecycleState("ERROR");
              toast.error("Location Permission Denied", {
                description: "NavSakhi needs device location to compute live route progress and telemetry.",
              });
            } else if (err.code === err.POSITION_UNAVAILABLE) {
              setPermissionError("Device position currently unavailable.");
              toast.warning("Position Unavailable", {
                description: "Waiting for GPS satellite signal...",
              });
            } else if (err.code === err.TIMEOUT) {
              setPermissionError("Location request timed out. Retrying...");
            }
          },
          {
            enableHighAccuracy: true,
            timeout: 20000,
            maximumAge: 5000,
          }
        );

        watchIdRef.current = watchId;
        toast.success("Journey Monitoring Active", {
          description: "Streaming authentic GPS telemetry over protected connection.",
        });
      } catch (err: unknown) {
        cleanupTracking();
        setLifecycleState("ERROR");
        const msg = err instanceof Error ? err.message : "Failed to start monitored journey.";
        setPermissionError(msg);
        toast.error("Failed to Start Monitoring", {
          description: msg,
        });
      }
    },
    [cleanupTracking, establishWebSocket, transmitLocation]
  );

  // Pause monitoring
  const pauseTracking = useCallback(async () => {
    const journeyId = activeJourneyIdRef.current;
    if (!journeyId) return;

    try {
      if (watchIdRef.current !== null && typeof navigator !== "undefined" && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setIsStale(false);
      await journeyService.pauseJourney(journeyId);
      setLifecycleState("PAUSED");
      toast.info("Journey Paused", {
        description: "Location telemetry paused.",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error pausing journey";
      toast.error("Could not pause journey", {
        description: msg,
      });
    }
  }, []);

  // Resume monitoring
  const resumeTracking = useCallback(async () => {
    const journeyId = activeJourneyIdRef.current;
    if (!journeyId) return;

    try {
      await journeyService.resumeJourney(journeyId);
      await establishWebSocket(journeyId);

      if (typeof navigator !== "undefined" && navigator.geolocation) {
        const watchId = navigator.geolocation.watchPosition(
          (pos) => {
            const reading: LiveTelemetrySnapshot = {
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
              accuracy: pos.coords.accuracy ?? null,
              timestamp: pos.timestamp || Date.now(),
            };
            lastFixTimestampRef.current = Date.now();
            setLatestTelemetry(reading);
            setIsStale(false);
            transmitLocation(reading.lat, reading.lng, reading.accuracy, reading.timestamp);
          },
          (err) => {
            console.warn("Geolocation watch error:", err.message);
          },
          { enableHighAccuracy: true, timeout: 20000, maximumAge: 5000 }
        );
        watchIdRef.current = watchId;
      }

      setLifecycleState("TRACKING");
      setIsStale(false);
      toast.success("Journey Resumed", {
        description: "Resumed live telemetry stream.",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error resuming journey";
      toast.error("Could not resume journey", {
        description: msg,
      });
    }
  }, [establishWebSocket, transmitLocation]);

  // Complete journey
  const completeTracking = useCallback(async () => {
    const journeyId = activeJourneyIdRef.current;
    cleanupTracking();
    setLifecycleState("COMPLETED");

    if (journeyId) {
      try {
        await journeyService.completeJourney(journeyId);
        toast.success("Journey Completed", {
          description: "All monitoring and telemetry ended safely.",
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error completing journey";
        console.warn("Error completing journey:", msg);
      }
    }
  }, [cleanupTracking]);

  // Cancel journey
  const cancelTracking = useCallback(async () => {
    const journeyId = activeJourneyIdRef.current;
    cleanupTracking();
    setLifecycleState("CANCELLED");

    if (journeyId) {
      try {
        await journeyService.cancelJourney(journeyId);
        toast.info("Journey Cancelled", {
          description: "Monitoring stopped and telemetry streams closed.",
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error cancelling journey";
        console.warn("Error cancelling journey:", msg);
      }
    }
  }, [cleanupTracking]);

  return {
    lifecycleState,
    permissionState,
    permissionError,
    latestTelemetry,
    serverProgress,
    isStale,
    startTracking,
    pauseTracking,
    resumeTracking,
    completeTracking,
    cancelTracking,
  };
}
