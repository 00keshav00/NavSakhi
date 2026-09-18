"use client";

import { 
  ShieldCheck, 
  MapPin, 
  AlertTriangle, 
  Clock, 
  ArrowRight,
  Sparkles,
  Navigation,
  Cloud,
  Droplets,
  Eye,
  Thermometer,
  Users,
  Activity,
  Server,
  Zap,
  TrendingUp,
  RefreshCcw,
  CheckCircle2,
  XCircle,
  AlertCircle
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuthStore } from "@/store/authStore";

export default function HomePage() {
  const { data, isLoading, error, refresh } = useDashboard();
  const user = useAuthStore((state) => state.user);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center p-6 text-center">
        <div className="glass-card flex max-w-md flex-col items-center rounded-3xl p-8 border-danger/30 bg-danger/5">
          <AlertCircle size={48} className="text-danger mb-4" />
          <h2 className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">Connection Error</h2>
          <p className="mt-2 text-muted-foreground font-light mb-6">{error || "Failed to load dashboard data."}</p>
          <Button onClick={refresh} className="rounded-full gap-2 px-6">
            <RefreshCcw size={16} /> Retry Connection
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto px-6 py-10 lg:px-12 scroll-smooth">
      <div className="mx-auto flex w-full max-w-6xl flex-col space-y-10">
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <div>
            <div className={`inline-flex items-center gap-1.5 px-3 py-1 mb-3 rounded-full text-xs font-semibold uppercase tracking-wider ${
              data.ai_status.health === 'Optimal' ? 'bg-primary/10 text-primary' : 'bg-warning/10 text-warning'
            }`}>
              <Sparkles size={14} className="animate-pulse-soft" /> AI Agent: {data.ai_status.health}
            </div>
            <h1 className="text-4xl font-[family-name:var(--font-jakarta)] font-extrabold tracking-tight text-foreground">
              Welcome back, <span className="text-gradient-primary">{user?.full_name?.split(' ')[0] || "User"}</span>
            </h1>
            <p className="mt-2 text-muted-foreground text-lg font-light">
              {data.ai_status.recommendation}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={refresh} className="rounded-full h-12 w-12 p-0 border-border bg-background/50 backdrop-blur-md">
              <RefreshCcw size={18} className="text-muted-foreground" />
            </Button>
            <Link href="/journey">
              <Button size="lg" className="btn-premium rounded-full gap-2 text-md px-6 shadow-primary/20">
                <Navigation size={18} /> Plan Safe Journey
              </Button>
            </Link>
          </div>
        </header>

        {/* Top Grid: Safety Score & Quick Actions */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-12 animate-slide-up" style={{ animationDelay: "0.2s" }}>
          
          {/* Safety Score Card (Spans 8 cols) */}
          <section className="glass-card flex flex-col justify-between rounded-3xl p-8 md:col-span-8 relative overflow-hidden group">
            <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-primary/10 blur-[80px] transition-opacity group-hover:bg-primary/20"></div>
            
            <div className="relative z-10 flex items-start justify-between">
              <div className="flex flex-col">
                <h2 className="text-2xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">{data.ai_status.mode}</h2>
                <div className="mt-1 flex items-center gap-2 text-muted-foreground font-medium">
                  <TrendingUp size={16} className={data.safety_score.trend === 'improving' ? 'text-success' : 'text-warning'} />
                  Trend: {data.safety_score.trend} &bull; Confidence {data.safety_score.confidence}%
                </div>
              </div>
              <div className="flex flex-col items-end">
                <div className="text-5xl font-black text-primary font-[family-name:var(--font-jakarta)] leading-none">
                  {data.safety_score.overall}
                </div>
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground mt-1">Overall Score</span>
              </div>
            </div>

            <div className="relative z-10 mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4 border-t border-border/50 pt-6">
              <MetricItem icon={<Thermometer />} label="Weather" value={`${data.weather.temperature}°C, ${data.weather.condition}`} />
              <MetricItem icon={<Users />} label="Nearby Reports" value={data.community.nearby_reports.toString()} />
              <MetricItem icon={<ShieldCheck />} label="Safe Zones" value={data.community.safe_zones.toString()} />
              <MetricItem icon={<Activity />} label="Risk Level" value={data.safety_score.risk_level} color={data.safety_score.risk_level === 'Low' ? 'text-success' : 'text-warning'} />
            </div>
          </section>

          {/* Quick Actions (Spans 4 cols) */}
          <section className="glass-card flex flex-col rounded-3xl p-6 md:col-span-4 justify-center gap-4 relative overflow-hidden">
            <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-lg mb-2">Quick Actions</h3>
            <Link href="/community" className="w-full">
              <Button variant="outline" className="w-full justify-start h-12 rounded-xl bg-background/30 border-border/50 hover:bg-secondary">
                <Users size={18} className="mr-3 text-primary" /> View Community Hazards
              </Button>
            </Link>
            <Link href="/emergency" className="w-full">
              <Button variant="outline" className="w-full justify-start h-12 rounded-xl border-danger/30 bg-danger/5 hover:bg-danger/10 text-danger hover:text-danger">
                <AlertTriangle size={18} className="mr-3" /> Emergency Center
              </Button>
            </Link>
            <Button variant="outline" disabled className="w-full justify-start h-12 rounded-xl bg-background/30 border-border/50 opacity-50 cursor-not-allowed">
              <Zap size={18} className="mr-3 text-muted-foreground" /> Ask AI Assistant (Soon)
            </Button>
          </section>
        </div>

        {/* Middle Grid: Alerts, Timeline & Weather Details */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 animate-slide-up" style={{ animationDelay: "0.3s" }}>
          
          {/* Recent Alerts */}
          <section className="glass-card flex flex-col rounded-3xl p-6 relative overflow-hidden">
             <div className="flex items-center gap-2 mb-6">
               <AlertTriangle size={20} className="text-warning" />
               <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-lg">Active Alerts</h3>
             </div>
             
             {data.recent_alerts.length === 0 ? (
               <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                 <CheckCircle2 size={32} className="mb-2 opacity-20" />
                 <p className="text-sm font-medium">No active alerts</p>
               </div>
             ) : (
               <div className="flex flex-col gap-3 overflow-y-auto pr-2">
                 {data.recent_alerts.map((alert) => (
                   <div key={alert.id} className={`p-4 rounded-xl border ${
                     alert.severity === 'danger' ? 'bg-danger/10 border-danger/20 text-danger' :
                     alert.severity === 'warning' ? 'bg-warning/10 border-warning/20 text-warning' :
                     'bg-primary/5 border-primary/20 text-primary'
                   }`}>
                     <p className="text-sm font-medium leading-snug">{alert.message}</p>
                     <p className="text-xs mt-2 opacity-70">{alert.time}</p>
                   </div>
                 ))}
               </div>
             )}
          </section>

          {/* AI Timeline */}
          <section className="glass-card flex flex-col rounded-3xl p-6 relative overflow-hidden">
             <div className="flex items-center gap-2 mb-6">
               <Activity size={20} className="text-primary" />
               <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-lg">Agent Timeline</h3>
             </div>
             <div className="flex flex-col gap-5 relative before:absolute before:inset-0 before:ml-2.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-primary/50 before:to-transparent">
                {data.ai_timeline.map((item, i) => (
                  <div key={item.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                    <div className="flex items-center justify-center w-6 h-6 rounded-full border-2 border-background bg-primary text-background shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                      <div className="h-1.5 w-1.5 bg-background rounded-full"></div>
                    </div>
                    <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1.5rem)] glass-card p-3 rounded-xl border border-border/50">
                      <p className="text-sm font-medium text-foreground leading-snug">{item.event}</p>
                      <time className="text-xs text-muted-foreground mt-1">{item.time}</time>
                    </div>
                  </div>
                ))}
             </div>
          </section>

          {/* Weather & Details */}
          <section className="glass-card flex flex-col rounded-3xl p-6 relative overflow-hidden">
             <div className="flex items-center gap-2 mb-6">
               <Cloud size={20} className="text-info" />
               <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-lg">Environment Context</h3>
             </div>
             <div className="grid grid-cols-2 gap-4 flex-1">
               <div className="flex flex-col gap-1 p-4 rounded-2xl bg-secondary/50">
                 <Thermometer size={20} className="text-muted-foreground mb-1" />
                 <span className="text-xl font-bold text-foreground">{data.weather.temperature}°C</span>
                 <span className="text-xs text-muted-foreground uppercase">Temp</span>
               </div>
               <div className="flex flex-col gap-1 p-4 rounded-2xl bg-secondary/50">
                 <Droplets size={20} className="text-info mb-1" />
                 <span className="text-xl font-bold text-foreground">{data.weather.humidity}%</span>
                 <span className="text-xs text-muted-foreground uppercase">Humidity</span>
               </div>
               <div className="flex flex-col gap-1 p-4 rounded-2xl bg-secondary/50">
                 <Cloud size={20} className="text-muted-foreground mb-1" />
                 <span className="text-xl font-bold text-foreground">{data.weather.rain_probability}%</span>
                 <span className="text-xs text-muted-foreground uppercase">Rain Prob</span>
               </div>
               <div className="flex flex-col gap-1 p-4 rounded-2xl bg-secondary/50">
                 <Eye size={20} className="text-muted-foreground mb-1" />
                 <span className="text-xl font-bold text-foreground">{data.weather.visibility}km</span>
                 <span className="text-xs text-muted-foreground uppercase">Visibility</span>
               </div>
             </div>
          </section>

        </div>

        {/* Bottom Area: Journeys & System Health */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 animate-slide-up" style={{ animationDelay: "0.4s" }}>
          
          {/* Recent Journeys (Spans 2 cols) */}
          <section className="md:col-span-2 flex flex-col">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">Recent Journeys</h2>
              <Button variant="ghost" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                View History
              </Button>
            </div>
            
            {data.recent_journeys.length === 0 ? (
              <div className="glass-card flex-1 flex flex-col items-center justify-center rounded-3xl p-10 text-muted-foreground">
                <Navigation size={48} className="mb-4 opacity-20" />
                <p className="font-medium text-lg">No recent journeys</p>
                <p className="text-sm">Plan a safe route to see history here.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {data.recent_journeys.map((j) => (
                  <ActivityRow 
                    key={j.id}
                    destination={j.destination} 
                    time={j.time} 
                    status={j.status} 
                    score={j.score} 
                  />
                ))}
              </div>
            )}
          </section>

          {/* System Health */}
          <section className="glass-card flex flex-col rounded-3xl p-6 relative overflow-hidden">
             <div className="flex items-center gap-2 mb-6">
               <Server size={20} className="text-primary" />
               <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-lg">System Health</h3>
             </div>
             <div className="flex flex-col gap-4">
                <HealthRow label="Backend Service" status={data.system_health.backend} />
                <HealthRow label="AI Coordinator" status={data.system_health.ai_agent} />
                <HealthRow label="API Latency" status={`${data.system_health.latency}ms`} neutral />
                <div className="mt-2 pt-4 border-t border-border/50">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Connected Providers</p>
                  <div className="flex flex-wrap gap-2">
                    {data.system_health.connected_providers.map(p => (
                      <span key={p} className="px-2 py-1 rounded bg-secondary text-xs font-medium text-foreground">{p}</span>
                    ))}
                  </div>
                </div>
             </div>
          </section>

        </div>

      </div>
    </div>
  );
}

// ---------------------------------------------------------
// Sub-components
// ---------------------------------------------------------

function MetricItem({ icon, label, value, color = "text-foreground" }: { icon: React.ReactNode, label: string, value: string, color?: string }) {
  return (
    <div className="flex flex-col gap-1.5 sm:border-l-2 sm:border-primary/20 sm:pl-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <div className="[&>svg]:h-4 [&>svg]:w-4">{icon}</div>
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <span className={`text-xl sm:text-2xl font-bold ${color}`}>{value}</span>
    </div>
  );
}

function ActivityRow({ destination, time, status, score }: { destination: string, time: string, status: string, score: number }) {
  return (
    <div className="glass-card flex items-center justify-between rounded-2xl p-5 group hover:border-primary/40 cursor-pointer">
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary text-primary transition-transform group-hover:scale-110">
          <MapPin size={20} />
        </div>
        <div className="flex flex-col">
          <span className="font-[family-name:var(--font-jakarta)] font-bold text-foreground text-lg">{destination}</span>
          <span className="flex items-center gap-1 text-sm text-muted-foreground">
            <Clock size={14} /> {time} &bull; {status}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex flex-col items-end mr-3 hidden sm:flex">
          <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Safety Score</span>
          <span className="font-bold text-success">{score}/100</span>
        </div>
        <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-colors text-muted-foreground">
          <ArrowRight size={16} />
        </div>
      </div>
    </div>
  );
}

function HealthRow({ label, status, neutral = false }: { label: string, status: string, neutral?: boolean }) {
  const isGood = status === 'Online' || status === 'Connected' || status === 'Optimal';
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {!neutral && (isGood ? <CheckCircle2 size={14} className="text-success" /> : <XCircle size={14} className="text-danger" />)}
        <span className={`text-sm font-bold ${neutral ? 'text-foreground' : isGood ? 'text-success' : 'text-danger'}`}>{status}</span>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex h-full w-full flex-col px-6 py-10 lg:px-12 animate-pulse">
      <div className="mx-auto flex w-full max-w-6xl flex-col space-y-10">
        <div className="flex justify-between items-end">
          <div>
            <div className="h-6 w-32 bg-secondary rounded-full mb-4"></div>
            <div className="h-10 w-64 bg-secondary rounded-xl mb-2"></div>
            <div className="h-5 w-80 bg-secondary rounded-lg"></div>
          </div>
          <div className="h-12 w-48 bg-secondary rounded-full"></div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          <div className="md:col-span-8 h-64 bg-secondary/50 rounded-3xl"></div>
          <div className="md:col-span-4 h-64 bg-secondary/50 rounded-3xl"></div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-80 bg-secondary/50 rounded-3xl"></div>
          <div className="h-80 bg-secondary/50 rounded-3xl"></div>
          <div className="h-80 bg-secondary/50 rounded-3xl"></div>
        </div>
      </div>
    </div>
  );
}