"use client";

import React, { useState } from "react";
import { 
  Sun, Cloud, CloudRain, CloudLightning, CloudDrizzle, 
  CloudFog, Snowflake, Wind, Droplets, MapPin, 
  RefreshCw, Navigation, Search, AlertCircle, Compass, Loader2
} from "lucide-react";
import { useWeather } from "@/hooks/useWeather";
import { LocationAutocompleteInput } from "@/components/journey/LocationAutocompleteInput";
import { LocationSuggestion } from "@/types/journey";
import { Button } from "@/components/ui/button";

export function RealWeatherCard() {
  const {
    location,
    weather,
    isLoading,
    permissionState,
    error,
    requestDeviceLocation,
    selectManualLocation,
    refresh,
  } = useWeather();

  const [isChangingLocation, setIsChangingLocation] = useState(false);
  const [manualSearchQuery, setManualSearchQuery] = useState("");
  const [selectedSuggestion, setSelectedSuggestion] = useState<LocationSuggestion | null>(null);

  const handleSelectSuggestion = (sug: LocationSuggestion | null) => {
    setSelectedSuggestion(sug);
    if (sug) {
      selectManualLocation(sug.name, sug.latitude, sug.longitude);
      setIsChangingLocation(false);
      setManualSearchQuery("");
      setSelectedSuggestion(null);
    }
  };

  // Weather Icon Helper
  const getWeatherIcon = (iconKey?: string, size = 44) => {
    switch (iconKey) {
      case "sun":
        return <Sun size={size} className="text-amber-500 animate-pulse-soft" />;
      case "partly-cloudy":
        return <Cloud size={size} className="text-amber-400" />;
      case "cloudy":
        return <Cloud size={size} className="text-zinc-400" />;
      case "rain":
      case "heavy-rain":
        return <CloudRain size={size} className="text-blue-400" />;
      case "thunderstorm":
        return <CloudLightning size={size} className="text-purple-400" />;
      case "drizzle":
        return <CloudDrizzle size={size} className="text-sky-400" />;
      case "fog":
        return <CloudFog size={size} className="text-zinc-400" />;
      case "snow":
        return <Snowflake size={size} className="text-cyan-300" />;
      default:
        return <Sun size={size} className="text-amber-500" />;
    }
  };

  const formatTimestamp = (isoString?: string) => {
    if (!isoString) return "Live";
    try {
      const dt = new Date(isoString);
      if (isNaN(dt.getTime())) {
        // Might be "2026-10-19T03:15" without timezone
        return isoString.replace("T", " ");
      }
      return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "Live";
    }
  };

  // 1. First-Use / No Location Selected State
  if (!location && !isLoading && permissionState !== "DENIED") {
    return (
      <div className="glass-card rounded-3xl p-6 md:p-8 flex flex-col justify-between relative overflow-hidden border border-border shadow-sm">
        <div className="flex items-center gap-2 text-primary font-semibold text-xs tracking-wider uppercase">
          <Compass size={16} />
          <span>Local Weather & Atmospheric Conditions</span>
        </div>
        <div className="my-5 max-w-lg">
          <h3 className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">
            See weather for your location
          </h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Get accurate, real-time observations, hourly forecasts, and UV indicators powered by Open-Meteo.
          </p>
        </div>

        {isChangingLocation ? (
          <div className="bg-secondary/40 p-3.5 rounded-2xl border border-border/70 space-y-3">
            <div className="text-xs font-semibold text-foreground">Search a city, locality, or enter GPS:</div>
            <LocationAutocompleteInput
              id="weather-search"
              value={manualSearchQuery}
              onChangeText={setManualSearchQuery}
              selectedSuggestion={selectedSuggestion}
              onSelectSuggestion={handleSelectSuggestion}
              placeholder="E.g. Chennai, Tambaram, or coordinates..."
            />
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => setIsChangingLocation(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={requestDeviceLocation}
              className="rounded-full gap-2 px-5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            >
              <Navigation size={15} /> Use my current location
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsChangingLocation(true)}
              className="rounded-full gap-2 px-5 border-border bg-card/80 hover:bg-secondary"
            >
              <Search size={15} /> Search a location
            </Button>
          </div>
        )}
      </div>
    );
  }

  // 2. Permission Denied State
  if (permissionState === "DENIED" && !location) {
    return (
      <div className="glass-card rounded-3xl p-6 md:p-8 flex flex-col justify-between relative overflow-hidden border border-danger/30 bg-danger/5 shadow-sm">
        <div className="flex items-center gap-2 text-danger font-semibold text-xs tracking-wider uppercase">
          <AlertCircle size={16} />
          <span>Location Permission Notice</span>
        </div>
        <div className="my-4 max-w-lg">
          <h3 className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">
            Location access is not enabled.
          </h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            NavSakhi respects your privacy and only requests location when you choose. You can enable permissions in your browser or manually search your intended area below.
          </p>
        </div>

        {isChangingLocation ? (
          <div className="bg-background/80 p-3.5 rounded-2xl border border-border space-y-3">
            <div className="text-xs font-semibold text-foreground">Search a city or locality:</div>
            <LocationAutocompleteInput
              id="weather-search-denied"
              value={manualSearchQuery}
              onChangeText={setManualSearchQuery}
              selectedSuggestion={selectedSuggestion}
              onSelectSuggestion={handleSelectSuggestion}
              placeholder="Search places or enter coordinates..."
            />
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => setIsChangingLocation(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            <Button
              variant="outline"
              onClick={requestDeviceLocation}
              className="rounded-full gap-2 px-5 border-border hover:bg-secondary"
            >
              <Navigation size={15} /> Try location access again
            </Button>
            <Button
              onClick={() => setIsChangingLocation(true)}
              className="rounded-full gap-2 px-5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Search size={15} /> Search a location
            </Button>
          </div>
        )}
      </div>
    );
  }

  // 3. Loading Skeleton
  if (isLoading && !weather) {
    return (
      <div className="glass-card rounded-3xl p-6 md:p-8 flex flex-col justify-between border border-border animate-pulse">
        <div className="flex justify-between items-center mb-6">
          <div className="h-5 w-40 bg-secondary rounded-lg"></div>
          <div className="h-8 w-28 bg-secondary rounded-full"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-secondary rounded-2xl"></div>
            <div>
              <div className="h-10 w-24 bg-secondary rounded-xl mb-2"></div>
              <div className="h-4 w-32 bg-secondary rounded-md"></div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="h-16 bg-secondary/60 rounded-2xl"></div>
            <div className="h-16 bg-secondary/60 rounded-2xl"></div>
            <div className="h-16 bg-secondary/60 rounded-2xl"></div>
            <div className="h-16 bg-secondary/60 rounded-2xl"></div>
          </div>
        </div>
      </div>
    );
  }

  // 4. Data-Driven Weather Card
  const isAvailable = weather?.available !== false && weather?.status !== "UNAVAILABLE" && weather?.status !== "RATE_LIMITED";
  const tempVal = isAvailable && typeof weather?.temperature === "number" ? Math.round(weather.temperature) : null;
  const apparentVal = isAvailable && typeof weather?.apparent_temperature === "number" ? Math.round(weather.apparent_temperature) : tempVal;
  const conditionLabel = isAvailable
    ? (weather?.condition || "Clear")
    : (weather?.status === "RATE_LIMITED" ? "Provider Rate Limited" : "Weather Unavailable");
  const humidityVal = isAvailable && typeof weather?.humidity === "number" ? weather.humidity : null;
  const windVal = isAvailable && typeof weather?.wind_speed === "number" ? Math.round(weather.wind_speed) : null;
  const rainVal = isAvailable && typeof weather?.precipitation === "number" ? weather.precipitation : null;
  const uvVal = isAvailable && typeof weather?.uv_index === "number" ? Math.round(weather.uv_index) : null;
  const uvMaxVal = isAvailable && typeof weather?.uv_index_max === "number" ? Math.round(weather.uv_index_max) : null;
  const uvDescriptor = uvVal !== null
    ? (uvVal >= 8 ? "Very High" : uvVal >= 6 ? "High" : uvVal >= 3 ? "Moderate" : uvVal > 0 ? "Low" : "Minimal / Night")
    : "--";

  return (
    <div className="glass-card rounded-3xl p-4.5 sm:p-6 md:p-7 flex flex-col justify-between border border-border/80 shadow-sm relative overflow-hidden group">
      {/* Background Soft Glow */}
      <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary/10 blur-[70px] pointer-events-none" />

      {/* Top Header Row - Responsive Stack on Mobile, Row on Desktop */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 relative z-10">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-foreground font-bold text-sm sm:text-base">
            <MapPin size={16} className="text-primary shrink-0" />
            <span className="truncate sm:max-w-[340px]" title={location?.name || weather?.location_name || "Selected Location"}>
              {location?.name || weather?.location_name || "Selected Location"}
            </span>
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5 flex flex-wrap items-center gap-1.5 font-medium">
            <span>Observed {formatTimestamp(weather?.observation_timestamp)}</span>
            <span>&bull;</span>
            <span className="text-primary/90 font-semibold">{weather?.provider || "Open-Meteo"}</span>
            {weather?.cached && (
              <span className="px-1.5 py-0.5 rounded bg-secondary/80 text-[10px] text-muted-foreground border border-border/40 font-medium">Cached</span>
            )}
            {!isAvailable && (
              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[10px] border border-amber-500/20 font-medium">
                {weather?.status === "RATE_LIMITED" ? "Rate Limited" : "Offline"}
              </span>
            )}
          </div>
        </div>

        {/* Action Controls - Always Fully Visible and Aligned */}
        <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsChangingLocation((prev) => !prev)}
            className="rounded-full text-xs font-semibold px-3 sm:px-3.5 h-8 border-border bg-card/70 hover:bg-secondary text-foreground shadow-2xs"
            aria-label="Change weather location"
          >
            <Search size={13} className="mr-1.5 text-primary" />
            <span>Change Location</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={refresh}
            disabled={isLoading}
            className="rounded-full h-8 w-8 p-0 text-muted-foreground hover:text-foreground hover:bg-secondary"
            title="Refresh weather"
            aria-label="Refresh weather data"
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          </Button>
        </div>
      </div>

      {/* Manual Search Dropdown (Inline Toggle) */}
      {isChangingLocation && (
        <div className="mb-4 p-3 bg-secondary/50 rounded-2xl border border-border/80 space-y-2 relative z-20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-foreground">Select New Location:</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={requestDeviceLocation}
              className="text-[11px] h-7 px-2 text-primary font-semibold hover:bg-secondary"
            >
              <Navigation size={12} className="mr-1" /> Use GPS
            </Button>
          </div>
          <LocationAutocompleteInput
            id="weather-change-input"
            value={manualSearchQuery}
            onChangeText={setManualSearchQuery}
            selectedSuggestion={selectedSuggestion}
            onSelectSuggestion={handleSelectSuggestion}
            placeholder="Search city, station, or coordinates..."
          />
        </div>
      )}

      {/* Main Weather Information Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-center relative z-10">
        {/* Left: Big Temp & Condition (Spans 5 cols) */}
        <div className="md:col-span-5 flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-secondary/60 border border-border/40 shrink-0">
            {getWeatherIcon(isAvailable ? weather?.condition_icon : "cloudy", 44)}
          </div>
          <div>
            <div className="text-4xl md:text-5xl font-black font-[family-name:var(--font-jakarta)] text-foreground tracking-tight">
              {tempVal !== null ? `${tempVal}°C` : "--"}
            </div>
            <div className="text-xs md:text-sm font-semibold text-foreground/90 mt-0.5">
              {conditionLabel}
            </div>
            <div className="text-[11px] text-muted-foreground font-medium">
              {apparentVal !== null ? `Feels like ${apparentVal}°C` : "Atmospheric telemetry offline"}
            </div>
          </div>
        </div>

        {/* Right: 4 Metrics Grid (Spans 7 cols) */}
        <div className="md:col-span-7 grid grid-cols-2 gap-2.5 sm:gap-3">
          {/* Humidity */}
          <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-2xl bg-secondary/40 border border-border/50">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500 shrink-0">
              <Droplets size={16} />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground block truncate">
                Humidity
              </span>
              <span className="text-sm font-black text-foreground">
                {humidityVal !== null ? `${humidityVal}%` : "--"}
              </span>
            </div>
          </div>

          {/* Wind */}
          <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-2xl bg-secondary/40 border border-border/50">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-500 shrink-0">
              <Wind size={16} />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground block truncate">
                Wind
              </span>
              <span className="text-sm font-black text-foreground">
                {windVal !== null ? `${windVal} km/h` : "--"}
              </span>
            </div>
          </div>

          {/* Rain / Precipitation */}
          <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-2xl bg-secondary/40 border border-border/50">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-500 shrink-0">
              <CloudRain size={16} />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground block truncate">
                Rain
              </span>
              <span className="text-sm font-black text-foreground">
                {rainVal !== null ? `${rainVal} mm` : "--"}
              </span>
            </div>
          </div>

          {/* UV Index */}
          <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-2xl bg-secondary/40 border border-border/50">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500 shrink-0">
              <Sun size={16} />
            </div>
            <div className="min-w-0">
              <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground block truncate">
                UV Index
              </span>
              <span className="text-sm font-black text-foreground">
                {uvVal !== null ? uvVal : "--"}{" "}
                <span className="text-[10px] font-normal text-muted-foreground">
                  ({uvDescriptor}{uvMaxVal !== null ? ` · Peak ${uvMaxVal}` : ""})
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {!isAvailable && (
        <div className="mt-3.5 pt-2.5 border-t border-border/50 text-[11px] text-muted-foreground flex items-center gap-2">
          <AlertCircle size={13} className="text-amber-500 shrink-0" />
          <span>
            Weather provider is temporarily offline or rate-limited. Journey routing and safety scoring operate independently.
          </span>
        </div>
      )}
    </div>
  );
}
