"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { 
  Navigation, 
  Radio, 
  Users, 
  BookOpen, 
  MessageSquare, 
  Sparkles, 
  ShieldAlert, 
  ArrowRight, 
  Heart,
  Clock,
  RefreshCcw,
  AlertCircle,
  Activity,
  CheckCircle2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { RealWeatherCard } from "@/components/dashboard/RealWeatherCard";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuthStore } from "@/store/authStore";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export default function HomePage() {
  const { data, isLoading, error, refresh } = useDashboard();
  const user = useAuthStore((state) => state.user);
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Derive time-of-day greeting (deterministic on SSR and initial client hydration)
  const getGreeting = () => {
    if (!mounted) return "Welcome";
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
  };

  const rawName = user?.full_name || (user?.email ? user.email.split("@")[0] : "");
  const isGenericOrTest = !rawName || /test|admin|user\d+/i.test(rawName);
  const displayName = !mounted || isGenericOrTest ? "explorer" : rawName.split(" ")[0];

  return (
    <motion.div 
      className="flex-1 w-full min-h-full overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-7xl mx-auto"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      
      {/* 1. Floral Editorial Hero Banner with Verified Dark Contrast & Editorial Accent */}
      <motion.section 
        className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 lg:p-10 shadow-xs"
        variants={itemVariants}
      >
        {/* Soft Decorative Ambient Circles */}
        <div className="absolute -right-16 -top-16 w-64 h-64 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute right-32 -bottom-16 w-48 h-48 rounded-full bg-rose-200/30 dark:bg-primary/5 blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
              <Sparkles size={13} className="text-primary animate-pulse-soft" />
              <span>NavSakhi Intelligent Companion</span>
            </div>
            
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
              {getGreeting()}, <span className="text-primary">{displayName}!</span>
            </h1>
            
            <p className="text-sm sm:text-base text-muted-foreground font-medium">
              Stay aware, plan safer, keep exploring. Real-time safety corridors and environmental insights.
            </p>
          </div>

          {/* Official NavSakhi Identity & Operational Status */}
          <div className="md:max-w-sm shrink-0 p-3.5 sm:p-4 rounded-2xl bg-card/85 dark:bg-card/70 backdrop-blur-md border border-border/80 shadow-xs flex items-center gap-3.5">
            <div className="relative w-12 h-12 rounded-2xl overflow-hidden shrink-0 border border-primary/20 bg-primary/10 flex items-center justify-center p-2 shadow-xs">
              <Image 
                src="/images/navsakhi/navsakhi_emblem.png" 
                alt="NavSakhi Official Emblem" 
                width={34}
                height={34}
                className="object-contain"
              />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-foreground truncate">
                &ldquo;Safer Journeys &bull; Stronger Women&rdquo;
              </p>
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary/70" />
                <span>Safety Architecture &bull; System Ready</span>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      {/* 2. Main Two-Column Row: Real Weather Card + Quick Actions */}
      <motion.section 
        className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch"
        variants={itemVariants}
      >
        
        {/* Real Weather Dashboard Card (7 cols) */}
        <div className="lg:col-span-7 flex flex-col">
          <RealWeatherCard />
        </div>

        {/* Quick Actions Card (5 cols) */}
        <div className="lg:col-span-5 rounded-3xl border border-border/80 bg-card p-6 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span>Quick Actions</span>
            </h2>
            <span className="text-xs font-medium text-muted-foreground">Always accessible</span>
          </div>

          <div className="space-y-3 flex-1 flex flex-col justify-center">
            
            <Link href="/journey" className="group block">
              <div className="flex items-center justify-between p-3.5 rounded-2xl border border-border/70 bg-secondary/30 hover:bg-secondary hover:border-primary/40 transition-all duration-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/15 text-primary flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                    <Navigation size={18} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">Plan a Safe Journey</h3>
                    <p className="text-xs text-muted-foreground">Metro, Suburban, Bus &amp; walking legs</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            </Link>

            <Link href="/live" className="group block">
              <div className="flex items-center justify-between p-3.5 rounded-2xl border border-border/70 bg-secondary/30 hover:bg-secondary hover:border-primary/40 transition-all duration-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#EEE8FF] dark:bg-purple-950/40 text-purple-600 dark:text-purple-300 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                    <Radio size={18} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">Live Journey Monitor</h3>
                    <p className="text-xs text-muted-foreground">Active telemetry &amp; circular geofencing</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            </Link>

            <Link href="/assistant" className="group block">
              <div className="flex items-center justify-between p-3.5 rounded-2xl border border-border/70 bg-secondary/30 hover:bg-secondary hover:border-primary/40 transition-all duration-200">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-pink-500/15 text-pink-600 dark:text-pink-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                    <MessageSquare size={18} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-foreground">Ask AI Assistant</h3>
                    <p className="text-xs text-muted-foreground">Voice-enabled transit coordinator</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            </Link>

          </div>

          <div className="mt-4 pt-3 border-t border-border/60">
            <Link href="/emergency">
              <Button className="w-full rounded-2xl bg-danger hover:bg-danger/90 text-white font-bold h-11 gap-2 shadow-xs">
                <ShieldAlert size={18} />
                <span>One-Tap Emergency SOS</span>
              </Button>
            </Link>
          </div>
        </div>

      </motion.section>

      {/* 3. Core Capabilities Grid */}
      <motion.section 
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        variants={itemVariants}
      >
        
        {/* Multimodal Transit Card */}
        <Link href="/journey" className="group block">
          <div className="rounded-3xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between h-44 hover:border-primary/40 hover:shadow-md transition-all duration-200">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center group-hover:scale-105 transition-transform">
                <Navigation size={18} />
              </div>
              <h3 className="text-sm font-bold text-foreground">Multimodal Transit</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                238 verified corridor links across Metro, Suburban, and MTC buses.
              </p>
            </div>
            <div className="flex items-center text-xs font-semibold text-primary">
              <span>Plan Route</span>
              <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>

        {/* Live Tracking Card */}
        <Link href="/live" className="group block">
          <div className="rounded-3xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between h-44 hover:border-primary/40 hover:shadow-md transition-all duration-200">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-[#EEE8FF] dark:bg-purple-950/40 text-purple-600 dark:text-purple-300 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Radio size={18} />
              </div>
              <h3 className="text-sm font-bold text-foreground">Live Telemetry</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Consent-based tracking with encrypted WebSocket tickets.
              </p>
            </div>
            <div className="flex items-center text-xs font-semibold text-purple-600 dark:text-purple-400">
              <span>View Monitor</span>
              <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>

        {/* Community Reports Card */}
        <Link href="/community" className="group block">
          <div className="rounded-3xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between h-44 hover:border-primary/40 hover:shadow-md transition-all duration-200">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Users size={18} />
              </div>
              <h3 className="text-sm font-bold text-foreground">Community Network</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Verified safety reports on lighting, isolated stops, and safe spaces.
              </p>
            </div>
            <div className="flex items-center text-xs font-semibold text-rose-500">
              <span>Explore Reports</span>
              <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>

        {/* Resources & Helplines Card */}
        <Link href="/resources" className="group block">
          <div className="rounded-3xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between h-44 hover:border-primary/40 hover:shadow-md transition-all duration-200">
            <div className="space-y-2">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center group-hover:scale-105 transition-transform">
                <BookOpen size={18} />
              </div>
              <h3 className="text-sm font-bold text-foreground">Resources &amp; Helplines</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Zero FIR guide, 112/1091 helplines, and constitutional rights directory.
              </p>
            </div>
            <div className="flex items-center text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              <span>Open Directory</span>
              <ArrowRight size={14} className="ml-1 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>

      </motion.section>

      {/* 4. Safety Tips & Recent Activity Section */}
      <motion.section 
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
        variants={itemVariants}
      >
        
        {/* Safety Tip Banner (7 cols) */}
        <div className="lg:col-span-7 rounded-3xl border border-border/80 bg-gradient-to-br from-[#FFF7FA] via-card to-[#FDE8F0]/30 dark:from-[#251429] dark:via-card dark:to-[#351C3B]/40 p-6 shadow-xs flex flex-col sm:flex-row items-center gap-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-primary to-[#F6C8D7] flex items-center justify-center text-white shrink-0 shadow-sm">
            <Heart size={36} className="fill-white/30" />
          </div>
          <div className="space-y-1 text-center sm:text-left flex-1">
            <span className="text-[11px] font-bold text-primary uppercase tracking-wider">
              Safety Tip of the Day
            </span>
            <h4 className="text-base font-bold text-foreground">
              Travel along active, well-lit corridors
            </h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              When traveling after sunset, choose routes that incorporate high-frequency transit stops like Chennai Metro and busy MTC bus routes. Keep emergency contacts shared via Live Monitor.
            </p>
            <div className="pt-2">
              <Link href="/resources" className="text-xs font-bold text-primary hover:underline inline-flex items-center gap-1">
                View all tips &amp; safety guides <ArrowRight size={12} />
              </Link>
            </div>
          </div>
        </div>

        {/* System & Active Alerts (5 cols) */}
        <div className="lg:col-span-5 rounded-3xl border border-border/80 bg-card p-6 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Clock size={16} className="text-muted-foreground" />
              <span>Safety Status</span>
            </h3>
            <button
              type="button"
              onClick={refresh}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <RefreshCcw size={12} /> Refresh
            </button>
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-xs text-muted-foreground animate-pulse">
              Updating safety status...
            </div>
          ) : error ? (
            <div className="py-4 text-center text-xs text-muted-foreground flex flex-col items-center gap-1">
              <AlertCircle size={16} className="text-warning" />
              <span>Offline / cached mode active</span>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-2xl bg-secondary/40 border border-border/50">
                <span className="text-xs font-semibold text-foreground">AI Intelligence Coordinator</span>
                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full bg-emerald-500/10">
                  {data?.ai_status?.health || "Operational"}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-secondary/40 border border-border/50">
                <span className="text-xs font-semibold text-foreground">Chennai Multimodal Feeds</span>
                <span className="text-xs font-bold text-primary px-2 py-0.5 rounded-full bg-primary/10">
                  CMRL &bull; SRR &bull; MTC GTFS
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-secondary/40 border border-border/50">
                <span className="text-xs font-semibold text-foreground">Spatial Risk Architecture</span>
                <span className="text-xs font-bold text-foreground px-2 py-0.5 rounded-full bg-secondary">
                  LightGBM v2.0.0 (Frozen)
                </span>
              </div>
            </div>
          )}
        </div>

      </motion.section>

    </motion.div>
  );
}