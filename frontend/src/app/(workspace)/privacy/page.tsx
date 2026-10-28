import type { Metadata } from "next";
import Link from "next/link";
import { Lock, ShieldCheck, Database, Eye, Trash2, ArrowRight, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Privacy policy detailing data collection, processing, storage, and retention practices for NavSakhi.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <Lock size={13} className="text-primary" />
            <span>Privacy Architecture &bull; Transparent Data Practices</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Privacy Policy
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Effective Date: October 2026 &bull; Scope: NavSakhi Prototype Application
          </p>
        </section>

        {/* Core Privacy Principles Callout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
              <ShieldCheck size={16} /> Consent-First Geolocation
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              GPS coordinates are polled only upon deliberate user action. Never polled secretly or in the background.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
            <div className="flex items-center gap-2 text-emerald-500 font-bold text-xs uppercase tracking-wider">
              <Database size={16} /> Bcrypt Password Hashing
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Account passwords are cryptographically hashed before saving. Plaintext passwords are never stored.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
            <div className="flex items-center gap-2 text-rose-500 font-bold text-xs uppercase tracking-wider">
              <Eye size={16} /> Guest Explorer Mode
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Route planning and safety scoring do not require an account. Drafts stay on your device in session storage.
            </p>
          </div>
        </div>

        {/* Detailed Data Inventory */}
        <div className="space-y-6 text-xs sm:text-sm text-muted-foreground leading-relaxed">
          
          {/* 1. Information Collected */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">01.</span>
              <span>Information We Collect &amp; Process</span>
            </h2>
            <p>
              NavSakhi collects only the minimum necessary information required to compute transit safety scores and facilitate user-directed safety features:
            </p>
            
            <div className="overflow-x-auto rounded-2xl border border-border/70 bg-card">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-secondary/40 text-foreground font-bold">
                    <th className="p-3">Data Category</th>
                    <th className="p-3">Specific Fields</th>
                    <th className="p-3">Storage Location</th>
                    <th className="p-3">Purpose</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-muted-foreground">
                  <tr>
                    <td className="p-3 font-semibold text-foreground">Account Profile</td>
                    <td className="p-3">Full name, email, hashed password, optional phone number, optional age</td>
                    <td className="p-3 font-mono text-[11px]">MongoDB (users collection)</td>
                    <td className="p-3">Authentication, personal settings, and display</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-foreground">Emergency Contacts</td>
                    <td className="p-3">Contact name, relationship, phone number, optional email, primary flag</td>
                    <td className="p-3 font-mono text-[11px]">MongoDB (user.contacts subdocument)</td>
                    <td className="p-3">Pre-staging contact details for quick manual dialing and client-side device sharing; no automated background dispatch is performed.</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-foreground">Journey Planning Drafts</td>
                    <td className="p-3">Origin, destination, route preferences, selected route ID</td>
                    <td className="p-3 font-mono text-[11px]">Browser sessionStorage (30-min TTL)</td>
                    <td className="p-3">Route restoration across sign-in; never saved to backend for guests</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-foreground">Live Telemetry</td>
                    <td className="p-3">Latitude, longitude, speed, heading (only while tracking)</td>
                    <td className="p-3 font-mono text-[11px]">WebSocket ephemeral session state</td>
                    <td className="p-3">Real-time corridor synchronization and timeline progress</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-semibold text-foreground">AI Chat Messages</td>
                    <td className="p-3">User questions and conversation history</td>
                    <td className="p-3 font-mono text-[11px]">Ephemeral request context</td>
                    <td className="p-3">Generating contextual safety guidance via Gemini</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* 2. Third-Party Services */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">02.</span>
              <span>Third-Party Service Providers</span>
            </h2>
            <p>
              NavSakhi interfaces with external APIs to deliver routing, atmospheric conditions, and AI guidance. Each provider receives only the technical parameters necessary to fulfill the request:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Open-Meteo:</strong> Receives geographic coordinates (lat/lng) to return weather conditions. Open-Meteo does not receive personal identifiers, names, or contact info. Responses are cached locally (900s positive / 30s negative) to respect rate limits.
              </li>
              <li>
                <strong>OpenStreetMap / Nominatim / OSRM:</strong> Receives search text and transit coordinates for geocoding and pedestrian pathfinding. No user identifiers are transmitted.
              </li>
              <li>
                <strong>Google Gemini API:</strong> When configured, user queries and conversation context are transmitted to the Google Gemini API (governed by Google developer terms) to generate contextual assistance. Passwords, ages, and emergency contact lists are never forwarded to Gemini.
              </li>
            </ul>
          </section>

          {/* 3. Emergency Contacts & SOS Sharing */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">03.</span>
              <span>Emergency Points of Contact (POC) Handling</span>
            </h2>
            <p>
              Emergency contacts designated in your Account Settings are stored strictly for your personal use. NavSakhi does not:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Sell, trade, or distribute your emergency contacts to third-party data brokers.</li>
              <li>Send unsolicited automated text messages, promotional SMS, or robocalls to your contacts.</li>
              <li>Dispatch automated background SMS alerts or telephone calls to contacts during an emergency; contacts are saved solely for quick manual dialing and device sharing.</li>
              <li>Share contacts across user accounts; strict authorization boundaries isolate each user&apos;s data.</li>
            </ul>
            <p>
              When you use the Emergency SOS screen, distress messages are generated locally and passed to your device&apos;s native share sheet or SMS app. You maintain complete control over whether the message is sent.
            </p>
          </section>

          {/* 4. Data Retention & Deletion */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">04.</span>
              <span>Data Retention &amp; User Control</span>
            </h2>
            <p>
              You have direct control over your profile and stored information:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>
                <strong>Profile Updates:</strong> You may edit your full name, phone number, and age at any time in Account Settings (<code className="text-primary">/settings</code>).
              </li>
              <li>
                <strong>Contact Deletion:</strong> You can remove any emergency contact immediately using the &quot;Delete&quot; action in Account Settings.
              </li>
              <li>
                <strong>Session Drafts:</strong> Guest journey drafts expire automatically after 30 minutes or immediately upon being consumed during route restoration.
              </li>
              <li>
                <strong>Account Deletion:</strong> Automated self-service account deletion is currently not implemented in the prototype API. You may clear your personal details (phone, age) and delete all saved emergency contacts directly in Account Settings (/settings). To request complete account removal from the database, contact the project maintainers directly (a private privacy channel will be established by project owners prior to public production launch; never post personal identifiers or account credentials to public GitHub issue trackers).
              </li>
            </ul>
          </section>

          {/* 5. Indian Data Protection Framework */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">05.</span>
              <span>Legal Context &amp; DPDP Notice</span>
            </h2>
            <p>
              NavSakhi is developed in alignment with modern data-protection principles outlined in India&apos;s Digital Personal Data Protection (DPDP) Act, including purpose limitation, data minimization, and user consent.
            </p>
            <div className="p-4 rounded-2xl bg-secondary/40 border border-border/70 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-foreground">
                <Info size={14} className="text-primary" />
                <span>Pre-Release Legal Caveat</span>
              </div>
              <p>
                NavSakhi is an independent women's safety navigation software platform. This privacy policy describes the actual data architecture implemented in the current codebase. It does not constitute formal certification or substitute for qualified legal review prior to commercial deployment.
              </p>
            </div>
          </section>

        </div>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/terms" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Read Terms &amp; Conditions <ArrowRight size={14} />
          </Link>
          <Link href="/settings" className="text-xs font-bold text-muted-foreground hover:text-foreground">
            Manage Account &amp; Emergency Contacts &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
