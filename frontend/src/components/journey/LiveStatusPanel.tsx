"use client";

import { Activity, ShieldCheck, Clock, MapPin, Eye, Zap, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

export function LiveStatusPanel() {
  return (
    <div className="flex h-full w-full flex-col bg-card/80 backdrop-blur-xl border-r border-border shadow-lg">
      
      {/* Header section with live pulse */}
      <div className="flex items-center justify-between border-b border-border p-5">
        <div className="flex items-center gap-2">
          <div className="relative flex h-3 w-3 items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success"></span>
          </div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Live Monitoring</h2>
        </div>
        <div className="flex items-center gap-1 rounded-md bg-success/10 px-2 py-1 text-xs font-bold text-success border border-success/20">
          <ShieldCheck size={14} /> 94 Score
        </div>
      </div>

      <ScrollArea className="flex-1">
        {/* Journey Metrics */}
        <div className="p-5 flex flex-col space-y-5">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="font-medium text-foreground">Journey Progress</span>
              <span className="text-muted-foreground">65%</span>
            </div>
            <Progress value={65} className="h-2 bg-secondary" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <MetricBox icon={Clock} label="ETA" value="12 mins" />
            <MetricBox icon={MapPin} label="Distance" value="1.2 km" />
          </div>
        </div>

        <Separator />

        {/* Live Agent Status */}
        <div className="p-5 flex flex-col space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ai-accent">
            <Eye size={16} />
            Agent is watching
          </div>
          
          <div className="flex flex-col gap-4 border-l-2 border-border ml-2 pl-4">
            
            <TimelineItem 
              time="12:45 PM" 
              title="Journey Started" 
              icon={CheckCircle2} 
              color="text-success"
            />
            <TimelineItem 
              time="12:50 PM" 
              title="Crowd Increased Ahead" 
              desc="Detected anomaly in historical pattern."
              icon={AlertTriangle} 
              color="text-warning"
            />
            <TimelineItem 
              time="12:51 PM" 
              title="Alternative Route Found" 
              desc="Switched to Main Ave for better lighting."
              icon={Zap} 
              color="text-ai-accent"
            />
            <TimelineItem 
              time="Now" 
              title="Monitoring Community Intel" 
              desc="Scanning 3km radius for live reports."
              icon={Activity} 
              color="text-muted-foreground"
              isLive
            />

          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

// Micro-component for the top metrics
function MetricBox({ icon: Icon, label, value }: { icon: any, label: string, value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-background/50 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon size={14} /> {label}
      </div>
      <span className="text-lg font-bold text-foreground">{value}</span>
    </div>
  );
}

// Micro-component for the vertical timeline
function TimelineItem({ time, title, desc, icon: Icon, color, isLive }: { time: string, title: string, desc?: string, icon: any, color: string, isLive?: boolean }) {
  return (
    <div className="relative">
      {/* Icon placed on the vertical line */}
      <div className={`absolute -left-[27px] top-0 flex h-6 w-6 items-center justify-center rounded-full bg-background border border-border ${color}`}>
        <Icon size={12} className={isLive ? "animate-pulse" : ""} />
      </div>
      
      <div className="flex flex-col">
        <span className="text-xs font-semibold text-muted-foreground mb-0.5">{time}</span>
        <span className={`text-sm font-medium ${isLive ? "text-foreground" : "text-muted-foreground"}`}>{title}</span>
        {desc && <span className="text-xs text-muted-foreground/70 mt-1">{desc}</span>}
      </div>
    </div>
  );
}