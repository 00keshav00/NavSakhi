"use client";

import { MapPin, Navigation2, Settings2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";

export function JourneyForm() {
  return (
    <div className="flex h-full flex-col bg-card border-r border-border p-4 shadow-sm">
      <div className="mb-6 flex items-center gap-2 px-2 pt-2">
        <Navigation2 className="text-primary" size={20} />
        <h2 className="text-lg font-bold">Plan Journey</h2>
      </div>

      <div className="flex flex-col space-y-4 px-2">
        {/* Source & Destination Inputs */}
        <div className="relative flex flex-col space-y-3">
          <div className="absolute left-3.5 top-3.5 h-12 w-0.5 bg-border"></div>
          
          <div className="relative flex items-center">
            <div className="absolute left-0 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-background">
              <div className="h-2 w-2 rounded-full bg-primary"></div>
            </div>
            <Input id="sourceInput" placeholder="Current Location" className="ml-10 h-11 bg-background pr-16" />
            <button 
              type="button"
              onClick={() => {
                if (navigator.geolocation) {
                  navigator.geolocation.getCurrentPosition(
                    (pos) => {
                      const el = document.getElementById("sourceInput") as HTMLInputElement;
                      if (el) {
                        el.value = `${pos.coords.latitude.toFixed(5)}, ${pos.coords.longitude.toFixed(5)}`;
                        const event = new Event('input', { bubbles: true });
                        el.dispatchEvent(event);
                      }
                    }
                  );
                }
              }}
              className="absolute right-2 text-[10px] bg-primary/10 text-primary px-2 py-1 rounded hover:bg-primary/20 transition-colors"
            >
              DETECT
            </button>
          </div>

          <div className="relative flex items-center">
            <div className="absolute left-0 z-10 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-background">
              <MapPin size={14} className="text-danger" />
            </div>
            <Input placeholder="Where to?" className="ml-10 h-11 bg-background border-primary/50 ring-1 ring-primary/20" />
          </div>
        </div>

        <Separator className="my-4" />

        {/* AI Preferences */}
        <div className="flex flex-col space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <Settings2 size={16} />
            AI Safety Preferences
          </div>

          <PreferenceToggle id="avoid-dark" label="Avoid dark roads" defaultChecked />
          <PreferenceToggle id="avoid-crowds" label="Avoid heavy crowds" />
          <PreferenceToggle id="police-routes" label="Prefer police routes" defaultChecked />
          <PreferenceToggle id="fastest" label="Prioritize fastest route" />
        </div>
      </div>

      <div className="mt-auto pt-6 px-2 pb-2">
        <Button className="w-full h-12 text-md font-semibold shadow-lg shadow-primary/20">
          Agent, Plan Route
        </Button>
      </div>
    </div>
  );
}

// Micro-component for the toggles
function PreferenceToggle({ id, label, defaultChecked }: { id: string, label: string, defaultChecked?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <label htmlFor={id} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
        {label}
      </label>
      <Switch id={id} defaultChecked={defaultChecked} />
    </div>
  );
}