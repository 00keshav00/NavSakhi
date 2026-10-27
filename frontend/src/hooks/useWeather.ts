"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { weatherService } from "@/api/services/weatherService";
import { LiveWeatherData } from "@/types/weather";
import { toast } from "sonner";

export interface WeatherLocation {
  name: string;
  latitude: number;
  longitude: number;
  source: "GPS" | "MANUAL";
}

export type LocationPermissionState = "PROMPT" | "REQUESTING" | "GRANTED" | "DENIED" | "UNSUPPORTED";

const STORAGE_KEY = "safeshe_weather_selected_location";

export function useWeather() {
  const [location, setLocation] = useState<WeatherLocation | null>(null);
  const [weather, setWeather] = useState<LiveWeatherData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [permissionState, setPermissionState] = useState<LocationPermissionState>("PROMPT");
  const [error, setError] = useState<string | null>(null);
  const lastFetchedKeyRef = useRef<string | null>(null);

  // Load saved location on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed: WeatherLocation = JSON.parse(saved);
        if (parsed && typeof parsed.latitude === "number" && typeof parsed.longitude === "number") {
          setLocation(parsed);
          setPermissionState(parsed.source === "GPS" ? "GRANTED" : "PROMPT");
        }
      }
    } catch {
      // Ignore JSON parse errors
    }
  }, []);

  const fetchWeatherForLocation = useCallback(async (loc: WeatherLocation, force: boolean = false) => {
    const key = `${loc.latitude.toFixed(2)}_${loc.longitude.toFixed(2)}`;
    if (!force && lastFetchedKeyRef.current === key && weather) {
      return;
    }
    lastFetchedKeyRef.current = key;
    setIsLoading(true);
    setError(null);
    try {
      const data = await weatherService.getLiveWeather(loc.latitude, loc.longitude, loc.name);
      setWeather(data);
      // Persist chosen location
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
      } catch {}
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to load live weather.";
      setError(msg);
      toast.error("Weather unavailable", { description: msg });
    } finally {
      setIsLoading(false);
    }
  }, [weather]);

  // Fetch when location is set or changes
  useEffect(() => {
    if (location) {
      fetchWeatherForLocation(location);
    }
  }, [location, fetchWeatherForLocation]);

  const requestDeviceLocation = useCallback(() => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      setPermissionState("UNSUPPORTED");
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setPermissionState("REQUESTING");
    setIsLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setPermissionState("GRANTED");

        // Reverse geocode to get a clean name
        let resolvedName = "Current Location";
        try {
          const geo = await weatherService.reverseGeocode(lat, lon);
          if (geo && geo.display_name) {
            resolvedName = geo.display_name;
          }
        } catch {
          resolvedName = `GPS (${lat.toFixed(2)}, ${lon.toFixed(2)})`;
        }

        const newLoc: WeatherLocation = {
          name: resolvedName,
          latitude: lat,
          longitude: lon,
          source: "GPS",
        };
        setLocation(newLoc);
      },
      (err) => {
        setIsLoading(false);
        setPermissionState("DENIED");
        if (err.code === 1) {
          setError("Location access is not enabled.");
        } else {
          setError(err.message || "Unable to acquire GPS coordinates.");
        }
      },
      { timeout: 9000, enableHighAccuracy: true }
    );
  }, []);

  const selectManualLocation = useCallback((name: string, latitude: number, longitude: number) => {
    const manualLoc: WeatherLocation = {
      name,
      latitude,
      longitude,
      source: "MANUAL",
    };
    setLocation(manualLoc);
  }, []);

  const refresh = useCallback(() => {
    if (location) {
      fetchWeatherForLocation(location, true);
    } else {
      requestDeviceLocation();
    }
  }, [location, fetchWeatherForLocation, requestDeviceLocation]);

  return {
    location,
    weather,
    isLoading,
    permissionState,
    error,
    requestDeviceLocation,
    selectManualLocation,
    refresh,
  };
}
