import type { Metadata } from "next";
import Link from "next/link";
import { 
  HelpCircle, MessageSquare, AlertCircle, CheckCircle2, 
  ExternalLink, Bug, Shield, LifeBuoy, ArrowRight, Info 
} from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Help, Feedback & Support",
  description: "Frequently asked questions, troubleshooting guidance, and feedback reporting for the NavSakhi platform.",
};

export default function HelpPage() {
  const faqs = [
    {
      q: "How does NavSakhi calculate the Safety Score for a route?",
      a: "NavSakhi evaluates multi-factor spatial proxies along each transit corridor segment: operational CMRL metro station proximity, commercial Point of Interest (POI) density, road functional classification (arterial vs isolated lanes), estimated street illumination, and nighttime activity dampening. A LightGBM gradient-boosted decision model aggregates these features into a normalized 0–100 score.",
    },
    {
      q: "Does Live Journey Tracking alert the police automatically?",
      a: "No. NavSakhi is a client-side decision-support tool, not an automated police dispatch system. Live tracking coordinates your journey timeline with pre-staged emergency contacts. Adding emergency contacts stores them for quick dialing and manual device sharing, but NavSakhi does not automatically send SMS or background messages. In an actual emergency, you must dial 112 directly or use the Emergency SOS screen to share your live coordinates with your trusted contacts via your device's native share sheet.",
    },
    {
      q: "Can I use NavSakhi without creating an account?",
      a: "Yes! You can explore transit corridors, plan routes, check weather, view safety scores, and browse resources completely anonymously as a Guest Explorer. An account is only required if you wish to persist your personal profile, configure saved emergency contacts, or sync live monitor sessions across devices.",
    },
    {
      q: "What happens to my journey search if I sign in midway?",
      a: "NavSakhi automatically saves your selected journey route, origin, destination, and preferences in your browser's session storage (valid for 30 minutes). When you complete sign-in, your route is seamlessly restored without requiring you to re-type addresses. Tracking will not start until you explicitly click 'Start Monitored Journey'.",
    },
    {
      q: "Why does the weather card occasionally say 'Atmospheric telemetry offline'?",
      a: "NavSakhi fetches live observations from Open-Meteo. To protect against upstream provider rate limits (HTTP 429), our backend implements a 900-second positive cache and a 30-second negative cooldown. When the provider is rate-limited, NavSakhi truthfully indicates an offline state rather than fabricating fake forecasts.",
    },
    {
      q: "How do I update or delete my emergency contacts?",
      a: "Navigate to Account Settings (/settings). Under the Emergency Contacts section, you can add new contacts (with international country codes), edit existing contact details, designate a primary contact, or permanently delete contacts with single-click confirmation.",
    },
    {
      q: "Is my GPS location shared in the background?",
      a: "Never. NavSakhi adheres to strict privacy-by-design principles. Location coordinates are queried only when you deliberately interact with location features (such as clicking 'Use My Location' or 'Start Monitored Journey'). When a journey ends or the tab is closed, geolocation polling ceases immediately.",
    },
  ];

  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <HelpCircle size={13} className="text-primary" />
            <span>Support &bull; Knowledge Base</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Help, Feedback &amp; Support
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Frequently asked questions, transit troubleshooting, and how to report issues or suggest improvements.
          </p>
        </section>

        {/* FAQs Section */}
        <section className="space-y-4">
          <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Frequently Asked Questions
          </h2>
          <div className="space-y-3">
            {faqs.map((faq, idx) => (
              <div key={idx} className="p-5 rounded-2xl bg-card border border-border/80 space-y-2 hover:border-primary/30 transition-colors">
                <h3 className="font-bold text-foreground text-sm sm:text-base flex items-start gap-2">
                  <span className="text-primary font-mono text-xs mt-1 shrink-0">Q{idx + 1}.</span>
                  <span>{faq.q}</span>
                </h3>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed pl-6">
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Feedback & Bug Reporting */}
        <section className="space-y-4">
          <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Reporting Issues &amp; Contributing Feedback
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-card border border-border/80 space-y-2.5">
              <div className="flex items-center gap-2 text-primary font-bold text-sm">
                <Bug size={17} />
                <span>Technical Bugs &amp; Route Errors</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Notice an inaccurate bus stop location, broken map tile, or application glitch? Submit an issue on our GitHub repository with steps to reproduce. <strong>(Note: The issue tracker is public. Never post passwords, phone numbers, or emergency contact details in public bug reports.)</strong>
              </p>
              <a 
                href="https://github.com/00keshav00/NavSakhi/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline pt-1"
              >
                <span>Open an issue on GitHub</span>
                <ExternalLink size={12} />
              </a>
            </div>

            <div className="p-5 rounded-2xl bg-card border border-border/80 space-y-2.5">
              <div className="flex items-center gap-2 text-rose-500 font-bold text-sm">
                <MessageSquare size={17} />
                <span>Community &amp; Safety Observations</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Have verified information about streetlight outages, unlit pathways, or active security patrols in Chennai transit hubs? Share them directly in the Community tab.
              </p>
              <Link 
                href="/community"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline pt-1"
              >
                <span>View Community Hub &rarr;</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Emergency Helplines Reminder */}
        <section className="p-5 rounded-3xl bg-secondary/40 border border-border/70 text-xs text-muted-foreground space-y-1.5">
          <span className="font-bold text-foreground block text-sm flex items-center gap-1.5">
            <LifeBuoy size={15} className="text-danger" /> Life-Threatening Emergencies
          </span>
          <p className="leading-relaxed">
            Please do not use the feedback form or GitHub issue tracker to report active crimes, harassment, or medical emergencies. In any urgent situation in India, call <strong>112 (National ERSS)</strong> or <strong>1091 (Women Helpline)</strong> immediately.
          </p>
        </section>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/safety-guidelines" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Official Safety Guidelines <ArrowRight size={14} />
          </Link>
          <Link href="/about" className="text-xs font-bold text-muted-foreground hover:text-foreground">
            About NavSakhi Architecture &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
