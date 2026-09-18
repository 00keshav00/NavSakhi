"use client";

import { motion, AnimatePresence } from "framer-motion";
import { 
  ShieldCheck, AlertTriangle, Bot, Navigation, Activity, Clock, 
  MapPin, CloudRain, Eye, Sun, Users, Radio, AlertOctagon, Share2, Phone
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import SafeMap from "@/components/map/SafeMap";
import { useLiveMonitor } from "@/hooks/useLiveMonitor";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function LiveMonitorPage() {
  // In a real flow, journeyId would come from global state (e.g. Zustand) or URL param
  // For Phase 5 validation, we use a mocked ID to force the UI to load
  const [journeyId] = useState("j_mock_active");
  const { data, isLoading, error } = useLiveMonitor(journeyId);

  // Auto-scroll timeline effect
  useEffect(() => {
    const timelineElement = document.getElementById("agent-timeline-scroll");
    if (timelineElement) {
      timelineElement.scrollTop = timelineElement.scrollHeight;
    }
  }, [data?.agent_timeline]);

  if (isLoading && !data) {
    return <LiveMonitorSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center p-6 text-center">
        <Bot size={48} className="text-muted-foreground mb-4 opacity-50" />
        <h2 className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">No Active Journey</h2>
        <p className="mt-2 text-muted-foreground font-light mb-6">Start a journey from the planner to monitor it here.</p>
        <Link href="/journey">
          <Button className="rounded-full gap-2 px-6"><Navigation size={16} /> Plan a Journey</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12">
      
      {/* Left Panel: Telemetry & Agent Status */}
      <aside className="relative z-10 flex h-full flex-col border-r border-border bg-card/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] backdrop-blur-3xl lg:col-span-5 dark:shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
        
        <div className="flex shrink-0 flex-col p-6 border-b border-border/30">
          <div className="flex items-center justify-between">
            <h1 className="font-[family-name:var(--font-jakarta)] text-2xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
              <Radio size={24} className="text-primary animate-pulse" /> Live Monitor
            </h1>
            <div className="flex items-center gap-2 px-3 py-1 bg-success/10 text-success rounded-full text-xs font-bold uppercase tracking-wider">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
              </span>
              Active
            </div>
          </div>
        </div>

        <ScrollArea className="flex-1 p-6">
          <div className="flex flex-col gap-6">
            
            {/* Live Safety Score */}
            <div className="glass-card flex items-center justify-between rounded-3xl p-6 bg-secondary/10 relative overflow-hidden group">
              <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-primary/5 blur-[80px]"></div>
              <div className="flex flex-col z-10">
                <span className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">Current Safety Score</span>
                <span className={`text-sm font-medium flex items-center gap-1 mt-1 ${data.safety_score.risk_level === 'Low' ? 'text-success' : 'text-warning'}`}>
                  <ShieldCheck size={16} /> Risk Level: {data.safety_score.risk_level}
                </span>
                <span className="text-xs text-muted-foreground mt-1">Trend: {data.safety_score.trend}</span>
              </div>
              <div className="flex flex-col items-end z-10">
                <span className={`text-5xl font-black ${data.safety_score.risk_level === 'Low' ? 'text-success' : 'text-warning'}`}>
                  {data.safety_score.current}<span className="text-2xl opacity-70">%</span>
                </span>
              </div>
            </div>

            {/* AI Recommendation Card */}
            <AnimatePresence mode="wait">
              <motion.div 
                key={data.ai_recommendation.recommendation}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="glass-card flex flex-col gap-3 rounded-3xl border-primary/20 bg-primary/5 p-6 relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-4 opacity-10"><Bot size={80} /></div>
                <div className="flex items-center gap-2 relative z-10 mb-1">
                  <Activity size={18} className="text-primary animate-pulse" />
                  <span className="font-[family-name:var(--font-jakarta)] text-sm font-bold text-foreground uppercase tracking-wider">Agent Intelligence</span>
                </div>
                <h3 className="font-bold text-lg text-primary relative z-10 leading-tight">
                  {data.ai_recommendation.recommendation}
                </h3>
                <p className="text-sm font-medium leading-relaxed text-muted-foreground relative z-10">
                  {data.ai_recommendation.reason}
                </p>
                
                {data.ai_recommendation.warnings.map((w, idx) => (
                  <div key={idx} className="flex items-start gap-2 mt-2 pt-3 border-t border-primary/10 text-warning text-sm font-semibold relative z-10">
                    <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </div>
                ))}
              </motion.div>
            </AnimatePresence>

            {/* Agent Timeline */}
            <div className="flex flex-col">
               <div className="flex items-center gap-2 mb-4 px-2">
                 <Radio size={16} className="text-muted-foreground" />
                 <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-sm uppercase tracking-wider text-muted-foreground">Action Feed</h3>
               </div>
               
               <div id="agent-timeline-scroll" className="glass-card rounded-3xl p-5 h-[240px] overflow-y-auto flex flex-col gap-4 relative">
                 <div className="absolute top-5 bottom-5 left-8 w-0.5 bg-border/50"></div>
                 {data.agent_timeline.map((item, i) => (
                   <motion.div 
                     initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} 
                     key={item.id} 
                     className="relative flex items-start gap-4 z-10"
                   >
                     <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary border-2 border-background text-primary shadow-sm mt-0.5">
                       <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                     </div>
                     <div className="flex flex-col">
                       <span className="text-sm font-medium text-foreground">{item.action}</span>
                       <span className="text-xs text-muted-foreground mt-0.5">{item.time}</span>
                     </div>
                   </motion.div>
                 ))}
               </div>
            </div>

            {/* Emergency Actions */}
            <div className="grid grid-cols-2 gap-3 mt-2 pb-6">
              <Button variant="outline" className="h-12 rounded-xl bg-background/50 border-border/50 gap-2">
                <Share2 size={16} className="text-primary" /> Share Location
              </Button>
              <Link href="/emergency">
                <Button className="h-12 w-full rounded-xl bg-danger hover:bg-danger/90 text-white gap-2 font-bold shadow-lg shadow-danger/20">
                  <AlertOctagon size={16} /> SOS
                </Button>
              </Link>
            </div>

          </div>
        </ScrollArea>
      </aside>

      {/* Right Panel: Progress & Map */}
      <main className="relative flex flex-col h-full w-full bg-background lg:col-span-7">
        
        {/* Top Overlay HUD */}
        <div className="absolute top-6 left-6 right-6 z-20 flex flex-col gap-4 pointer-events-none">
          
          {/* Progress Bar HUD */}
          <div className="glass-card rounded-2xl p-4 flex flex-col gap-3 pointer-events-auto">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Next Milestone</span>
                <span className="text-sm font-bold text-foreground">{data.status_summary.current_segment}</span>
              </div>
              <div className="flex items-center gap-4 text-right">
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Remaining</span>
                  <span className="text-sm font-bold flex items-center gap-1 justify-end"><MapPin size={12}/> {Math.ceil(data.status_summary.distance_remaining)}m</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">ETA</span>
                  <span className="text-sm font-bold flex items-center gap-1 justify-end"><Clock size={12}/> {Math.ceil(data.status_summary.eta / 60)} min</span>
                </div>
              </div>
            </div>
            
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-secondary/50">
              <motion.div 
                className="absolute left-0 top-0 h-full bg-primary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${data.status_summary.progress_percentage}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
          </div>

          {/* Environment Summary HUD */}
          <div className="flex gap-2 pointer-events-auto">
            <EnvironmentPill icon={CloudRain} label="Weather" value={data.environment_summary.weather_condition} />
            <EnvironmentPill icon={Eye} label="Visibility" value={data.environment_summary.visibility} />
            <EnvironmentPill icon={Sun} label="Lighting" value={data.environment_summary.lighting} />
            <EnvironmentPill icon={Users} label="Crowds" value={data.environment_summary.crowd_density} />
          </div>

        </div>

        {/* Live Tracking Map */}
        <div className="flex-1 w-full h-full relative z-0">
          <SafeMap 
            source={{ coordinates: [data.current_location.lng, data.current_location.lat] }} 
            destination={undefined}
            routeGeometry={data.current_route.geometry}
          />
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------
// Sub-components
// ---------------------------------------------------------

function EnvironmentPill({ icon: Icon, label, value }: { icon: any, label: string, value: string }) {
  return (
    <div className="glass-card flex items-center gap-2 rounded-xl px-3 py-2 bg-background/80 backdrop-blur-md border border-border/50">
      <Icon size={14} className="text-muted-foreground shrink-0" />
      <div className="flex flex-col">
        <span className="text-[9px] uppercase font-bold tracking-widest text-muted-foreground leading-none mb-0.5">{label}</span>
        <span className="text-xs font-semibold text-foreground leading-none">{value}</span>
      </div>
    </div>
  );
}

function LiveMonitorSkeleton() {
  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12 animate-pulse">
      <aside className="border-r border-border bg-card/60 lg:col-span-5 p-6 flex flex-col gap-6">
        <div className="h-8 w-48 bg-secondary rounded-xl mb-4"></div>
        <div className="h-32 bg-secondary/50 rounded-3xl"></div>
        <div className="h-48 bg-secondary/50 rounded-3xl"></div>
        <div className="flex-1 bg-secondary/30 rounded-3xl"></div>
      </aside>
      <main className="lg:col-span-7 bg-secondary/20 p-6 flex flex-col gap-4">
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
        <div className="h-10 w-3/4 bg-secondary/50 rounded-xl"></div>
        <div className="flex-1 rounded-3xl"></div>
      </main>
    </div>
  );
}