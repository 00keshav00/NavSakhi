"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  MapPin, Train, Bus, Shield, Landmark, Navigation, 
  Loader2, X, Check, Compass
} from "lucide-react";
import { journeyService } from "@/api/services/journeyService";
import { LocationSuggestion } from "@/types/journey";

interface LocationAutocompleteInputProps {
  id: string;
  value: string;
  onChangeText: (text: string) => void;
  selectedSuggestion: LocationSuggestion | null;
  onSelectSuggestion: (suggestion: LocationSuggestion | null) => void;
  placeholder?: string;
  className?: string;
  leadingIcon?: React.ReactNode;
  trailingAction?: React.ReactNode;
  ariaLabel?: string;
}

export function LocationAutocompleteInput({
  id,
  value,
  onChangeText,
  selectedSuggestion,
  onSelectSuggestion,
  placeholder = "Search places or enter coordinates...",
  className = "",
  leadingIcon,
  trailingAction,
  ariaLabel,
}: LocationAutocompleteInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const latestQueryRef = useRef<string>("");
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search query
  const performSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    latestQueryRef.current = trimmed;

    if (trimmed.length < 2) {
      setSuggestions([]);
      setIsLoading(false);
      setIsOpen(false);
      return;
    }

    setIsLoading(true);

    try {
      const results = await journeyService.autocomplete(trimmed, 8);
      // Discard stale out-of-order response
      if (latestQueryRef.current !== trimmed) return;

      if (results && results.length > 0) {
        setSuggestions(results);
        setHighlightedIndex(-1);
        setIsOpen(true);
      } else {
        setSuggestions([]);
        setIsOpen(false);
      }
    } catch {
      if (latestQueryRef.current !== trimmed) return;
      setSuggestions([]);
      setIsOpen(false);
    } finally {
      if (latestQueryRef.current === trimmed) {
        setIsLoading(false);
      }
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newText = e.target.value;
    onChangeText(newText);

    // If user modifies text away from selected suggestion, invalidate confirmed selection
    if (
      selectedSuggestion &&
      newText !== selectedSuggestion.name &&
      newText !== selectedSuggestion.formatted_coords
    ) {
      onSelectSuggestion(null);
    }

    if (newText.trim().length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      return;
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      performSearch(newText);
    }, 280);
  };

  const handleSelect = (item: LocationSuggestion) => {
    // Fill text with friendly name and bind canonical suggestion record
    onChangeText(item.name);
    onSelectSuggestion(item);
    setIsOpen(false);
    setSuggestions([]);
    setIsFocused(false);
  };

  const handleClear = () => {
    onChangeText("");
    onSelectSuggestion(null);
    setSuggestions([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      setIsOpen(false);
      return;
    }

    if (e.key === "Tab") {
      setIsOpen(false);
      return;
    }

    if (!isOpen || suggestions.length === 0) {
      if (e.key === "ArrowDown" && value.trim().length >= 2) {
        performSearch(value);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1));
    } else if (e.key === "Enter") {
      if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
        e.preventDefault();
        handleSelect(suggestions[highlightedIndex]);
      }
    }
  };

  const handleContainerBlur = (e: React.FocusEvent<HTMLDivElement>) => {
    if (containerRef.current?.contains(e.relatedTarget as Node)) {
      return;
    }
    setIsFocused(false);
    setIsOpen(false);
  };

  const getPlaceIcon = (type: string) => {
    switch (type) {
      case "METRO_STATION":
        return <Train className="w-4 h-4 text-emerald-400" />;
      case "RAILWAY_STATION":
        return <Train className="w-4 h-4 text-blue-400" />;
      case "BUS_STOP":
        return <Bus className="w-4 h-4 text-amber-400" />;
      case "SAFETY_FACILITY":
        return <Shield className="w-4 h-4 text-purple-400" />;
      case "LANDMARK":
        return <Landmark className="w-4 h-4 text-indigo-400" />;
      case "COORDINATES":
        return <Compass className="w-4 h-4 text-rose-400" />;
      default:
        return <MapPin className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getBadgeStyle = (type: string) => {
    switch (type) {
      case "METRO_STATION":
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      case "RAILWAY_STATION":
        return "bg-blue-500/15 text-blue-400 border-blue-500/30";
      case "BUS_STOP":
        return "bg-amber-500/15 text-amber-400 border-amber-500/30";
      case "SAFETY_FACILITY":
        return "bg-purple-500/15 text-purple-400 border-purple-500/30";
      case "LANDMARK":
        return "bg-indigo-500/15 text-indigo-400 border-indigo-500/30";
      case "COORDINATES":
        return "bg-rose-500/15 text-rose-400 border-rose-500/30";
      default:
        return "bg-zinc-500/15 text-zinc-300 border-zinc-500/30";
    }
  };

  const listboxId = `${id}-listbox`;
  const activeDescendantId =
    highlightedIndex >= 0 ? `${id}-option-${highlightedIndex}` : undefined;

  // The dropdown is ONLY visible when there are real, verified suggestions to show
  const showDropdown = isOpen && isFocused && suggestions.length > 0;

  return (
    <div
      ref={containerRef}
      onBlur={handleContainerBlur}
      className="relative w-full"
    >
      <div className="relative flex items-center">
        {/* Leading icon */}
        {leadingIcon && (
          <div className="absolute left-2.5 z-10 flex items-center pointer-events-none">
            {leadingIcon}
          </div>
        )}

        <input
          ref={inputRef}
          id={id}
          type="text"
          value={value}
          onChange={handleInputChange}
          onFocus={() => {
            setIsFocused(true);
            if (value.trim().length >= 2 && suggestions.length > 0) {
              setIsOpen(true);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label={ariaLabel || placeholder}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showDropdown}
          aria-controls={listboxId}
          aria-activedescendant={activeDescendantId}
          className={`w-full h-10 bg-background border border-border rounded-lg text-xs font-medium text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-1 focus:ring-primary focus:border-primary transition-colors ${
            leadingIcon ? "pl-8" : "pl-3"
          } ${
            trailingAction ? "pr-20" : value ? "pr-14" : "pr-8"
          } ${className}`}
        />

        {/* Right side controls: spinner, clear, and trailingAction */}
        <div className="absolute right-1.5 flex items-center gap-1 z-10">
          {isLoading && (
            <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
          )}

          {value && !isLoading && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
              title="Clear input"
              aria-label="Clear location input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          {trailingAction}
        </div>
      </div>

      {/* Selected location indicator badge */}
      {selectedSuggestion && (
        <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground px-1 truncate">
          <Check className="w-3 h-3 text-emerald-400 shrink-0" />
          <span className="font-semibold text-emerald-400/90 truncate">
            {selectedSuggestion.place_type_label}:
          </span>
          <span className="font-mono text-zinc-400 shrink-0">
            {selectedSuggestion.formatted_coords}
          </span>
        </div>
      )}

      {/* Autocomplete Dropdown - STRICTLY rendered ONLY when genuine suggestions exist */}
      {showDropdown && (
        <div
          id={listboxId}
          role="listbox"
          onMouseDown={(e) => {
            // Prevent input blur before option selection click fires
            e.preventDefault();
          }}
          className="absolute left-0 right-0 top-full mt-1 max-h-60 overflow-y-auto rounded-xl bg-card border border-border/80 shadow-2xl backdrop-blur-md z-40 p-1 flex flex-col gap-0.5 divide-y divide-border/20"
        >
          {suggestions.map((item, idx) => {
            const isHighlighted = idx === highlightedIndex;
            const isSelected = selectedSuggestion?.id === item.id;

            return (
              <div
                key={item.id}
                id={`${id}-option-${idx}`}
                role="option"
                aria-selected={isSelected || isHighlighted}
                onMouseEnter={() => setHighlightedIndex(idx)}
                onClick={() => handleSelect(item)}
                className={`flex items-start gap-2.5 p-2 rounded-lg cursor-pointer transition-colors text-left ${
                  isHighlighted
                    ? "bg-primary/20 text-foreground"
                    : isSelected
                    ? "bg-secondary/80 text-foreground"
                    : "hover:bg-secondary/40 text-foreground/90"
                }`}
              >
                <div className="mt-0.5 shrink-0 p-1 rounded-md bg-secondary/80 border border-border/50">
                  {getPlaceIcon(item.place_type)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1.5">
                    <span className="text-xs font-semibold truncate text-foreground">
                      {item.name}
                    </span>
                    <span
                      className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full border shrink-0 ${getBadgeStyle(
                        item.place_type
                      )}`}
                    >
                      {item.place_type_label}
                    </span>
                  </div>

                  <div className="text-[11px] text-muted-foreground truncate mt-0.5">
                    {item.secondary_text}
                  </div>

                  <div className="text-[10px] font-mono text-zinc-500 mt-0.5">
                    {item.formatted_coords}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
