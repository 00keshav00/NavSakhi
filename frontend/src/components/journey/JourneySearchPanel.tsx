"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  MapPin, ArrowUpDown, Clock, Train, 
  Car, Bike, Search, RotateCcw, Crosshair
} from "lucide-react";
import { toast } from "sonner";
import { LocationAutocompleteInput } from "./LocationAutocompleteInput";
import { LocationSuggestion } from "@/types/journey";

interface JourneySearchPanelProps {
  isLoading: boolean;
  hasRoutes: boolean;
  onSearch: (params: {
    source: string;
    destination: string;
    preferences: string[];
    travelTime?: string;
  }) => void;
  onReset: () => void;
  initialSource?: string;
  initialDest?: string;
}

export function JourneySearchPanel({
  isLoading,
  hasRoutes,
  onSearch,
  onReset,
  initialSource = "",
  initialDest = "",
}: JourneySearchPanelProps) {
  const [source, setSource] = useState(initialSource);
  const [dest, setDest] = useState(initialDest);
  const [sourceSuggestion, setSourceSuggestion] = useState<LocationSuggestion | null>(null);
  const [destSuggestion, setDestSuggestion] = useState<LocationSuggestion | null>(null);

  const [timeMode, setTimeMode] = useState<"now" | "later">("now");
  const [laterDate, setLaterDate] = useState("");
  const [laterTime, setLaterTime] = useState("");
  const [transportPref, setTransportPref] = useState<"any" | "public" | "personal">("any");
  const [vehicleType, setVehicleType] = useState<"two_wheeler" | "four_wheeler">("four_wheeler");
  const [routePriority, setRoutePriority] = useState<"safest" | "fastest" | "fewest_transfers" | "prefer_familiar" | "prefer_businesses">("safest");
  const [isDetectingLocation, setIsDetectingLocation] = useState(false);

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser.");
      return;
    }

    setIsDetectingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsDetectingLocation(false);
        const coords = `${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`;
        setSource(coords);
        setSourceSuggestion({
          id: `gps_${Date.now()}`,
          name: `Current Location (${coords})`,
          secondary_text: "Device GPS Position",
          place_type: "COORDINATES",
          place_type_label: "Device GPS",
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          formatted_coords: coords,
          source: "COORDINATES",
        });
        toast.success("Location Detected", {
          description: `Set source coordinates to ${coords}`,
        });
      },
      (err) => {
        setIsDetectingLocation(false);
        toast.error("Location detection failed", {
          description: err.message || "Please enter your source manually.",
        });
      },
      { timeout: 8000 }
    );
  };

  const handleSwap = () => {
    const tempSource = source;
    const tempSourceSug = sourceSuggestion;
    setSource(dest);
    setSourceSuggestion(destSuggestion);
    setDest(tempSource);
    setDestSuggestion(tempSourceSug);
  };

  const handlePanelReset = () => {
    setSource("");
    setDest("");
    setSourceSuggestion(null);
    setDestSuggestion(null);
    onReset();
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!source.trim() || !dest.trim()) {
      toast.error("Please enter both source and destination.");
      return;
    }

    const preferences: string[] = [routePriority];
    if (transportPref === "public") preferences.push("public_transport");
    if (transportPref === "personal") {
      preferences.push("personal_vehicle");
      preferences.push(vehicleType);
    }

    let reqTime: string | undefined = undefined;
    if (timeMode === "later" && laterDate && laterTime) {
      reqTime = new Date(`${laterDate}T${laterTime}`).toISOString();
    }

    // Submit canonical coordinates if available, otherwise trimmed text
    const resolvedSource = sourceSuggestion?.formatted_coords || source.trim();
    const resolvedDest = destSuggestion?.formatted_coords || dest.trim();

    onSearch({
      source: resolvedSource,
      destination: resolvedDest,
      preferences,
      travelTime: reqTime,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3.5 p-4">
      {/* Origin & Destination Container */}
      <div className="relative flex flex-col gap-2 bg-secondary/30 p-2.5 rounded-xl border border-border">
        {/* Source Field with Autocomplete */}
        <LocationAutocompleteInput
          id="journey-source"
          value={source}
          onChangeText={setSource}
          selectedSuggestion={sourceSuggestion}
          onSelectSuggestion={setSourceSuggestion}
          placeholder="Origin (station, locality, or coordinates)"
          ariaLabel="Journey origin location"
          leadingIcon={
            <div className="w-2.5 h-2.5 rounded-full bg-primary ring-4 ring-primary/20" />
          }
          trailingAction={
            <button
              type="button"
              onClick={handleDetectLocation}
              disabled={isDetectingLocation}
              className="px-2 py-1 text-[11px] font-semibold text-primary hover:bg-primary/10 rounded flex items-center gap-1 transition-colors disabled:opacity-50"
              title="Auto-detect current coordinates"
            >
              <Crosshair className="w-3 h-3" />
              <span>{isDetectingLocation ? "..." : "GPS"}</span>
            </button>
          }
        />

        {/* Swap Button Divider */}
        <div className="relative flex items-center justify-center my--1">
          <div className="absolute inset-x-0 h-px bg-border/80" />
          <button
            type="button"
            onClick={handleSwap}
            className="relative z-10 p-1 rounded-full bg-card border border-border hover:bg-secondary text-muted-foreground hover:text-foreground transition-all shadow-xs"
            aria-label="Swap origin and destination"
          >
            <ArrowUpDown className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Destination Field with Autocomplete */}
        <LocationAutocompleteInput
          id="journey-destination"
          value={dest}
          onChangeText={setDest}
          selectedSuggestion={destSuggestion}
          onSelectSuggestion={setDestSuggestion}
          placeholder="Where to? (station, landmark, or coordinates)"
          ariaLabel="Journey destination location"
          leadingIcon={
            <MapPin className="w-4 h-4 text-rose-500" />
          }
        />
      </div>

      {/* Travel Time Toggle */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-primary" /> Departure Time
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1.5 bg-secondary/40 p-1 rounded-lg border border-border">
          <button
            type="button"
            onClick={() => setTimeMode("now")}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all ${
              timeMode === "now"
                ? "bg-card text-foreground shadow-xs border border-border"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Leave Now
          </button>
          <button
            type="button"
            onClick={() => setTimeMode("later")}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all ${
              timeMode === "later"
                ? "bg-card text-foreground shadow-xs border border-border"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Depart Later
          </button>
        </div>

        {timeMode === "later" && (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Input
              type="date"
              value={laterDate}
              onChange={(e) => setLaterDate(e.target.value)}
              className="h-8 text-xs bg-background border-border"
            />
            <Input
              type="time"
              value={laterTime}
              onChange={(e) => setLaterTime(e.target.value)}
              className="h-8 text-xs bg-background border-border"
            />
          </div>
        )}
      </div>

      {/* Transport Preferences */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-muted-foreground">Transport Mode</label>
        <div className="grid grid-cols-3 gap-1.5 bg-secondary/40 p-1 rounded-lg border border-border">
          <button
            type="button"
            onClick={() => setTransportPref("any")}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all ${
              transportPref === "any"
                ? "bg-card text-foreground shadow-xs border border-border"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All Modes
          </button>
          <button
            type="button"
            onClick={() => setTransportPref("public")}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1 ${
              transportPref === "public"
                ? "bg-card text-foreground shadow-xs border border-border"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Train className="w-3 h-3" /> Transit
          </button>
          <button
            type="button"
            onClick={() => setTransportPref("personal")}
            className={`py-1.5 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1 ${
              transportPref === "personal"
                ? "bg-card text-foreground shadow-xs border border-border"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Car className="w-3 h-3" /> Personal
          </button>
        </div>

        {transportPref === "personal" && (
          <div className="grid grid-cols-2 gap-1.5 pt-1">
            <button
              type="button"
              onClick={() => setVehicleType("two_wheeler")}
              className={`py-1 px-2 text-xs font-medium rounded-md border flex items-center justify-center gap-1.5 transition-colors ${
                vehicleType === "two_wheeler"
                  ? "bg-primary/10 text-primary border-primary/30"
                  : "bg-background text-muted-foreground border-border hover:bg-secondary"
              }`}
            >
              <Bike className="w-3.5 h-3.5" /> Two Wheeler
            </button>
            <button
              type="button"
              onClick={() => setVehicleType("four_wheeler")}
              className={`py-1 px-2 text-xs font-medium rounded-md border flex items-center justify-center gap-1.5 transition-colors ${
                vehicleType === "four_wheeler"
                  ? "bg-primary/10 text-primary border-primary/30"
                  : "bg-background text-muted-foreground border-border hover:bg-secondary"
              }`}
            >
              <Car className="w-3.5 h-3.5" /> Four Wheeler
            </button>
          </div>
        )}
      </div>

      {/* Route Strategy & User Preference */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-muted-foreground">Route Strategy &amp; Local Knowledge</label>
        <div className="flex flex-wrap gap-1 bg-secondary/30 p-1.5 rounded-lg border border-border">
          {[
            { id: "safest", label: "Safest (ML)" },
            { id: "fastest", label: "Fastest" },
            { id: "fewest_transfers", label: "Fewest Transfers" },
            { id: "prefer_familiar", label: "Prefer Familiar Route" },
            { id: "prefer_businesses", label: "Prefer Mapped Shops" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setRoutePriority(item.id as typeof routePriority)}
              className={`py-1 px-2 text-[11px] font-semibold rounded-md transition-all ${
                routePriority === item.id
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "bg-card text-muted-foreground hover:text-foreground border border-border/60"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-2 flex items-center gap-2">
        <Button
          type="submit"
          disabled={isLoading}
          className="flex-1 h-11 text-xs font-bold shadow-md shadow-primary/20 flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground" />
              <span>Analyzing Routes...</span>
            </>
          ) : (
            <>
              <Search className="w-3.5 h-3.5" />
              <span>Find Safe Routes</span>
            </>
          )}
        </Button>

        {hasRoutes && (
          <Button
            type="button"
            variant="outline"
            onClick={handlePanelReset}
            className="h-11 px-3 text-muted-foreground hover:text-foreground"
            title="Reset search"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
        )}
      </div>
    </form>
  );
}
