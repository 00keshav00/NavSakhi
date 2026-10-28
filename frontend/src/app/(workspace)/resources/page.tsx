"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Shield, PhoneCall, BookOpen, Scale, Bus, HeartHandshake, 
  ExternalLink, AlertTriangle, CheckCircle2, ChevronRight,
  Sparkles, Phone, ShieldCheck, Info, Compass, HelpCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Footer } from "@/components/layout/Footer";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export default function ResourcesPage() {
  const [activeTab, setActiveTab] = useState<"all" | "helplines" | "legal" | "guidelines">("all");

  const editorialCategories = [
    {
      id: "travel",
      title: "Safe Urban Travel & Preparedness",
      subtitle: "First-Mile to Last-Mile Transit Guidance",
      image: "/images/navsakhi/transit_women_platform.jpg",
      alt: "Women commuters navigating public transit together with clarity and confidence",
      description: "Proactive route selection, illuminated transit corridors, and safe telemetry sharing for evening commutes.",
      badge: "Travel Guide",
      badgeColor: "bg-primary/10 text-primary border-primary/20",
      actionText: "View Travel Guidelines",
      targetTab: "guidelines" as const,
    },
    {
      id: "station",
      title: "Public Transit & Station Awareness",
      subtitle: "CMRL Metro, EMU Suburban & MTC Bus Safety",
      image: "/images/navsakhi/metro_commuter_transit.jpg",
      alt: "Woman commuter checking route schedule on platform with arriving metro train",
      description: "Station wayfinding, women's reserved coach protocols, staffed counter locations, and platform security zones.",
      badge: "Transit Security",
      badgeColor: "bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/20",
      actionText: "Explore Station Protocols",
      targetTab: "guidelines" as const,
    },
    {
      id: "support",
      title: "Legal Rights & Emergency Advisory",
      subtitle: "Constitutional Safeguards & 24/7 Helplines",
      image: "/images/navsakhi/legal_aid_support.jpg",
      alt: "Scales of justice, legal consultation desk, and constitutional rights documentation",
      description: "Supreme Court guidelines, Zero FIR legal guarantees, arrest protections, and 24/7 emergency response contacts.",
      badge: "Legal Safeguards",
      badgeColor: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
      actionText: "View Legal Rights",
      targetTab: "legal" as const,
    },
  ];

  const emergencyHelplines = [
    { title: "National Women Helpline", number: "1091", desc: "24/7 dedicated toll-free helpline for women in distress." },
    { title: "National Emergency Service", number: "112", desc: "Unified emergency number for Police, Fire, and Ambulance." },
    { title: "Tamil Nadu Women Helpline", number: "181", desc: "Toll-free 24-hour telecom service for women affected by violence." },
    { title: "Chennai City Police SOS", number: "100", desc: "Immediate police response and nearest patrol dispatch." },
    { title: "MTC Bus Grievance & Safety", number: "1800 233 1234", desc: "Metropolitan Transport Corporation passenger safety helpline." },
    { title: "Chennai Metro Rail Helpline", number: "1860 425 1515", desc: "CMRL station security and commuter assistance." },
  ];

  const legalRights = [
    {
      title: "Right to Zero FIR",
      description: "A woman can lodge an FIR at any police station regardless of where the incident took place. The receiving station is legally required to register it and transfer it to the competent jurisdiction."
    },
    {
      title: "Right to Virtual / Electronic Complaints",
      description: "Under Delhi Police and Supreme Court guidelines adopted nationwide, if a woman cannot visit a police station in person, she can send a written complaint via registered post or email."
    },
    {
      title: "Arrest Rules for Women",
      description: "According to Section 46(4) of the CrPC, women cannot be arrested after sunset and before sunrise except in exceptional circumstances with prior permission from a Judicial Magistrate."
    },
    {
      title: "Privacy During Statement Recording",
      description: "Statements regarding sexual harassment or assault must be recorded by a woman police officer at the residence of the victim or a place of her choice in presence of legal assistance."
    }
  ];

  const travelTips = [
    {
      title: "Transit Selection",
      desc: "Prioritize routes with high-frequency stops such as Chennai Metro and designated MTC express bus corridors."
    },
    {
      title: "Telemetry Sharing",
      desc: "Before embarking on evening journeys, activate NavSakhi Live Monitor to stream verified GPS coordinates to your designated circle."
    },
    {
      title: "Emergency Quick Dial",
      desc: "Keep 112 on speed dial or use NavSakhi's prominent Emergency SOS button to broadcast instant location alerts."
    },
    {
      title: "Station Well-Lit Zones",
      desc: "Wait near station master booths, staffed ticket counters, or well-illuminated women's reserved coaches."
    }
  ];

  return (
    <div className="flex-1 w-full min-h-full overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8 max-w-7xl mx-auto">
      
      {/* Header Banner with High-Contrast Dark Gradient */}
      <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 lg:p-10 shadow-xs">
        <div className="max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <BookOpen size={13} className="text-primary" />
            <span>Knowledge &amp; Support Hub</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Women&apos;s Safety &amp; Legal Rights
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground font-medium leading-relaxed">
            Essential emergency helplines, constitutional legal safeguards, transit guidelines, and verified community assistance networks for women in Chennai and beyond.
          </p>
        </div>
      </section>

      {/* 1. Visual Editorial Category Showcase with Real Photography */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-foreground font-[family-name:var(--font-jakarta)] tracking-tight">
              Safety Knowledge &amp; Guidance
            </h2>
            <p className="text-xs text-muted-foreground font-medium mt-0.5">
              Curated visual guides covering everyday transit awareness, platform safety, and legal rights.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {editorialCategories.map((cat, idx) => (
            <motion.div 
              key={cat.id}
              className="editorial-frame bg-card flex flex-col justify-between group cursor-pointer"
              whileHover={{ y: -4 }}
              transition={{ duration: 0.3 }}
              onClick={() => setActiveTab(cat.targetTab)}
            >
              <div className="relative aspect-[16/10] w-full overflow-hidden bg-secondary/40">
                <Image 
                  src={cat.image}
                  alt={cat.alt}
                  fill
                  className="object-cover object-center transition-transform duration-700 group-hover:scale-105"
                  sizes="(max-width: 768px) 100vw, 33vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent pointer-events-none" />
                <div className="absolute top-3 left-3">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border backdrop-blur-md ${cat.badgeColor}`}>
                    {cat.badge}
                  </span>
                </div>
              </div>

              <div className="p-5 flex-1 flex flex-col justify-between space-y-3">
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                    {cat.subtitle}
                  </div>
                  <h3 className="font-bold text-foreground text-base sm:text-lg font-[family-name:var(--font-jakarta)] leading-snug group-hover:text-primary transition-colors">
                    {cat.title}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {cat.description}
                  </p>
                </div>

                <div className="pt-2 flex items-center justify-between text-xs font-bold text-primary group-hover:translate-x-1 transition-transform">
                  <span>{cat.actionText}</span>
                  <ChevronRight size={16} />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Navigation Filter Tabs */}
      <section className="flex flex-wrap items-center gap-2 border-b border-border/80 pb-3">
        <Button
          variant={activeTab === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("all")}
          className="rounded-full text-xs font-semibold px-4"
        >
          All Resources
        </Button>
        <Button
          variant={activeTab === "helplines" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("helplines")}
          className="rounded-full text-xs font-semibold px-4"
        >
          <PhoneCall size={14} className="mr-1.5" /> Emergency Helplines
        </Button>
        <Button
          variant={activeTab === "legal" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("legal")}
          className="rounded-full text-xs font-semibold px-4"
        >
          <Scale size={14} className="mr-1.5" /> Legal Rights &amp; Safeguards
        </Button>
        <Button
          variant={activeTab === "guidelines" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("guidelines")}
          className="rounded-full text-xs font-semibold px-4"
        >
          <Compass size={14} className="mr-1.5" /> Travel Guidelines
        </Button>
      </section>

      {/* 2. Emergency Helplines Grid with Clickable Phone Dialers */}
      {(activeTab === "all" || activeTab === "helplines") && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <PhoneCall size={20} className="text-danger" />
              <span>Verified Emergency Helplines</span>
            </h2>
            <span className="text-xs text-muted-foreground font-medium">Toll-Free &bull; 24/7 Available</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {emergencyHelplines.map((item) => {
              const cleanNumber = item.number.replace(/\s+/g, "");
              return (
                <div key={item.number} className="rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-primary/40 hover:shadow-md transition-all duration-200">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{item.title}</span>
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                    <a 
                      href={`tel:${cleanNumber}`}
                      className="text-2xl font-black text-foreground hover:text-primary tracking-tight font-[family-name:var(--font-jakarta)] block transition-colors"
                      title={`Click to call ${item.title}`}
                    >
                      {item.number}
                    </a>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 size={13} /> Verified Helpline
                    </span>
                    <a 
                      href={`tel:${cleanNumber}`}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-danger/10 text-danger text-xs font-bold hover:bg-danger/20 transition-colors"
                    >
                      <Phone size={12} /> Call Now
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 3. Constitutional & Legal Rights Section */}
      {(activeTab === "all" || activeTab === "legal") && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <Scale size={20} className="text-primary" />
              <span>Constitutional &amp; Legal Safeguards</span>
            </h2>
            <span className="text-xs text-muted-foreground font-medium">Supreme Court &amp; CrPC Provisions</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {legalRights.map((right) => (
              <div key={right.title} className="rounded-2xl border border-border/80 bg-card p-5 shadow-xs space-y-2 hover:border-primary/40 transition-colors">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                    <ShieldCheck size={16} />
                  </div>
                  <h3 className="font-bold text-foreground text-base font-[family-name:var(--font-jakarta)]">
                    {right.title}
                  </h3>
                </div>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed pl-8">
                  {right.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 4. Safe Urban Travel Guidelines */}
      {(activeTab === "all" || activeTab === "guidelines") && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <Bus size={20} className="text-[#8B5CF6]" />
              <span>Safe Urban Travel Guidelines</span>
            </h2>
            <span className="text-xs text-muted-foreground font-medium">Transit Best Practices</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {travelTips.map((tip, idx) => (
              <div key={tip.title} className="rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-primary/40 transition-colors">
                <div className="space-y-2">
                  <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                    {idx + 1}
                  </div>
                  <h4 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">
                    {tip.title}
                  </h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {tip.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Legal & Educational Disclaimer Notice */}
      <section className="p-4 rounded-2xl bg-secondary/40 border border-border/60 text-xs text-muted-foreground space-y-1">
        <div className="font-bold text-foreground flex items-center gap-1.5">
          <Info size={14} className="text-primary" />
          <span>Informational and Educational Directory</span>
        </div>
        <p className="leading-relaxed">
          The emergency contacts and legal rights compiled here are sourced from authoritative government bodies including the National Commission for Women (NCW), Tamil Nadu Police, and Indian Penal Code / CrPC statutes. In any active life-threatening situation, dial 112 immediately.
        </p>
      </section>

      {/* Official Footer with Disclosures & Navigation Links */}
      <Footer />

    </div>
  );
}
