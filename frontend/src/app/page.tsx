import Link from "next/link";
import { ShieldCheck, ArrowRight, Sparkles, Activity, Map, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex flex-col">
      {/* Dynamic Mesh Gradient Background */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-primary/10 blur-[100px] animate-aurora opacity-50 dark:opacity-30" />
        <div className="absolute top-[30%] -right-[10%] w-[40vw] h-[40vw] rounded-full bg-rose-gold/10 blur-[100px] animate-aurora opacity-50 dark:opacity-30" style={{ animationDelay: "-5s" }} />
      </div>

      {/* Premium Navigation */}
      <nav className="fixed top-0 w-full z-50 glass px-6 lg:px-12 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-iris text-white shadow-lg shadow-primary/25">
            <ShieldCheck size={20} />
          </div>
          <span className="text-xl font-[family-name:var(--font-jakarta)] font-bold tracking-tight text-foreground">
            Safe<span className="text-primary">She</span>
          </span>
        </div>
        <Link href="/home">
          <Button variant="outline" className="rounded-full px-6 border-border bg-background/50 backdrop-blur-md hover:bg-secondary transition-all">
            Open Workspace
          </Button>
        </Link>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 pt-32 pb-20 z-10">
        <div className="max-w-5xl mx-auto flex flex-col items-center text-center">
          
          <div className="animate-slide-up opacity-0" style={{ animationDelay: "0.1s" }}>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary mb-8">
              <Sparkles size={16} className="animate-pulse-soft" />
              Intelligence meets personal security
            </div>
          </div>

          <h1 className="animate-slide-up opacity-0 font-[family-name:var(--font-jakarta)] text-5xl md:text-7xl font-extrabold tracking-tight text-foreground leading-[1.1] mb-6" style={{ animationDelay: "0.2s" }}>
            Navigate the world with <br className="hidden md:block" />
            <span className="text-gradient-primary">absolute confidence.</span>
          </h1>

          <p className="animate-slide-up opacity-0 max-w-2xl text-lg md:text-xl text-muted-foreground font-light leading-relaxed mb-10" style={{ animationDelay: "0.3s" }}>
            SafeShe is a proactive AI telemetry platform. It anticipates risks, analyzes environmental data, and provides dynamic secure routing in real-time.
          </p>

          <div className="animate-slide-up opacity-0 flex flex-col sm:flex-row gap-4 w-full sm:w-auto" style={{ animationDelay: "0.4s" }}>
            <Link href="/home" className="w-full sm:w-auto">
              <Button size="lg" className="btn-premium w-full h-14 rounded-full px-8 text-base font-semibold bg-primary text-primary-foreground">
                Initialize Agent <ArrowRight size={18} className="ml-2" />
              </Button>
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="animate-slide-up opacity-0 grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl mt-32" style={{ animationDelay: "0.6s" }}>
          <FeatureCard icon={Activity} title="Live Telemetry" desc="Real-time environmental monitoring that dynamically reroutes if conditions shift." />
          <FeatureCard icon={Map} title="Neural Routing" desc="AI pathfinding optimized for lighting, historical data, and verified safe zones." />
          <FeatureCard icon={ShieldAlert} title="Instant SOS" desc="One-tap high-priority distress signaling to authorities and emergency contacts." />
        </div>
      </main>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }: { icon: any, title: string, desc: string }) {
  return (
    <div className="glass-card flex flex-col gap-4 rounded-3xl p-8 items-start text-left">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary text-primary">
        <Icon size={24} />
      </div>
      <h3 className="text-xl font-[family-name:var(--font-jakarta)] font-bold text-foreground">{title}</h3>
      <p className="text-muted-foreground leading-relaxed font-light">{desc}</p>
    </div>
  );
}