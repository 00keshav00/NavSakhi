"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { 
  ShieldCheck, 
  Sparkles, 
  ArrowRight, 
  Activity, 
  MapPin, 
  Lock, 
  ShieldAlert, 
  Navigation, 
  CheckCircle2, 
  ChevronRight, 
  Users, 
  Radio, 
  CloudSun, 
  Compass,
  Bus,
  Train
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section, Container, Grid } from "@/components/ui/craft";
import { ContainerScroll } from "@/components/ui/container-scroll-animation";
import { ImagesScrollingAnimation } from "@/components/ui/images-scrolling-animation";
import { Reveal } from "@/components/ui/reveal";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const imageRevealVariants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.75, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export function LandingView() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background text-foreground flex flex-col">
      {/* Dynamic Ambient Background Glows */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[15%] -left-[10%] w-[55vw] h-[55vw] rounded-full bg-primary/10 blur-[130px] dark:bg-primary/5" />
        <div className="absolute top-[35%] -right-[10%] w-[45vw] h-[45vw] rounded-full bg-rose-200/25 dark:bg-primary/5 blur-[130px]" />
        <div className="absolute top-[75%] left-[20%] w-[40vw] h-[40vw] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      {/* Navigation Header */}
      <header className="sticky top-0 w-full z-50 glass border-b border-border/80 px-4 sm:px-8 py-3 flex items-center justify-between backdrop-blur-2xl">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="relative h-10 w-36 sm:w-44 flex items-center">
              <Image 
                src="/images/navsakhi/navsakhi_logo_official.png" 
                alt="NavSakhi - Safer Journeys • Stronger Women" 
                width={175} 
                height={56} 
                className="h-9 sm:h-10 w-auto object-contain" 
                priority 
              />
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm" className="rounded-full text-xs font-semibold px-4 text-muted-foreground hover:text-foreground">
              Sign In
            </Button>
          </Link>
          <Link href="/home">
            <Button size="sm" className="rounded-full px-5 text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/25">
              Open Workspace
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section: Craft UI-style Editorial Split Composition */}
      <Section className="pt-8 sm:pt-16 pb-12 z-10">
        <Container>
          <motion.div 
            className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center w-full"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Left Column: Headline, Copy & Actions (7 cols on lg) */}
            <motion.div className="lg:col-span-7 space-y-6 text-left" variants={itemVariants}>
              
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-primary shadow-xs">
                <Sparkles size={14} className="text-primary animate-pulse-soft" />
                <span>Intelligent Companion &bull; Multimodal Transit Security</span>
              </div>

              <h1 className="font-[family-name:var(--font-jakarta)] text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-foreground leading-[1.12]">
                Safer journeys for every woman, <br className="hidden sm:block" />
                <span className="text-gradient-primary">grounded in real transit data.</span>
              </h1>

              <p className="max-w-xl text-base sm:text-lg text-muted-foreground font-normal leading-relaxed">
                NavSakhi evaluates multimodal transit corridors across Chennai Metro, Suburban Rail, and MTC Buses. Using spatial risk proxy indicators and privacy-first live telemetry, it empowers you to commute with awareness, clarity, and peace of mind.
              </p>

              {/* Primary Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 w-full sm:w-auto">
                <Link href="/journey" className="w-full sm:w-auto">
                  <Button size="lg" className="btn-premium w-full sm:w-auto h-12 sm:h-14 rounded-full px-8 text-sm sm:text-base font-bold bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 transition-all">
                    <Navigation size={18} className="mr-2" /> Plan a Safe Journey
                  </Button>
                </Link>
                <Link href="/home" className="w-full sm:w-auto">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto h-12 sm:h-14 rounded-full px-8 text-sm sm:text-base font-bold border-border bg-card/80 hover:bg-secondary transition-all">
                    Explore Dashboard <ArrowRight size={18} className="ml-2" />
                  </Button>
                </Link>
              </div>

              {/* Trust Badges */}
              <div className="pt-4 flex flex-wrap items-center gap-4 sm:gap-6 text-xs text-muted-foreground font-medium">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 size={15} className="text-emerald-500" /> Real CMRL &amp; SRR Timetables
                </span>
                <span className="flex items-center gap-1.5">
                  <Lock size={15} className="text-primary" /> Consent-Based Geolocation
                </span>
                <span className="flex items-center gap-1.5">
                  <ShieldAlert size={15} className="text-rose-500" /> One-Tap Emergency SOS
                </span>
              </div>
            </motion.div>

            {/* Right Column: Prominent Editorial Hero Photography (5 cols on lg) */}
            <motion.div className="lg:col-span-5 relative" variants={imageRevealVariants}>
              <div className="editorial-frame relative aspect-[4/5] sm:aspect-[4/5] lg:aspect-[3/4] w-full max-w-md mx-auto">
                <Image 
                  src="/images/navsakhi/transit_commuter_navigating.jpg"
                  alt="Woman commuter checking route directions and navigating city transit with confidence"
                  fill
                  priority
                  className="object-cover object-center transition-transform duration-700 hover:scale-105"
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 45vw, 500px"
                />
                {/* Subtle Ambient Vignette Overlay - dark translucent to preserve photo clarity */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent pointer-events-none" />

                {/* Floating Glass Badge over Photo */}
                <div className="absolute bottom-4 left-4 right-4 p-4 rounded-2xl glass border border-white/20 dark:border-white/10 shadow-lg backdrop-blur-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-primary/20 text-primary flex items-center justify-center shrink-0">
                      <Activity size={20} className="animate-pulse" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-foreground truncate">
                        Multimodal Transit Network
                      </div>
                      <div className="text-[11px] text-muted-foreground truncate">
                        Suburban Rail &bull; Metro &bull; MTC Feeder Buses
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </Container>
      </Section>

      {/* Photographic Infinite Scroll Animation (ImagesScrollingAnimation) */}
      <section className="w-full border-y border-border/50 bg-secondary/20 py-4">
        <Container>
          <div className="text-center max-w-xl mx-auto mb-2">
            <span className="text-[11px] font-bold text-primary uppercase tracking-widest">
              Live Urban Journeys
            </span>
            <p className="text-xs text-muted-foreground mt-1">
              Real transit environments, well-lit station platforms, and active commuter networks.
            </p>
          </div>
          <ImagesScrollingAnimation speed={32} />
        </Container>
      </section>

      {/* Interactive Showcase: ContainerScroll Animation - Tightened vertical rhythm */}
      <Section className="py-4 sm:py-8">
        <Container>
          <ContainerScroll
            titleComponent={
              <div className="space-y-3">
                <span className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
                  <Compass size={13} className="text-primary" />
                  Interactive Journey Intelligence
                </span>
                <h2 className="text-2xl sm:text-4xl lg:text-5xl font-black text-foreground font-[family-name:var(--font-jakarta)] tracking-tight">
                  Experience Safety-First Routing <br className="hidden sm:block" />
                  <span className="text-gradient-primary">Before You Step Outside</span>
                </h2>
                <p className="text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto">
                  Scroll to preview NavSakhi&apos;s multimodal search interface, LightGBM spatial risk scoring, and verified transit connections.
                </p>
              </div>
            }
          >
            <div className="relative aspect-[16/10] sm:aspect-[16/9] w-full overflow-hidden bg-muted">
              <Image
                src="/images/navsakhi/showcase_journey_preview.png"
                alt="NavSakhi SafeJourney Multimodal Planner Preview showing route scoring and map"
                fill
                sizes="(max-width: 1200px) 100vw, 1200px"
                className="object-cover object-top"
                priority
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
              <div className="absolute bottom-4 left-6 right-6 flex items-center justify-between text-xs text-foreground font-semibold">
                <span className="flex items-center gap-2 bg-background/80 px-3 py-1.5 rounded-full border border-border/80 backdrop-blur-md">
                  <Compass size={13} className="text-primary" /> Interactive journey planner preview
                </span>
                <Link href="/journey">
                  <Button size="sm" className="rounded-full h-8 px-4 text-xs font-bold bg-primary text-primary-foreground shadow-sm">
                    Open Journey Planner <ArrowRight size={13} className="ml-1" />
                  </Button>
                </Link>
              </div>
            </div>
          </ContainerScroll>
        </Container>
      </Section>

      {/* Feature Narrative 1: Multimodal Urban Travel with Photography & Reveal */}
      <Section className="py-8 sm:py-16">
        <Container>
          <Reveal index={0}>
            <div className="rounded-3xl border border-border/80 hero-gradient p-6 sm:p-10 shadow-xl overflow-hidden">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                
                <div className="lg:col-span-6 space-y-4 text-left">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary">
                    <Compass size={13} className="text-primary" />
                    <span>Multimodal Transit Intelligence</span>
                  </div>
                  <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-foreground font-[family-name:var(--font-jakarta)] leading-tight">
                    Seamless Connections Across Rail, Bus &amp; Walking Legs
                  </h2>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    NavSakhi eliminates disconnected transit journeys. Instead of declaring trips impossible when direct lines don&apos;t exist, our multimodal coordinator connects Chennai Metro and Suburban Rail with MTC feeder buses and verified walking segments.
                  </p>
                  <div className="pt-2 grid grid-cols-2 gap-3 text-xs font-semibold text-foreground">
                    <div className="p-3 rounded-xl bg-card border border-border/60 flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-[#8B5CF6] shrink-0" />
                      <span>CMRL Metro Rail</span>
                    </div>
                    <div className="p-3 rounded-xl bg-card border border-border/60 flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-[#3B82F6] shrink-0" />
                      <span>Suburban EMU Rail</span>
                    </div>
                    <div className="p-3 rounded-xl bg-card border border-border/60 flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-[#10B981] shrink-0" />
                      <span>MTC Government Bus</span>
                    </div>
                    <div className="p-3 rounded-xl bg-card border border-border/60 flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-[#EAB308] shrink-0" />
                      <span>Verified Walk Links</span>
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-6">
                  <div className="editorial-frame relative aspect-[16/10] sm:aspect-[16/9] w-full">
                    <Image 
                      src="/images/navsakhi/metro_commuter_transit.jpg"
                      alt="Woman commuter checking route schedule on platform with arriving metro train"
                      fill
                      className="object-cover object-center transition-transform duration-700 hover:scale-105"
                      sizes="(max-width: 1024px) 100vw, 550px"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
                    <div className="absolute bottom-3 left-4 text-xs font-medium text-white drop-shadow-sm">
                      Station platforms &bull; Rapid transit network synchronization
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </Reveal>
        </Container>
      </Section>

      {/* How It Works 3-Step Section with Reveal */}
      <Section className="py-6 sm:py-10 text-center">
        <Container>
          <Reveal index={0}>
            <div className="space-y-2 mb-10 max-w-xl mx-auto">
              <span className="text-xs font-bold text-primary uppercase tracking-widest">Architecture</span>
              <h2 className="text-2xl sm:text-4xl font-extrabold text-foreground font-[family-name:var(--font-jakarta)]">
                How NavSakhi Protects Your Commute
              </h2>
              <p className="text-sm text-muted-foreground">
                Three coordinated layers of intelligence designed specifically for women traveling independently.
              </p>
            </div>
          </Reveal>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <Reveal index={1}>
              <div className="h-full rounded-3xl border border-border/80 bg-card p-6 shadow-xs flex flex-col justify-between space-y-4 hover:border-primary/40 hover:shadow-md transition-all duration-300">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-black text-lg">
                  1
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="font-bold text-foreground text-lg font-[family-name:var(--font-jakarta)]">
                    Multimodal Journey Engine
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Searches authentic GTFS timetables across Chennai Metro and Southern Railway with connecting MTC buses to deliver realistic, low-risk routes without excessive detours.
                  </p>
                </div>
                <div className="text-xs font-semibold text-primary flex items-center gap-1 pt-2 border-t border-border/40">
                  <span>Timetable-verified</span> &bull; <span>Transfer-aware</span>
                </div>
              </div>
            </Reveal>

            <Reveal index={2}>
              <div className="h-full rounded-3xl border border-border/80 bg-card p-6 shadow-xs flex flex-col justify-between space-y-4 hover:border-primary/40 hover:shadow-md transition-all duration-300">
                <div className="w-12 h-12 rounded-2xl bg-[#EEE8FF] dark:bg-purple-950/40 text-purple-600 dark:text-purple-300 flex items-center justify-center font-black text-lg">
                  2
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="font-bold text-foreground text-lg font-[family-name:var(--font-jakarta)]">
                    Environmental Risk Proxy
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Our validated LightGBM model scores candidate road segments based on street lighting, verified police/hospital proximity, and spatial features without fabricating crime forecasts.
                  </p>
                </div>
                <div className="text-xs font-semibold text-purple-600 dark:text-purple-400 flex items-center gap-1 pt-2 border-t border-border/40">
                  <span>LightGBM v2.0.0</span> &bull; <span>Strict disclosures</span>
                </div>
              </div>
            </Reveal>

            <Reveal index={3}>
              <div className="h-full rounded-3xl border border-border/80 bg-card p-6 shadow-xs flex flex-col justify-between space-y-4 hover:border-primary/40 hover:shadow-md transition-all duration-300">
                <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center font-black text-lg">
                  3
                </div>
                <div className="space-y-2 flex-1">
                  <h3 className="font-bold text-foreground text-lg font-[family-name:var(--font-jakarta)]">
                    Privacy-First Live Monitoring
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Active journey tracking operates exclusively with explicit device location consent. Encrypted telemetry can be shared with your trusted emergency contacts alongside instant SOS.
                  </p>
                </div>
                <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1 pt-2 border-t border-border/40">
                  <span>Zero background snooping</span> &bull; <span>One-tap SOS</span>
                </div>
              </div>
            </Reveal>
          </div>
        </Container>
      </Section>

      {/* Feature Narrative 2: Community Solidarity with Photography & Reveal */}
      <Section className="py-6 sm:py-10">
        <Container>
          <Reveal index={0}>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              
              <div className="lg:col-span-6 order-2 lg:order-1">
                <div className="editorial-frame relative aspect-[16/11] w-full">
                  <Image 
                    src="/images/navsakhi/transit_women_platform.jpg"
                    alt="Two women commuters navigating railway platform together with clarity and confidence"
                    fill
                    className="object-cover object-center transition-transform duration-700 hover:scale-105"
                    sizes="(max-width: 1024px) 100vw, 550px"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
                  <div className="absolute bottom-3 left-4 text-xs font-medium text-white drop-shadow-sm">
                    Safety in solidarity &bull; Transit Community Observations
                  </div>
                </div>
              </div>

              <div className="lg:col-span-6 space-y-4 text-left order-1 lg:order-2">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-500">
                  <Users size={13} className="text-rose-500" />
                  <span>Community Solidarity</span>
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-foreground font-[family-name:var(--font-jakarta)] leading-tight">
                  Collective Awareness Across Everyday Routes
                </h2>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  NavSakhi connects travelers through crowd-verified safety observations: street light outages, isolated bus stops, active transit patrol presence, and safe community shelters. Every report is audited and verified before publication.
                </p>
                <div className="pt-2">
                  <Link href="/community">
                    <Button variant="outline" className="rounded-full px-6 font-semibold border-border hover:bg-secondary">
                      View Community Reports <ChevronRight size={16} className="ml-1" />
                    </Button>
                  </Link>
                </div>
              </div>

            </div>
          </Reveal>
        </Container>
      </Section>

      {/* Core Capabilities Grid with Reveal */}
      <Section className="py-6 sm:py-10 text-center">
        <Container>
          <Reveal index={0}>
            <div className="space-y-2 mb-10 max-w-xl mx-auto">
              <span className="text-xs font-bold text-primary uppercase tracking-widest">Capabilities</span>
              <h2 className="text-2xl sm:text-4xl font-extrabold text-foreground font-[family-name:var(--font-jakarta)]">
                Core Modules Designed for Daily Travel
              </h2>
            </div>
          </Reveal>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left">
            <Reveal index={1}>
              <div className="h-full rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-primary/40 transition-colors">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                    <CloudSun size={20} />
                  </div>
                  <h4 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">Real Weather Dashboard</h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    Open-Meteo observations, hourly forecasts, and honest nighttime UV indicators.
                  </p>
                </div>
                <Link href="/home" className="mt-4 text-xs font-bold text-primary hover:underline">
                  View weather &rarr;
                </Link>
              </div>
            </Reveal>

            <Reveal index={2}>
              <div className="h-full rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-purple-400/40 transition-colors">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-[#EEE8FF] dark:bg-purple-950/40 text-purple-600 dark:text-purple-300 flex items-center justify-center mb-3">
                    <Radio size={20} />
                  </div>
                  <h4 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">Live Location Monitor</h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    Real-time telemetry companion with authenticated WebSocket session tickets.
                  </p>
                </div>
                <Link href="/live" className="mt-4 text-xs font-bold text-purple-600 dark:text-purple-400 hover:underline">
                  Open monitor &rarr;
                </Link>
              </div>
            </Reveal>

            <Reveal index={3}>
              <div className="h-full rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-rose-400/40 transition-colors">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-500 flex items-center justify-center mb-3">
                    <ShieldAlert size={20} />
                  </div>
                  <h4 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">Emergency SOS Hub</h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    Rapid location sharing with emergency contacts and verified 112/1091 national helplines.
                  </p>
                </div>
                <Link href="/emergency" className="mt-4 text-xs font-bold text-rose-600 dark:text-rose-400 hover:underline">
                  Emergency options &rarr;
                </Link>
              </div>
            </Reveal>

            <Reveal index={4}>
              <div className="h-full rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-emerald-400/40 transition-colors">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3">
                    <Users size={20} />
                  </div>
                  <h4 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">Resources &amp; Rights</h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    Constitutional legal safeguards, Zero FIR guide, and safety knowledge directory.
                  </p>
                </div>
                <Link href="/resources" className="mt-4 text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline">
                  Browse resources &rarr;
                </Link>
              </div>
            </Reveal>
          </div>
        </Container>
      </Section>

      {/* Footer with Official Brand Identity */}
      <footer className="border-t border-border/80 bg-card/60 backdrop-blur-md px-4 sm:px-8 py-8 text-center text-xs text-muted-foreground space-y-3">
        <div className="flex items-center justify-center gap-2">
          <div className="relative h-8 w-32 flex items-center justify-center">
            <Image 
              src="/images/navsakhi/navsakhi_logo_official.png" 
              alt="NavSakhi Logo" 
              width={140} 
              height={45} 
              className="h-7 w-auto object-contain" 
            />
          </div>
        </div>
        <p className="max-w-md mx-auto">
          NavSakhi &bull; Personal Software Project &amp; Working Prototype &bull; Multimodal Chennai Transit Routing &bull; Environmental Risk Proxies.
        </p>
      </footer>
    </div>
  );
}
