import type { Metadata } from "next";
import Link from "next/link";
import { Sparkles, AlertTriangle, ShieldAlert, Cpu, CloudSun, Radio, ArrowRight, Info, CheckCircle2 } from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "AI & ML Limitations Notice",
  description: "Architectural and statistical limitations disclosure for NavSakhi's machine learning, AI assistant, and telemetry models.",
};

export default function LimitationsPage() {
  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <Sparkles size={13} className="text-rose-500" />
            <span>Transparency Notice &bull; Statistical Boundaries</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Prototype, AI &amp; ML Limitations
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Understanding the algorithmic boundaries, statistical assumptions, and technical limits of NavSakhi.
          </p>
        </section>

        {/* Primary Prototype Disclosure Callout */}
        <div className="p-5 rounded-3xl bg-danger/10 border border-danger/25 space-y-3">
          <div className="flex items-center gap-2 text-danger font-bold text-sm">
            <AlertTriangle size={18} />
            <span>Foundational Prototype Disclaimer</span>
          </div>
          <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed">
            &quot;NavSakhi is a prototype decision-support tool. Its route recommendations, environmental and safety indicators, ML scores, AI-generated guidance, community information, and weather data may be incomplete, delayed, inaccurate, or unavailable.
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            The ML model has been trained and evaluated using the available datasets and the project&apos;s documented training process. Its results reflect the data, features, and conditions represented in that process and may not represent current conditions or every user&apos;s experience. The application does not guarantee that a route is safe, that a reported condition exists, or that an emergency response will occur. Recommendations are informational aids, not assurances of personal safety. Users should use their own judgment, follow official instructions, and contact official emergency services when necessary.&quot;
          </p>
        </div>

        {/* Detailed Limitations Breakdown */}
        <div className="space-y-6 text-xs sm:text-sm text-muted-foreground leading-relaxed">
          
          {/* Section 1: ML Safety Scoring */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">01.</span>
              <span>Machine Learning Model &amp; Spatial Risk Proxies</span>
            </h2>
            <p>
              NavSakhi employs a <strong>LightGBM</strong> gradient-boosted decision tree architecture combined with <strong>TreeSHAP</strong> feature attribution to compute composite route safety indices. It is essential to recognize what the model does and does not measure:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Spatial Proxies, Not Direct Threat Sensors:</strong> The model evaluates infrastructure proxies — street lighting availability, road functional classification (arterial vs residential), commercial Point of Interest (POI) density, proximity to operational CMRL metro stations, and time of day (including nighttime activity dampening).
              </li>
              <li>
                <strong>Historical Datasets:</strong> Training data represents historical urban features from Chennai. Temporary conditions such as sudden power blackouts, road construction diversions, private gatherings, or dynamic crowd movements are not reflected in real time.
              </li>
              <li>
                <strong>No Independent Field Certification:</strong> Model predictions have not been independently validated or certified by municipal transit authorities or law enforcement agencies. Scores should be treated as comparative heuristics rather than absolute guarantees.
              </li>
            </ul>
          </section>

          {/* Section 2: In-App Tracking vs Human Monitoring */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">02.</span>
              <span>In-App Tracking vs. Human Monitoring Operations</span>
            </h2>
            <div className="p-4 rounded-2xl bg-secondary/40 border border-border/80 space-y-2">
              <div className="flex items-center gap-2 text-foreground font-bold text-xs uppercase tracking-wider">
                <Radio size={15} className="text-primary" />
                <span>Zero Human Surveillance / Zero Dispatch Operations</span>
              </div>
              <p>
                There is a critical distinction between NavSakhi&apos;s client-side telemetry companion and a human security service:
              </p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>NavSakhi <strong>does NOT</strong> employ live human operators, dispatch agents, or security monitors.</li>
                <li>No one is actively watching your trip, tracking deviations, or contacting police on your behalf.</li>
                <li>Live Monitor is an automated tool that coordinates timeline waypoints and pre-stages emergency coordinates for you to share directly with your designated contacts.</li>
              </ul>
            </div>
          </section>

          {/* Section 3: AI Assistant & Generative Models */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">03.</span>
              <span>Generative AI Assistant (Google Gemini &amp; Fallbacks)</span>
            </h2>
            <p>
              The AI Safety Assistant is powered by large language model APIs (Google Gemini) with deterministic local fallback logic. Users must be aware that:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Generative Output:</strong> AI responses are probabilistically generated suggestions. They may occasionally produce hallucinated bus routes, obsolete station operating hours, or inaccurate safety advice.
              </li>
              <li>
                <strong>Distinction from Verified Live Data:</strong> AI conversational advice is fundamentally distinct from deterministic transit timetables or algorithmic safety scores. Always cross-reference transit schedules with official Chennai Metro (CMRL) or MTC signage.
              </li>
              <li>
                <strong>Offline / Quota Fallback:</strong> If the external Gemini API is unreachable, rate-limited, or unconfigured, the assistant defaults to structured, deterministic safety guidance without real-time generative capabilities.
              </li>
            </ul>
          </section>

          {/* Section 4: Weather Provider Rate Limits & Caching */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">04.</span>
              <span>Atmospheric &amp; Weather Data (Open-Meteo)</span>
            </h2>
            <p>
              NavSakhi interfaces with Open-Meteo to display temperature, precipitation, and UV index:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Deterministic Caching:</strong> Successful observations are cached for 900 seconds (15 minutes). If the upstream API returns an HTTP 429 rate limit or network error, a negative cache holds the error for 30 seconds to prevent cascading upstream retries.
              </li>
              <li>
                <strong>Honest Offline Representation:</strong> When weather data is unavailable or rate-limited, the application clearly displays an offline state. NavSakhi will never fabricate mock weather values or represent stale forecasts as live observations.
              </li>
            </ul>
          </section>

          {/* Section 5: Community Reports Verification */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">05.</span>
              <span>Community Observations &amp; Crowd-Sourced Data</span>
            </h2>
            <p>
              Community reports regarding streetlight outages, isolated stops, or transit conditions reflect user-submitted input. While NavSakhi applies automated spam heuristics and administrative auditing, reports may be outdated, subjective, or incomplete. Always assess real-world surroundings independently.
            </p>
          </section>

        </div>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/safety-guidelines" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Read Official Safety Guidelines <ArrowRight size={14} />
          </Link>
          <Link href="/about" className="text-xs font-bold text-muted-foreground hover:text-foreground">
            Learn How NavSakhi Works &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
