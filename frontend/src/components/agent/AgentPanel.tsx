"use client";

import { BrainCircuit, CheckCircle2, ShieldCheck, CloudRain, Users, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

export function AgentPanel() {
  return (
    <div className="flex h-full flex-col bg-card border-l border-border shadow-sm">
      <div className="flex items-center gap-2 border-b border-border p-5">
        <BrainCircuit className="text-ai-accent" size={20} />
        <h2 className="text-lg font-bold">Agent Status</h2>
      </div>

      <ScrollArea className="flex-1 p-5">
        {/* Agent Thinking Timeline */}
        <div className="flex flex-col space-y-6">
          <TimelineStep text="Understanding Goal" completed />
          <TimelineStep text="Finding Routes" completed />
          <TimelineStep text="Checking Weather" completed />
          <TimelineStep text="Predicting Crowd Density" completed />
          <TimelineStep text="Calculating Safety Scores" active />
        </div>

        <Separator className="my-8" />

        {/* AI Recommendation Card */}
        <div className="flex flex-col space-y-4 rounded-xl border border-ai-accent/30 bg-ai-accent/5 p-4 relative overflow-hidden">
          {/* Subtle glow effect */}
          <div className="absolute -right-4 -top-4 h-16 w-16 rounded-full bg-ai-accent/20 blur-xl"></div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-ai-accent uppercase tracking-wider">Recommendation</span>
            <div className="flex items-center gap-1 rounded-md bg-success/20 px-2 py-1 text-xs font-bold text-success">
              <ShieldCheck size={14} /> 94/100 Safe
            </div>
          </div>
          
          <h3 className="text-lg font-bold">Main Avenue Route</h3>
          
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <CloudRain size={16} /> Clear
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users size={16} /> Low Crowd
            </div>
          </div>
          
          <p className="text-xs leading-relaxed text-muted-foreground mt-2 border-t border-ai-accent/10 pt-3">
            <span className="font-semibold text-foreground">AI Reasoning:</span> Selected for optimal street lighting and proximity to 2 verified safe zones. Avoids the 5th street construction.
          </p>
        </div>
      </ScrollArea>

      <div className="border-t border-border p-5">
        <Button className="w-full h-12 bg-ai-accent hover:bg-ai-accent/90 text-white font-semibold">
          Start Live Journey
        </Button>
      </div>
    </div>
  );
}

// Micro-component for the Timeline
function TimelineStep({ text, completed, active }: { text: string, completed?: boolean, active?: boolean }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex shrink-0 items-center justify-center">
        {completed ? (
          <CheckCircle2 size={18} className="text-success" />
        ) : active ? (
          <Loader2 size={18} className="text-ai-accent animate-spin" />
        ) : (
          <div className="h-4 w-4 rounded-full border-2 border-muted" />
        )}
      </div>
      <span className={`text-sm ${active ? "font-semibold text-foreground" : completed ? "text-muted-foreground" : "text-muted-foreground/50"}`}>
        {text}
      </span>
    </div>
  );
}