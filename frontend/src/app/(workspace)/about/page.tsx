import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { 
  Sparkles, Compass, MapPin, ShieldCheck, Database, 
  Cpu, Radio, Bot, Users, CloudSun, ArrowRight, CheckCircle2 
} from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "About NavSakhi & How It Works",
  description: "Architecture, engineering pillars, and research mission behind the NavSakhi intelligent women's safety platform.",
};

export default function AboutPage() {
  const pillars = [
    {
      num: "01",
      title: "Multimodal Transit Graph",
      icon: <Compass className="text-primary" size={20} />,
      desc: "Integrates official Chennai Metro Rail (CMRL), Southern Railway Suburban EMU networks, and Metropolitan Transport Corporation (MTC) bus stops into a unified spatial routing engine.",
    },
    {
      num: "02",
      title: "LightGBM Spatial Safety Scoring",
      icon: <Cpu className="text-purple-500" size={20} />,
      desc: "Evaluates infrastructure proxy indicators — street lighting, commercial POI density, road class, and time of day — paired with TreeSHAP feature attribution to explain score factors.",
    },
    {
      num: "03",
      title: "Real Atmospheric Weather Engine",
      icon: <CloudSun className="text-amber-500" size={20} />,
      desc: "Fetches live Open-Meteo observations with 900-second positive caching, single-flight request coalescing, and transparent offline fallbacks.",
    },
    {
      num: "04",
      title: "Context-Aware AI Assistant",
      icon: <Bot className="text-emerald-500" size={20} />,
      desc: "Leverages Google Gemini 2.5 Flash with conversational history forwarding and safety-intent classification, supported by deterministic offline guidance.",
    },
    {
      num: "05",
      title: "Privacy-First Live Telemetry",
      icon: <Radio className="text-rose-500" size={20} />,
      desc: "Consent-driven GPS tracking with WebSocket session tickets. Geolocation is never polled silently or tracked without user consent.",
    },
    {
      num: "06",
      title: "Community Intelligence Hub",
      icon: <Users className="text-sky-500" size={20} />,
      desc: "Crowd-verified observations for streetlight outages, isolated stops, and safe public spaces, validated before publication.",
    },
  ];

  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 lg:p-10 shadow-xs space-y-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <Sparkles size={13} className="text-primary" />
            <span>Architecture &bull; Research Mission</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)] leading-tight">
            Safer Journeys for Every Woman, Grounded in Real Data.
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground font-medium leading-relaxed max-w-2xl">
            NavSakhi is an intelligent women&apos;s transit safety architecture designed to evaluate multimodal urban commuting corridors in Chennai through transparent spatial proxies, real-time weather, and privacy-first telemetry.
          </p>
        </section>

        {/* Project Genesis & Purpose */}
        <section className="space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Our Mission &amp; Approach
          </h2>
          <div className="p-6 rounded-3xl bg-card border border-border/80 space-y-3 text-xs sm:text-sm text-muted-foreground leading-relaxed">
            <p>
              Urban mobility remains an everyday challenge for millions of women across Indian metropolitan areas. Fear of poorly illuminated streets, isolated bus stops, or lack of emergency preparedness often restricts women&apos;s freedom of movement, education, and career opportunities.
            </p>
            <p>
              NavSakhi was conceived as an engineering exploration: <strong>Can we combine open transit timetables, spatial data science, machine learning risk proxies, and modern mobile web standards to give women clear, comparative safety awareness before they step out the door?</strong>
            </p>
            <p>
              Unlike generic turn-by-turn navigators that optimize solely for travel time, NavSakhi prioritizes high-frequency transit corridors, illuminated pathways, and safe commercial clusters, helping commuters make informed, confident choices.
            </p>
          </div>
        </section>

        {/* The 6 Engineering Pillars */}
        <section className="space-y-4">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
              How NavSakhi Works: Six Architectural Pillars
            </h2>
            <p className="text-xs text-muted-foreground">
              A breakdown of the core software and machine learning systems powering the platform.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pillars.map((p) => (
              <div key={p.num} className="p-5 rounded-2xl border border-border/80 bg-card flex flex-col justify-between hover:border-primary/40 transition-colors">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-primary">{p.num}</span>
                    <div className="p-2 rounded-xl bg-secondary/60">
                      {p.icon}
                    </div>
                  </div>
                  <h3 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">
                    {p.title}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {p.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Independent Prototype Context */}
        <section className="p-5 rounded-3xl bg-secondary/40 border border-border/70 space-y-2 text-xs text-muted-foreground leading-relaxed">
          <span className="font-bold text-foreground block text-sm">Independent Technology Prototype</span>
          <p>
            NavSakhi is an independent software project developed for commuter safety innovation and proactive spatial navigation. It is not affiliated with the Government of Tamil Nadu, Chennai Metro Rail Limited (CMRL), or Chennai City Police. Route calculations and scores are mathematical estimates for decision support.
          </p>
        </section>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/journey" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Try the Journey Planner <ArrowRight size={14} />
          </Link>
          <Link href="/limitations" className="text-xs font-bold text-muted-foreground hover:text-foreground">
            View AI &amp; ML Limitations &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
