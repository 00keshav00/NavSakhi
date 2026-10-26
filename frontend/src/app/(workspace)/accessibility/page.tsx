import type { Metadata } from "next";
import Link from "next/link";
import { 
  Eye, CheckCircle2, ShieldCheck, Sparkles, 
  ArrowRight, Info, Keyboard, Volume2, Contrast 
} from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Accessibility Statement",
  description: "Accessibility features, WCAG compliance efforts, and assistive technology support across NavSakhi.",
};

export default function AccessibilityPage() {
  const features = [
    {
      title: "Semantic HTML5 & Landmarks",
      icon: <CheckCircle2 className="text-emerald-500" size={18} />,
      desc: "Pages utilize proper landmark tags (<header>, <nav>, <main>, <footer>), valid heading hierarchies (h1 through h4), and descriptive button roles to assist screen reader navigation.",
    },
    {
      title: "High-Contrast HSL Color Palettes",
      icon: <Contrast className="text-primary" size={18} />,
      desc: "Both light and dark color schemes are engineered to satisfy WCAG 2.1 AA contrast ratios (4.5:1 for standard text, 3:1 for large text and interactive icons) against backgrounds.",
    },
    {
      title: "Keyboard Operability & Focus Rings",
      icon: <Keyboard className="text-purple-500" size={18} />,
      desc: "All interactive controls, navigation tabs, modal dialogs, and form inputs are fully operable via keyboard navigation with distinct visual focus rings.",
    },
    {
      title: "Accessible Labels & Screen Readers",
      icon: <Volume2 className="text-amber-500" size={18} />,
      desc: "Icon-only buttons (such as theme toggles, SOS help info, and password revealers) include explicit aria-label and aria-expanded attributes for assistive technology.",
    },
  ];

  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
            <Eye size={13} className="text-primary" />
            <span>Inclusive Design &bull; Assistive Technology</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Accessibility Statement
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Our commitment to ensuring NavSakhi is usable, perceptible, and accessible for everyone, including commuters with disabilities.
          </p>
        </section>

        {/* Commitment Statement */}
        <section className="p-6 rounded-3xl bg-card border border-border/80 space-y-3 text-xs sm:text-sm text-muted-foreground leading-relaxed">
          <h2 className="text-lg font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Our Accessibility Philosophy
          </h2>
          <p>
            Safety and mobility tools must be accessible to all commuters, regardless of visual, motor, auditory, or cognitive abilities. NavSakhi strives to adhere to the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA recommendations across desktop, tablet, and mobile platforms.
          </p>
          <p>
            As a technology prototype, we continuously audit interactive elements, form controls, and map visualizations to identify and remediate potential barriers.
          </p>
          <div className="p-3.5 rounded-2xl bg-secondary/50 border border-border/70 text-xs text-muted-foreground flex items-start gap-2 mt-2">
            <Info size={15} className="text-primary shrink-0 mt-0.5" />
            <p>
              <strong>Statement of Scope:</strong> NavSakhi is designed using accessibility best practices (color contrast, semantic landmarks, keyboard focus rings), but has not undergone formal independent third-party WCAG certification. We welcome community and user feedback to identify remaining barriers.
            </p>
          </div>
        </section>

        {/* Implemented Accessibility Features */}
        <section className="space-y-4">
          <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Implemented Features &amp; Standards
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {features.map((feat, idx) => (
              <div key={idx} className="p-5 rounded-2xl bg-card border border-border/80 space-y-2 hover:border-primary/40 transition-colors">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-secondary">
                    {feat.icon}
                  </div>
                  <h3 className="font-bold text-foreground text-sm font-[family-name:var(--font-jakarta)]">
                    {feat.title}
                  </h3>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed pl-8">
                  {feat.desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Known Limitations & Workarounds */}
        <section className="space-y-3">
          <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)]">
            Known Prototype Limitations &amp; Future Goals
          </h2>
          <div className="p-5 rounded-3xl bg-secondary/40 border border-border/80 space-y-3 text-xs text-muted-foreground leading-relaxed">
            <p>
              While core navigation and forms meet high accessibility standards, certain complex components remain in active research and refinement:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Interactive Map Canvas:</strong> WebGL and Leaflet/MapLibre map canvases are inherently visual. To provide parity, all calculated routes and transit steps are fully rendered in structured text cards and timeline panels alongside the map.
              </li>
              <li>
                <strong>Motion Sensitivity:</strong> NavSakhi respects system-level <code className="text-primary font-mono">prefers-reduced-motion</code> settings to minimize animations for users prone to vestibular motion triggers.
              </li>
            </ul>
          </div>
        </section>

        {/* Feedback Channel */}
        <section className="p-5 rounded-3xl bg-card border border-border/80 space-y-2 text-xs text-muted-foreground">
          <span className="font-bold text-foreground block text-sm flex items-center gap-1.5">
            <Info size={15} className="text-primary" /> Accessibility Feedback
          </span>
          <p className="leading-relaxed">
            Encountering an accessibility obstacle or have a suggestion to improve screen reader compatibility? Please file an issue on the NavSakhi GitHub repository or mention it through our Community module.
          </p>
        </section>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/help" className="text-xs font-bold text-primary hover:underline flex items-center gap-1">
            Visit Help &amp; Support <ArrowRight size={14} />
          </Link>
          <Link href="/terms" className="text-xs font-bold text-muted-foreground hover:text-foreground">
            View Terms &amp; Conditions &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
