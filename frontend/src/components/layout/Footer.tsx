"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { 
  ShieldCheck, AlertTriangle, PhoneCall, Heart, 
  ExternalLink, Sparkles, Scale, Info
} from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-border/80 bg-card/60 backdrop-blur-xl text-foreground shrink-0 mt-auto">
      {/* Top Banner: Prominent Prototype & Emergency Disclosures */}
      <div className="border-b border-border/60 bg-secondary/30 px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            <span className="font-bold text-foreground">Prototype Decision-Support Tool:</span>
            <span>Predictions &amp; scores are estimates, not guarantees.</span>
          </div>
          <div className="flex items-center gap-2 text-danger font-bold">
            <AlertTriangle size={14} className="shrink-0" />
            <span>Real Emergency in India? Dial 112 (National ERSS) or 1091 (Women Helpline)</span>
          </div>
        </div>
      </div>

      {/* Main Footer Links & Branding */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          
          {/* Col 1 & 2: Brand, Identity, Scope */}
          <div className="lg:col-span-2 space-y-4">
            <Link href="/" className="inline-block">
              <div className="relative h-10 w-44 flex items-center">
                <Image 
                  src="/images/navsakhi/navsakhi_logo_official.png" 
                  alt="NavSakhi - Safer Journeys • Stronger Women" 
                  width={175} 
                  height={56} 
                  className="h-9 w-auto object-contain" 
                />
              </div>
            </Link>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-sm">
              NavSakhi is an independent software research prototype exploring multimodal transit routing, spatial safety proxies, and privacy-first live telemetry for women commuters in Chennai.
            </p>
            <div className="p-3 rounded-2xl bg-secondary/40 border border-border/60 text-[11px] text-muted-foreground space-y-1">
              <span className="font-bold text-foreground block flex items-center gap-1.5">
                <Info size={13} className="text-primary" /> Notice on Human Monitoring
              </span>
              <p>
                NavSakhi provides client-side decision support. It does not operate a 24/7 human dispatch center, private patrol fleet, or automated police integration.
              </p>
            </div>
          </div>

          {/* Col 3: Platform Navigation */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-[family-name:var(--font-jakarta)]">
              Platform
            </h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link href="/home" className="hover:text-primary transition-colors">
                  Dashboard
                </Link>
              </li>
              <li>
                <Link href="/journey" className="hover:text-primary transition-colors">
                  Journey Planner
                </Link>
              </li>
              <li>
                <Link href="/live" className="hover:text-primary transition-colors">
                  Live Telemetry Monitor
                </Link>
              </li>
              <li>
                <Link href="/community" className="hover:text-primary transition-colors">
                  Community Intelligence
                </Link>
              </li>
              <li>
                <Link href="/assistant" className="hover:text-primary transition-colors">
                  AI Safety Assistant
                </Link>
              </li>
              <li>
                <Link href="/emergency" className="hover:text-danger transition-colors font-bold flex items-center gap-1 text-danger">
                  <span className="w-1.5 h-1.5 rounded-full bg-danger animate-ping" />
                  Emergency SOS Hub
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Knowledge & Safety */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-[family-name:var(--font-jakarta)]">
              Safety &amp; Guidance
            </h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link href="/about" className="hover:text-primary transition-colors">
                  About &amp; How It Works
                </Link>
              </li>
              <li>
                <Link href="/safety-guidelines" className="hover:text-primary transition-colors">
                  Safety Guidelines &amp; SOS
                </Link>
              </li>
              <li>
                <Link href="/resources" className="hover:text-primary transition-colors">
                  Legal Rights &amp; Helplines
                </Link>
              </li>
              <li>
                <Link href="/help" className="hover:text-primary transition-colors">
                  Help, Support &amp; FAQ
                </Link>
              </li>
              <li>
                <Link href="/accessibility" className="hover:text-primary transition-colors">
                  Accessibility Statement
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 5: Transparency & Disclosures */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-foreground uppercase tracking-wider font-[family-name:var(--font-jakarta)]">
              Legal &amp; Policy
            </h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <Link href="/limitations" className="hover:text-primary transition-colors font-semibold text-foreground">
                  AI &amp; ML Limitations
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-primary transition-colors">
                  Terms &amp; Conditions
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-primary transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/settings" className="hover:text-primary transition-colors">
                  Account Settings &amp; Data
                </Link>
              </li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar: Copyright & Helplines summary */}
        <div className="mt-8 pt-6 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-muted-foreground">
          <p>
            &copy; {new Date().getFullYear()} NavSakhi &bull; Personal Software Project &amp; Prototype &bull; Developed for academic &amp; demonstration purposes.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <ShieldCheck size={13} /> Consent-Based Telemetry
            </span>
            <span className="flex items-center gap-1 font-mono text-foreground font-semibold">
              <PhoneCall size={12} className="text-danger" /> 112 National Emergency
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
