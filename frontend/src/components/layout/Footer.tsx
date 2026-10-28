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
                  className="h-9 w-auto object-contain dark:drop-shadow-[0_0_10px_rgba(255,255,255,0.55)] dark:brightness-110" 
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

        {/* Bottom Bar: Copyright, Helplines summary & Creator Credit */}
        <div className="mt-8 pt-6 border-t border-border/60 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] text-muted-foreground">
          <div className="flex flex-col sm:flex-row items-center gap-2 text-center sm:text-left">
            <p>
              &copy; {new Date().getFullYear()} NavSakhi &bull; Personal Software Project &bull; Decision-Support Platform for Commuter Safety.
            </p>
          </div>

          {/* Designed by Keshav Kumar with Social Profiles */}
          <div className="flex items-center gap-3 bg-secondary/50 px-3.5 py-1.5 rounded-full border border-border/70 text-foreground font-medium shadow-xs shrink-0 whitespace-nowrap">
            <span className="text-muted-foreground text-xs whitespace-nowrap">Designed by</span>
            <span className="font-bold text-foreground text-xs font-[family-name:var(--font-jakarta)] whitespace-nowrap">Keshav Kumar</span>
            <div className="h-3 w-px bg-border/80" />
            <div className="flex items-center gap-1.5 shrink-0">
              <a
                href="https://www.linkedin.com/in/keshavkumarofficial/"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Keshav Kumar on LinkedIn (opens in new tab)"
                className="p-1 rounded-md text-muted-foreground hover:text-[#0077b5] dark:hover:text-[#38a8e3] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                title="LinkedIn Profile"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/>
                </svg>
              </a>
              <a
                href="https://github.com/00keshav00"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Keshav Kumar on GitHub (opens in new tab)"
                className="p-1 rounded-md text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                title="GitHub Profile"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                  <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                </svg>
              </a>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <ShieldCheck size={13} /> Consent-Based Telemetry
            </span>
            <a
              href="tel:112"
              className="flex items-center gap-1 font-mono text-foreground font-semibold hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger rounded-md px-1 py-0.5 transition-colors"
              title="Direct telephone call to 112 National Emergency Helpline (India)"
              aria-label="Call 112 National Emergency Helpline"
            >
              <PhoneCall size={12} className="text-danger" /> 112 National Emergency
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
