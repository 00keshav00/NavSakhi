"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  AlertOctagon, PhoneCall, MapPin, ShieldAlert, XCircle, CheckCircle2, 
  Share2, Hospital, ShieldCheck, Loader2, Bot, Info, Navigation, AlertTriangle,
  Lock, Copy, ExternalLink, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { emergencyService } from "@/api/services/emergencyService";
import { useEmergencySession } from "@/hooks/useEmergency";
import { EmergencyTimelineEvent } from "@/types/emergency";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export default function EmergencyPage() {
  const [status, setStatus] = useState<"idle" | "counting" | "active">("idle");
  const [countdown, setCountdown] = useState(5);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSharing, setIsSharing] = useState(false);
  const [isSosInfoOpen, setIsSosInfoOpen] = useState(false);

  // Explicit user-invoked location detection state (Never fetched automatically)
  const [userCoords, setUserCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationStatus, setLocationStatus] = useState<"unrequested" | "located" | "denied">("unrequested");
  const [sharingStatus, setSharingStatus] = useState<"idle" | "previewed" | "shared">("idle");

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);

  // Hook continuously polls the backend for session telemetry when sessionId is present
  const { data } = useEmergencySession(sessionId);

  // Explicit GPS location retrieval for preview only upon deliberate user click
  const handleAcquireLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation not supported by this browser.");
      setLocationStatus("denied");
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserCoords({
          lat: parseFloat(pos.coords.latitude.toFixed(5)),
          lng: parseFloat(pos.coords.longitude.toFixed(5))
        });
        setLocationStatus("located");
        setSharingStatus("previewed");
        setIsLocating(false);
        toast.success("Location Acquired for Preview", {
          description: `Coordinates: ${pos.coords.latitude.toFixed(4)}°N, ${pos.coords.longitude.toFixed(4)}°E`
        });
      },
      (err) => {
        setIsLocating(false);
        setLocationStatus("denied");
        toast.error("Location permission denied", {
          description: "Coordinates cannot be retrieved without your explicit permission."
        });
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  // Previewed Emergency Message Text
  const previewLat = userCoords?.lat ?? (data?.live_location?.coordinates ? data.live_location.coordinates[1] : 13.0827);
  const previewLng = userCoords?.lng ?? (data?.live_location?.coordinates ? data.live_location.coordinates[0] : 80.2707);
  const mapLink = `https://www.google.com/maps?q=${previewLat},${previewLng}`;
  const emergencyMessage = `[NavSakhi Emergency SOS Alert] Urgent assistance requested. My location is: ${previewLat}° N, ${previewLng}° E. Live map link: ${mapLink}`;

  // User-Initiated Native Device Sharing
  const handleShareLocation = async () => {
    if (isSharing) return;

    if (navigator.share) {
      try {
        setIsSharing(true);
        await navigator.share({
          title: "NavSakhi Emergency SOS Alert",
          text: emergencyMessage,
          url: mapLink,
        });
        setSharingStatus("shared");
        toast.success("Device Share Sheet Opened", {
          description: "Message dispatched via your device's native application."
        });
      } catch (err: unknown) {
        // User aborted or dismissed native share dialog
        if ((err as Error)?.name !== "AbortError") {
          toast.error("Share failed", { description: (err as Error)?.message });
        }
      } finally {
        setIsSharing(false);
      }
    } else {
      try {
        await navigator.clipboard.writeText(emergencyMessage);
        setSharingStatus("shared");
        toast.success("Tracking Link Copied to Clipboard", {
          description: "Paste and send to your emergency contact via WhatsApp, SMS, or Messenger."
        });
      } catch (e) {
        toast.error("Could not copy link to clipboard.");
      }
    }
  };

  const handleDialEmergency = () => {
    const isMobile = typeof navigator !== "undefined" && /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (isMobile) {
      window.location.href = "tel:112";
    } else {
      toast.info("National Emergency Helpline: 112", {
        description: "Please dial 112 directly on your mobile device for genuine emergency services."
      });
    }
  };

  const initiateEmergencyProtocol = async () => {
    try {
      const locationString = userCoords 
        ? `${userCoords.lat}° N, ${userCoords.lng}° E`
        : "13.0827° N, 80.2707° E";
      
      const response = await emergencyService.triggerSOS({
        current_location: locationString,
      });
      
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
    } catch (error) {
      console.error("Failed to initiate emergency protocol:", error);
    }
  };

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (status === "counting" && countdown > 0) {
      timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    } else if (status === "counting" && countdown === 0) {
      setStatus("active");
      initiateEmergencyProtocol();
    }
    return () => clearTimeout(timer);
  }, [status, countdown]);

  const triggerSOS = () => {
    if (!isAuthenticated) {
      toast.info("Account Required for SOS Simulation", {
        description: "Please sign in to bind emergency contacts and test live simulated telemetry."
      });
      return;
    }
    setCountdown(5);
    setStatus("counting");
  };

  const cancelSOS = () => {
    setStatus("idle");
    setCountdown(5);
    setSessionId(null);
    setSharingStatus("idle");
  };

  return (
    <div className="relative flex h-full min-h-full w-full flex-col items-center overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-8 sm:py-12">
      {/* Background Danger Overlay */}
      <div className={`fixed inset-0 z-0 transition-colors duration-1000 ${status === 'active' ? 'bg-danger/10' : status === 'counting' ? 'bg-warning/10' : 'bg-transparent'}`} />
      
      <div className="relative z-10 flex w-full max-w-4xl flex-col items-center space-y-8">
        
        {/* 1. Prototype Scope & Honest Disclosure Banner */}
        <div className="w-full p-4 rounded-2xl bg-secondary/80 border border-border/80 backdrop-blur-md shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <span className="p-1.5 rounded-xl bg-danger/10 text-danger shrink-0">
              <ShieldAlert size={18} />
            </span>
            <div>
              <p className="font-bold text-foreground">NavSakhi Working Prototype</p>
              <p className="text-muted-foreground text-[11px]">
                No real 112 police dispatch or automated cellular SMS broadcasts are conducted. All emergency coordination workflows are local interactive simulations.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSosInfoOpen(true)}
            className="rounded-full text-[11px] font-bold h-7 px-3 border-border shrink-0 gap-1.5"
          >
            <Info size={13} /> Scope & Architecture
          </Button>
        </div>

        {/* 2. Unauthenticated Guest Warning Card */}
        {!isAuthenticated && (
          <div className="w-full p-5 rounded-3xl bg-primary/5 border border-primary/20 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-2xl bg-primary/10 text-primary shrink-0 mt-0.5">
                <Lock size={18} />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-foreground text-sm">Guest Exploration Mode</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Triggering the emergency simulation requires an authenticated account to link contact notifications and session persistence.
                  Sign in with the local test account to unlock the full simulation.
                </p>
              </div>
            </div>
            <Link href="/login?redirect=/emergency" className="shrink-0">
              <Button size="sm" className="rounded-full font-bold text-xs px-4 h-9 shadow-xs">
                Sign In to Test SOS
              </Button>
            </Link>
          </div>
        )}

        {/* 3. Header Section */}
        <div className="flex flex-col items-center text-center space-y-2">
          <AnimatePresence mode="wait">
            {status === "active" ? (
              <motion.div key="active" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-3 flex items-center gap-1.5 animate-pulse rounded-full border border-danger/30 bg-danger/20 px-4 py-1 text-xs font-bold uppercase tracking-wider text-danger">
                  <AlertTriangle size={13} /> Simulation Active (No Real Dispatch)
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-foreground">
                  Simulated Emergency Response
                </h1>
                <p className="text-xs sm:text-sm text-muted-foreground max-w-lg mt-1 font-medium">
                  Review the simulated deployment sequence, inspect nearest safe havens, or initiate native device sharing.
                </p>
              </motion.div>
            ) : status === "counting" ? (
              <motion.div key="counting" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-3 rounded-full border border-warning/30 bg-warning/20 px-4 py-1 text-xs font-bold uppercase tracking-wider text-warning">
                  Initiating Demonstration Protocol
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
                  Countdown to Staged Alert
                </h1>
              </motion.div>
            ) : (
              <motion.div key="idle" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-3 flex items-center gap-1.5 rounded-full border border-success/20 bg-success/15 px-4 py-1 text-xs font-bold uppercase tracking-wider text-success">
                  <ShieldCheck size={14} /> System Operational: Standby
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-foreground">
                  Emergency Command Center
                </h1>
                <p className="text-xs sm:text-sm text-muted-foreground max-w-md mt-1 font-medium">
                  Press and hold the SOS action to simulate the emergency coordination sequence.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 4. SOS Button Section */}
        <div className="relative my-4 flex items-center justify-center">
          {status === "active" && (
            <>
              <div className="absolute h-[280px] w-[280px] sm:h-[340px] sm:w-[340px] animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite] rounded-full bg-danger/20 opacity-75" />
              <div className="absolute h-[360px] w-[360px] sm:h-[440px] sm:w-[440px] animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite] rounded-full bg-danger/10 opacity-50" style={{ animationDelay: "0.5s" }} />
            </>
          )}

          <button
            onClick={status === "idle" ? triggerSOS : cancelSOS}
            className={`relative z-10 flex h-48 w-48 sm:h-56 sm:w-56 flex-col items-center justify-center rounded-full shadow-2xl transition-all duration-500 ${
              status === "active" ? "scale-105 bg-danger text-white ring-8 ring-danger/30 shadow-[0_0_60px_rgba(225,29,72,0.6)] cursor-pointer" : 
              status === "counting" ? "scale-105 bg-warning text-white ring-8 ring-warning/30 shadow-[0_0_60px_rgba(245,158,11,0.6)]" :
              "border-4 border-danger/80 bg-card text-danger shadow-[0_0_30px_rgba(225,29,72,0.15)] hover:scale-105 hover:bg-danger hover:text-white active:scale-95"
            }`}
            aria-label={status === "active" ? "Reset Emergency Simulation" : "Trigger Emergency SOS"}
          >
            {status === "counting" ? (
              <span className="font-[family-name:var(--font-jakarta)] text-6xl sm:text-7xl font-black">{countdown}</span>
            ) : (
              <>
                <AlertOctagon size={64} strokeWidth={1.5} className={status === "active" ? "animate-pulse" : ""} />
                <span className="mt-3 font-[family-name:var(--font-jakarta)] text-2xl sm:text-3xl font-black uppercase tracking-widest">
                  {status === "active" ? "RESET SOS" : "SOS"}
                </span>
                <span className="text-[10px] tracking-wider uppercase opacity-80 mt-0.5">
                  {status === "active" ? "Click to Conclude" : "Tap to Trigger"}
                </span>
              </>
            )}
          </button>
        </div>

        {/* 5. Detailed Active Simulation Interface */}
        <div className="w-full">
          <AnimatePresence mode="popLayout">
            {status === "active" ? (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className="grid grid-cols-1 gap-6 md:grid-cols-2">
                
                {/* Left Column: Simulated Deployment Sequence & Nearest Safe Zones */}
                <div className="flex flex-col gap-6">
                  
                  {/* Dynamic Deployment Sequence */}
                  <div className="glass-card flex flex-col rounded-3xl border border-border/70 p-6 sm:p-7 shadow-xs">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">
                        Demonstration Workflow Sequence
                      </h3>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-danger/10 text-danger border border-danger/20 uppercase tracking-wider">
                        SIMULATED
                      </span>
                    </div>

                    <div className="relative flex flex-col space-y-6 pl-2">
                      <div className="absolute bottom-6 left-[11px] top-2 z-0 w-0.5 bg-border/50" />
                      {!data ? (
                        <div className="animate-pulse space-y-4">
                           <div className="h-6 w-full bg-secondary/50 rounded-md" />
                           <div className="h-6 w-3/4 bg-secondary/50 rounded-md" />
                        </div>
                      ) : (
                        data.timeline.map((event: EmergencyTimelineEvent) => (
                          <TimelineStep 
                            key={event.id}
                            text={event.description} 
                            completed={event.status === 'completed'} 
                            active={event.status === 'active'}
                            timestamp={event.timestamp}
                          />
                        ))
                      )}
                    </div>
                  </div>

                  {/* Dynamic Safe Havens (Police & Hospitals) */}
                  <div className="glass-card flex flex-col rounded-3xl border border-border/70 p-6 shadow-xs space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-[family-name:var(--font-jakarta)] text-md font-bold text-foreground">
                        Nearest Safe Havens (Chennai Metro)
                      </h3>
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        ROUTED VIA OSRM
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                      {data?.safe_zones && data.safe_zones.length > 0 ? (
                        data.safe_zones.map(zone => (
                          <ServiceCard 
                            key={zone.id}
                            icon={zone.type === 'Police' ? ShieldAlert : Hospital} 
                            title={zone.name} 
                            desc={`${zone.distance} (${zone.eta})`} 
                            color={zone.type === 'Police' ? 'text-primary' : 'text-success'} 
                          />
                        ))
                      ) : (
                        <>
                          <ServiceCard 
                            icon={ShieldAlert}
                            title="Periamet Police Station"
                            desc="1.2 km (4 mins)"
                            color="text-primary"
                          />
                          <ServiceCard 
                            icon={Hospital}
                            title="Rajiv Gandhi Govt General Hospital"
                            desc="1.8 km (7 mins)"
                            color="text-success"
                          />
                        </>
                      )}
                    </div>
                  </div>

                </div>

                {/* Right Column: Message Preview & User-Initiated Sharing */}
                <div className="flex flex-col gap-6">
                  
                  {/* Proposed Emergency Message Preview Card */}
                  <div className="glass-card flex flex-col rounded-3xl border border-border/70 p-6 shadow-xs space-y-4">
                    <div className="flex items-center justify-between border-b border-border/50 pb-3">
                      <div className="flex items-center gap-2">
                        <MapPin size={16} className="text-primary" />
                        <span className="font-bold text-sm text-foreground">Location & Message Preview</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                        sharingStatus === 'shared' 
                          ? 'bg-success/10 text-success border-success/30'
                          : sharingStatus === 'previewed'
                          ? 'bg-primary/10 text-primary border-primary/30'
                          : 'bg-muted text-muted-foreground border-border'
                      }`}>
                        {sharingStatus === 'shared' ? 'READY TO SHARE / OPENED' : sharingStatus === 'previewed' ? 'PREVIEWED - NOT SENT' : 'UNREQUESTED'}
                      </span>
                    </div>

                    <div className="space-y-3">
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        In accordance with privacy requirements, your device coordinates are only retrieved when you explicitly trigger location preview.
                      </p>

                      <div className="p-3.5 rounded-2xl bg-secondary/50 border border-border/70 space-y-2">
                        <div className="flex items-center justify-between text-[11px] font-semibold text-muted-foreground">
                          <span>Preview Coordinates:</span>
                          <span className="font-mono text-foreground font-bold">{previewLat}° N, {previewLng}° E</span>
                        </div>
                        <div className="text-[11px] font-mono p-2.5 rounded-xl bg-card border border-border/60 text-foreground break-all leading-normal select-all">
                          {emergencyMessage}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleAcquireLocation}
                          disabled={isLocating}
                          className="rounded-full text-xs font-bold h-8 border-border gap-1.5"
                        >
                          {isLocating ? <Loader2 size={13} className="animate-spin" /> : <Navigation size={13} />}
                          <span>{locationStatus === 'located' ? "Refresh GPS Coordinates" : "Detect My Location for Preview"}</span>
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Actions: Native Sharing & Helpline */}
                  <div className="glass-card flex flex-col rounded-3xl border border-border/70 p-6 shadow-xs space-y-3.5">
                    <h4 className="font-bold text-sm text-foreground">Emergency Sharing & Direct Helplines</h4>
                    <p className="text-xs text-muted-foreground">
                      Share your staged emergency coordinates with a designated contact using your device's native share sheet, or dial national emergency helplines directly.
                    </p>

                    <Button 
                      size="lg" 
                      onClick={handleShareLocation} 
                      className="h-13 w-full rounded-2xl bg-primary text-primary-foreground font-bold text-sm shadow-md shadow-primary/20 hover:bg-primary/90 gap-2.5"
                    >
                      <Share2 size={18} />
                      <span>Share Location via Device (SMS / WhatsApp)</span>
                    </Button>

                    <Button 
                      size="lg" 
                      onClick={handleDialEmergency} 
                      variant="outline" 
                      className="h-13 w-full rounded-2xl border-danger/50 text-danger hover:bg-danger/10 font-bold text-sm gap-2.5"
                    >
                      <PhoneCall size={18} />
                      <span>Dial National Emergency Helpline (112)</span>
                    </Button>

                    <Button 
                      size="sm" 
                      variant="ghost" 
                      onClick={cancelSOS} 
                      className="h-10 w-full rounded-full font-semibold text-xs text-muted-foreground hover:bg-secondary hover:text-foreground gap-1.5 mt-2"
                    >
                      <XCircle size={15} />
                      <span>Conclude Demonstration & Reset State</span>
                    </Button>
                  </div>

                </div>

              </motion.div>
            ) : status === "counting" ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex w-full justify-center">
                <Button size="lg" onClick={cancelSOS} className="h-12 w-full max-w-sm rounded-full bg-secondary text-sm font-bold text-foreground hover:bg-secondary/80">
                  Cancel Protocol
                </Button>
              </motion.div>
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="glass-card flex flex-col items-center justify-center rounded-3xl border border-dashed border-border/80 px-6 py-12 text-center max-w-xl mx-auto shadow-xs">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-secondary text-muted-foreground">
                  <ShieldCheck size={28} className="text-success" />
                </div>
                <h3 className="font-[family-name:var(--font-jakarta)] text-lg font-bold text-foreground">
                  Safety Telemetry Ready
                </h3>
                <p className="mt-2 text-xs font-medium leading-relaxed text-muted-foreground">
                  Your device telemetry remains strictly private. NavSakhi does not poll your location in the background or notify external contacts unless you explicitly trigger the emergency action.
                </p>
                <div className="mt-5 flex items-center gap-2 text-[11px] text-muted-foreground bg-secondary/60 px-3.5 py-1.5 rounded-full border border-border/60">
                  <Sparkles size={13} className="text-primary" />
                  <span>Verified local prototype profile</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>

      {/* Scope & Architecture Dialog */}
      <Dialog open={isSosInfoOpen} onOpenChange={setIsSosInfoOpen}>
        <DialogContent className="max-w-lg rounded-3xl p-6 border-border shadow-2xl bg-card text-foreground">
          <DialogHeader className="space-y-2">
            <div className="flex items-center gap-2 text-danger">
              <ShieldAlert size={20} />
              <DialogTitle className="text-base font-bold font-[family-name:var(--font-jakarta)]">
                Emergency SOS — Prototype Scope & Architecture
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground">
              Architectural disclosure for the NavSakhi personal software project prototype.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2 text-xs leading-relaxed text-muted-foreground">
            <div className="p-3.5 rounded-2xl bg-danger/10 border border-danger/20 text-foreground space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-danger">
                <AlertTriangle size={15} />
                <span>Prototype Disclosures (No Live Emergency Dispatch)</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                NavSakhi is a personal-interest software project and working prototype. In this local demonstration, 
                <strong> no real police dispatch, 112 emergency calls, or automated SMS/PSTN cellular broadcasts are conducted.</strong>
              </p>
            </div>

            <div className="space-y-2">
              <p className="font-bold text-foreground">Demonstration Capabilities:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground text-[11px]">
                <li><strong>Local Simulation:</strong> Authenticated users can simulate the response sequence, preview staged distress payloads, and inspect nearest safe havens.</li>
                <li><strong>User-Initiated Native Sharing:</strong> When triggered explicitly by the user, the browser's native share sheet (or SMS deep-link / clipboard) generates a verified tracking link with explicit user consent.</li>
                <li><strong>Privacy & Location Consent:</strong> NavSakhi never automatically polls or transmits your GPS coordinates merely by opening the interface. Explicit user action is required.</li>
              </ul>
            </div>

            <div className="p-3 rounded-2xl bg-secondary/50 border border-border/70 text-[11px] space-y-1">
              <span className="font-bold text-foreground block">Real-World Helplines:</span>
              <p>For actual distress in India, always dial <strong>112 (National Emergency)</strong> or <strong>1091 (Women Helpline)</strong>.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TimelineStep({ text, completed, active, timestamp }: { text: string, completed?: boolean, active?: boolean, timestamp?: string }) {
  return (
    <div className="relative z-10 flex items-start gap-4">
      <div className="mt-0.5 flex shrink-0 items-center justify-center bg-card">
        {completed ? <CheckCircle2 size={20} className="text-success" /> : active ? <Loader2 size={20} className="animate-spin text-danger" /> : <div className="h-5 w-5 rounded-full border-2 border-muted" />}
      </div>
      <div className="flex flex-col">
        <span className={`text-xs ${active ? "font-bold text-danger" : completed ? "font-semibold text-foreground" : "font-medium text-muted-foreground"}`}>{text}</span>
        {timestamp && <span className="text-[10px] text-muted-foreground font-medium">{timestamp}</span>}
      </div>
    </div>
  );
}

function ServiceCard({ icon: Icon, title, desc, color }: { icon: any, title: string, desc: string, color: string }) {
  return (
    <div className="p-3.5 rounded-2xl bg-secondary/40 border border-border/60 flex flex-col gap-2">
      <Icon size={20} className={color} />
      <div className="flex flex-col">
        <h4 className="font-bold text-xs text-foreground truncate">{title}</h4>
        <p className="text-[11px] font-medium text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}