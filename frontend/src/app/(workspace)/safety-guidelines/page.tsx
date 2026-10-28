import type { Metadata } from "next";
import Link from "next/link";
import { 
  ShieldAlert, PhoneCall, CheckCircle2, AlertTriangle, 
  Bus, Train, ShieldCheck, HeartHandshake, Phone, ArrowRight, Info 
} from "lucide-react";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Safety Guidelines & Emergency Information",
  description: "Official emergency response protocols, verified helplines in India, and safe commuting guidance for NavSakhi.",
};

export default function SafetyGuidelinesPage() {
  const verifiedHelplines = [
    {
      number: "112",
      name: "National Emergency Response Support System (ERSS)",
      desc: "All-in-one single emergency number across India for Police, Fire, Ambulance, and Disaster assistance.",
      officialUrl: "https://112.gov.in/",
      badge: "Primary National Service",
      badgeColor: "bg-danger/10 text-danger border-danger/20",
    },
    {
      number: "1091",
      name: "Women Helpline (24/7 Dedicated)",
      desc: "Dedicated toll-free national distress line for women facing harassment, assault, or requiring immediate police intervention.",
      officialUrl: "http://ncw.nic.in/",
      badge: "National Women Helpline",
      badgeColor: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
    },
    {
      number: "181",
      name: "Tamil Nadu Women in Distress Helpline",
      desc: "Statewide 24-hour telephone service providing immediate crisis counseling, shelter referrals, and legal guidance.",
      officialUrl: "https://www.tn.gov.in/",
      badge: "State Helpline (Tamil Nadu)",
      badgeColor: "bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/20",
    },
    {
      number: "100",
      name: "City Police Control Room",
      desc: "Direct connection to Chennai City Police dispatch and nearest mobile patrol vehicles (PCR vans).",
      officialUrl: "https://eservices.tnpolice.gov.in/",
      badge: "City Police",
      badgeColor: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    },
    {
      number: "1860 425 1515",
      name: "Chennai Metro Rail (CMRL) Helpline",
      desc: "CMRL station customer care, platform security assistance, and lost-and-found inquiry.",
      officialUrl: "https://chennaimetrorail.org/",
      badge: "Metro Rail Security",
      badgeColor: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20",
    },
    {
      number: "1800 425 6151",
      name: "MTC Chennai Grievance & Passenger Helpline",
      desc: "Official Metropolitan Transport Corporation (MTC) Chennai toll-free passenger grievance and control assistance.",
      officialUrl: "https://mtcbus.tn.gov.in/",
      badge: "MTC Chennai Bus",
      badgeColor: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    },
  ];

  return (
    <div className="flex-1 w-full min-h-full flex flex-col justify-between">
      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        
        {/* Header Banner */}
        <section className="relative overflow-hidden rounded-3xl border border-border/80 hero-gradient p-6 sm:p-8 shadow-xs space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-danger/10 text-danger border border-danger/20">
            <ShieldAlert size={13} className="text-danger" />
            <span>Emergency Preparedness &bull; Official Helplines</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground font-[family-name:var(--font-jakarta)]">
            Safety Guidelines &amp; Emergency Protocols
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium leading-relaxed">
            Essential protocols, official national emergency numbers, and safe commuting practices for daily urban transit.
          </p>
        </section>

        {/* Vital Clarification: Not a Police Replacement */}
        <div className="p-5 rounded-3xl bg-danger/10 border border-danger/25 space-y-2">
          <div className="flex items-center gap-2 text-danger font-bold text-sm">
            <AlertTriangle size={18} />
            <span>Critical Emergency Notice</span>
          </div>
          <p className="text-xs sm:text-sm text-foreground/90 leading-relaxed">
            NavSakhi is a software tool, <strong>NOT a replacement for official law enforcement or emergency dispatch services.</strong>
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            If you are in immediate physical danger, experiencing harassment, or witness an emergency, <strong>dial 112 immediately</strong>. Do not rely on web apps or internet connections when rapid police or medical intervention is required.
          </p>
        </div>

        {/* Verified Helplines Grid */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
              <PhoneCall size={20} className="text-danger" />
              <span>Official Government &amp; Transit Helplines in India</span>
            </h2>
            <span className="text-xs text-muted-foreground font-medium">Toll-Free &bull; 24/7 Available</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {verifiedHelplines.map((item) => {
              const cleanNumber = item.number.replace(/\s+/g, "");
              return (
                <div key={item.number} className="rounded-2xl border border-border/80 bg-card p-5 shadow-xs flex flex-col justify-between hover:border-danger/40 transition-colors">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${item.badgeColor}`}>
                        {item.badge}
                      </span>
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    </div>
                    <a 
                      href={`tel:${cleanNumber}`}
                      className="text-2xl font-black text-foreground hover:text-danger tracking-tight font-[family-name:var(--font-jakarta)] block transition-colors"
                      title={`Click to call ${item.name}`}
                    >
                      {item.number}
                    </a>
                    <h3 className="font-bold text-foreground text-sm">{item.name}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {item.desc}
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border/60 flex items-center justify-between">
                    <a 
                      href={item.officialUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-[11px] text-primary hover:underline font-semibold flex items-center gap-1"
                    >
                      Official Portal &rarr;
                    </a>
                    <a 
                      href={`tel:${cleanNumber}`}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-danger/10 text-danger text-xs font-bold hover:bg-danger/20 transition-colors"
                    >
                      <Phone size={12} /> Call {cleanNumber}
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Official Helpline Notice */}
        <div className="p-4 rounded-2xl bg-secondary/50 border border-border/70 text-xs text-muted-foreground flex items-start gap-2.5">
          <Info size={16} className="text-primary shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Helpline Notice:</strong> Telephone links (<code>tel:</code>) open your smartphone or computer dialer. NavSakhi is an independent software application and does not operate, manage, or dispatch from these government or transit helplines.
          </p>
        </div>

        {/* How the In-App SOS Button Operates */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
            <ShieldCheck size={20} className="text-primary" />
            <span>How NavSakhi&apos;s Emergency SOS Works (Safe-Test Mode)</span>
          </h2>
          <div className="p-5 rounded-3xl bg-secondary/40 border border-border/80 space-y-3 text-xs sm:text-sm text-muted-foreground leading-relaxed">
            <p>
              NavSakhi includes a dedicated Emergency SOS screen accessible via the header and mobile navigation. Here is how it functions:
            </p>
            <ul className="list-disc list-inside space-y-1.5 pl-2">
              <li>
                <strong>Safe to Explore:</strong> Testing the SOS feature in NavSakhi will never accidentally call the police, summon emergency dispatchers, send automated background SMS, or incur cellular telecom charges.
              </li>
              <li>
                <strong>Countdown &amp; Cancellation:</strong> When initiated, a 5-second animated countdown allows you to cancel the trigger if activated by mistake.
              </li>
              <li>
                <strong>Client-Side Message Pre-Staging:</strong> The app formats a clean distress text containing your current GPS coordinates, time, and Google Maps link.
              </li>
              <li>
                <strong>Native Device Sharing:</strong> Tapping &quot;Share Alert&quot; triggers your smartphone or browser&apos;s native share sheet (WhatsApp, SMS, Email). The message is only transmitted if you confirm it inside your device application.
              </li>
            </ul>
          </div>
        </section>

        {/* Practical Commuter Safety Advice */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-foreground font-[family-name:var(--font-jakarta)] flex items-center gap-2">
            <Bus size={20} className="text-purple-500" />
            <span>Everyday Urban Commuter Safety Practices</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
            <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
              <span className="font-bold text-foreground block">1. Prioritize High-Frequency Corridors</span>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Choose Chennai Metro (Blue &amp; Green lines) or designated MTC express bus stops where active passenger volume and CCTV coverage are highest.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
              <span className="font-bold text-foreground block">2. Women&apos;s Reserved Coaches</span>
              <p className="text-muted-foreground text-xs leading-relaxed">
                CMRL trains feature dedicated women-only coaches (marked with pink platform decals). EMU Suburban trains maintain designated women&apos;s compartments with security personnel during evening hours.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
              <span className="font-bold text-foreground block">3. Pre-Stage Emergency Contacts</span>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Keep at least two trusted family members or friends configured in your NavSakhi Account Settings. Verify that their phone numbers include the correct country code (+91).
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-card border border-border/80 space-y-1.5">
              <span className="font-bold text-foreground block">4. Share Route Intentions Early</span>
              <p className="text-muted-foreground text-xs leading-relaxed">
                Before boarding late-night transit, send your expected arrival time and transit corridor name to your trusted circle.
              </p>
            </div>
          </div>
        </section>

        {/* Footer Navigation */}
        <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between gap-4">
          <Link href="/emergency" className="text-xs font-bold text-danger hover:underline flex items-center gap-1">
            Open Emergency SOS Hub <ArrowRight size={14} />
          </Link>
          <Link href="/resources" className="text-xs font-bold text-primary hover:underline">
            View Legal Rights &amp; Zero FIR Protections &rarr;
          </Link>
        </div>

      </div>

      <Footer />
    </div>
  );
}
