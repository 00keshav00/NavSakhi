import type { Metadata } from "next";
import Link from "next/link";
import { Scale, ShieldAlert, AlertTriangle, CheckCircle2, Lock, ArrowRight, Info } from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Terms & Conditions",
  description: "Terms and conditions governing the use of the NavSakhi prototype decision-support software application.",
};

export default function TermsPage() {
  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <Scale size={13} className="text-primary" />
            <span>Legal Notice &bull; Prototype Agreement</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Terms &amp; Conditions
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Effective Date: October 2026 &bull; Project Status: Working Research Prototype
          </p>
        </section>

        {/* Prominent Prototype Disclaimer Callout */}
        <div className="p-5 rounded-3xl bg-amber-500/10 border border-amber-500/25 space-y-2">
          <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-bold text-sm">
            <AlertTriangle size={18} />
            <span>Important Prototype Notice</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            NavSakhi is an independent software research project and working prototype. It is designed solely as an informational decision-support aid for evaluating public transit alternatives in Chennai. 
            <strong> NavSakhi does not provide guaranteed personal safety, does not dispatch police or emergency responders, and cannot prevent crime or hazardous incidents. In any active emergency in India, always dial 112 immediately.</strong>
          </p>
        </div>

        {/* Main Terms Sections */}
        <div className="space-y-6 text-xs sm:text-sm text-muted-foreground leading-relaxed">
          
          {/* Section 1 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">01.</span>
              <span>Acceptance of Terms &amp; Scope of Service</span>
            </h2>
            <p>
              By accessing, browsing, or creating an account on NavSakhi (&quot;the Platform&quot;), you acknowledge that you have read, understood, and agreed to be bound by these Terms &amp; Conditions. If you do not agree to these terms, you should discontinue using the Platform.
            </p>
            <p>
              NavSakhi is provided as an open technology prototype. It is not an enterprise safety service, a commercial security platform, or an accredited emergency dispatch provider.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">02.</span>
              <span>User Responsibilities &amp; Acceptable Use</span>
            </h2>
            <p>
              You agree to use NavSakhi solely for lawful, non-commercial transit planning and personal safety awareness. You agree that you will not:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Submit false, misleading, or abusive emergency reports in the Community module.</li>
              <li>Attempt to reverse-engineer, decompile, scrape, or overwhelm application endpoints or external upstream APIs.</li>
              <li>Impersonate any other person or misrepresent your affiliation with emergency services or law enforcement.</li>
              <li>Rely on NavSakhi as the sole determinant of personal safety in dangerous or life-threatening environments.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">03.</span>
              <span>Account Credentials &amp; Profile Data</span>
            </h2>
            <p>
              Registration is optional; users may explore transit corridors and routes as Guest Explorers. If you choose to register, you are responsible for maintaining the confidentiality of your login credentials. You are responsible for all actions taken under your account.
            </p>
            <p>
              Passwords are cryptographically hashed using standard bcrypt algorithms before persistence. Plaintext passwords are never logged, stored, or visible to system administrators.
            </p>
          </section>

          {/* Section 4 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">04.</span>
              <span>Location Access &amp; Live Journey Tracking Consent</span>
            </h2>
            <p>
              Location access is strictly consent-driven. NavSakhi will never poll, track, or record your physical GPS location in the background without explicit user authorization:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Signing in or restoring a saved journey draft does not initiate live GPS tracking.</li>
              <li>Live GPS tracking begins only when you explicitly click &quot;Start Monitored Journey&quot; and approve the browser location prompt.</li>
              <li>You may stop active tracking at any time by clicking &quot;Stop Journey&quot; or closing the browser session.</li>
            </ul>
          </section>

          {/* Section 5 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">05.</span>
              <span>Emergency SOS &amp; Helpline Limitations</span>
            </h2>
            <p>
              The Emergency SOS feature operates in a local demonstration and simulated staging mode:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>NavSakhi does not connect to police telecommunications, cellular SMS gateways, or 112 emergency services.</li>
              <li>Saving an emergency contact stores the contact for manual reference and pre-staged dialing; it does not automatically transmit background alerts or SMS messages to that contact.</li>
              <li>Emergency contact sharing relies entirely on client-side native browser sharing (Web Share API) or SMS deep-linking, which requires manual user confirmation on your device.</li>
              <li>In any genuine crisis, danger, or threat of violence, you must use your device phone dialer to reach <strong>112 (National Emergency)</strong> or <strong>1091 (Women Helpline)</strong>.</li>
            </ul>
          </section>

          {/* Section 6 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">06.</span>
              <span>Machine Learning &amp; AI Suggestions Disclaimer</span>
            </h2>
            <p>
              Route safety scores, lighting proxies, night activity ratings, and AI Assistant recommendations are probabilistic estimates generated by LightGBM machine learning models and generative AI systems (Google Gemini):
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Scores reflect historical proxy datasets (station density, road classifications, commercial POIs) and do not represent guaranteed real-time safety.</li>
              <li>AI Assistant responses may contain inaccuracies, omissions, or errors. Always verify transit schedules and route feasibility through official transit operators (CMRL, MTC).</li>
              <li>NavSakhi does not guarantee the availability, accuracy, or timeliness of external data providers, including Open-Meteo weather or OpenStreetMap routing.</li>
            </ul>
          </section>

          {/* Section 7 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">07.</span>
              <span>Limitation of Liability &amp; Disclaimers</span>
            </h2>
            <p>
              To the fullest extent permitted by applicable law, NavSakhi, its developers, and contributors disclaim all warranties, whether express or implied, including warranties of merchantability, fitness for a particular purpose, non-infringement, or personal security.
            </p>
            <p>
              Under no circumstances shall the project developers be liable for any direct, indirect, incidental, consequential, special, or exemplary damages, or personal injury resulting from your use of or reliance on the Platform.
            </p>
            <p className="text-[11px] text-muted-foreground/90 bg-secondary/40 p-3 rounded-xl border border-border/60">
              <strong>Statutory Protections:</strong> Nothing in these terms is intended to exclude or limit any statutory rights or consumer protections that cannot be lawfully excluded or limited under the laws of India. Users acknowledge that NavSakhi is an experimental decision-support prototype, and personal safety decisions remain the responsibility of the individual traveler.
            </p>
          </section>

          {/* Section 8 */}
          <section className="space-y-2">
            <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <span className="text-primary font-mono text-sm">08.</span>
              <span>Inquiries, Bug Reports &amp; Legal Review</span>
            </h2>
            <p>
              NavSakhi is an open software project maintained by independent developers. To report software defects, security vulnerabilities, or privacy concerns, please open an issue in the official project repository.
            </p>
            <p className="text-[11px] text-muted-foreground/80 italic">
              Note: These terms represent a product and research prototype policy draft. Prior to any formal public or commercial release, these terms must be reviewed and adapted by qualified legal counsel.
            </p>
          </section>

        </div>

        {/* Navigation Actions */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/privacy" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Read Privacy Policy <ArrowRight size={14} />
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
