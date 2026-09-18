"use client";

import { useState, useEffect } from "react";
import { 
  AlertOctagon, PhoneCall, MapPin, ShieldAlert, XCircle, CheckCircle2, Share2, Hospital, ShieldCheck, Loader2, Bot, Info, Navigation
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { emergencyService } from "@/api/services/emergencyService";
import { useEmergencySession } from "@/hooks/useEmergency";
import { EmergencyTimelineEvent } from "@/types/emergency";

export default function EmergencyPage() {
  const [status, setStatus] = useState<"idle" | "counting" | "active">("idle");
  const [countdown, setCountdown] = useState(5);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSharing, setIsSharing] = useState(false);

  // The hook continuously polls the backend and provides the complex EmergencyResponse DTO
  const { data } = useEmergencySession(sessionId);

  const handleShareLocation = () => {
    const shareUrl = async (lat: number, lng: number) => {
      if (isSharing) return;
      const url = `https://www.google.com/maps?q=${lat},${lng}`;
      if (navigator.share) {
        try {
          setIsSharing(true);
          await navigator.share({
            title: "SafeShe Emergency SOS Tracking",
            text: `Emergency! Track my live location here.`,
            url,
          });
        } catch (err) {
          console.error("Failed to share", err);
        } finally {
          setIsSharing(false);
        }
      } else {
        navigator.clipboard.writeText(`Please track my location immediately: ${url}`);
        alert("Tracking link copied to clipboard:\n" + url);
      }
    };

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => shareUrl(pos.coords.latitude, pos.coords.longitude),
        (err) => {
          // Fallback to DTO if permission denied
          if (data?.live_location?.coordinates) {
            shareUrl(data.live_location.coordinates[1], data.live_location.coordinates[0]);
          } else {
            alert("Could not detect location. Please enable GPS.");
          }
        },
        { enableHighAccuracy: true, timeout: 5000 }
      );
    } else if (data?.live_location?.coordinates) {
      shareUrl(data.live_location.coordinates[1], data.live_location.coordinates[0]);
    } else {
      alert("Live location not yet established.");
    }
  };

  const handleDialEmergency = () => {
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (isMobile) {
      window.location.href = "tel:112";
    } else {
      alert("Sorry, can't open dialer on this device. Please dial 112 from your phone.");
    }
  };

  const initiateEmergencyProtocol = async () => {
    try {
      // Step 1: Hit the SOS trigger endpoint to get the Session ID
      const response = await emergencyService.triggerSOS({
        current_location: "12.9716° N, 77.5946° E", // Placeholder until GPS provider is implemented
      });
      
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);

      // Step 2: The useEmergencySession hook automatically begins polling based on the sessionId
      // Future WebSockets will connect here dynamically within the service layer if needed.
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
    setCountdown(5);
    setStatus("counting");
  };

  const cancelSOS = () => {
    setStatus("idle");
    setCountdown(5);
    setSessionId(null); // This automatically pauses the polling hook
  };

  return (
    <div className="relative flex h-full min-h-full w-full flex-col items-center overflow-y-auto overflow-x-hidden px-6 py-12">
      {/* Background Danger Overlay */}
      <div className={`fixed inset-0 z-0 transition-colors duration-1000 ${status === 'active' ? 'bg-danger/10' : status === 'counting' ? 'bg-warning/10' : 'bg-transparent'}`} />
      
      <div className="relative z-10 flex w-full max-w-4xl flex-col items-center">
        
        {/* Header Section */}
        <div className="mb-16 flex flex-col items-center text-center">
          <AnimatePresence mode="wait">
            {status === "active" ? (
              <motion.div key="active" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-4 animate-pulse rounded-full border border-danger/30 bg-danger/20 px-5 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-danger">
                  Critical Alert Active
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-4xl font-extrabold tracking-tight text-foreground md:text-5xl">Assistance Dispatched</h1>
              </motion.div>
            ) : status === "counting" ? (
              <motion.div key="counting" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-4 rounded-full border border-warning/30 bg-warning/20 px-5 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-warning">
                  Initiating Protocol
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-4xl font-extrabold tracking-tight text-foreground md:text-5xl">Standby</h1>
              </motion.div>
            ) : (
              <motion.div key="idle" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center">
                <span className="mb-4 flex items-center gap-2 rounded-full border border-success/20 bg-success/15 px-5 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-success">
                  <ShieldCheck size={16} /> Status: Secure
                </span>
                <h1 className="font-[family-name:var(--font-jakarta)] text-4xl font-extrabold tracking-tight text-foreground md:text-5xl">Emergency Center</h1>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* SOS Button Section */}
        <div className="relative mb-20 flex items-center justify-center">
          {status === "active" && (
            <>
              <div className="absolute h-[300px] w-[300px] animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite] rounded-full bg-danger/20 opacity-75" />
              <div className="absolute h-[400px] w-[400px] animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite] rounded-full bg-danger/10 opacity-50" style={{ animationDelay: "0.5s" }} />
            </>
          )}

          <button
            onClick={status === "idle" ? triggerSOS : cancelSOS}
            className={`relative z-10 flex h-56 w-56 flex-col items-center justify-center rounded-full shadow-2xl transition-all duration-500 ${
              status === "active" ? "scale-110 cursor-default bg-danger text-white ring-8 ring-danger/30 shadow-[0_0_60px_rgba(225,29,72,0.6)]" : 
              status === "counting" ? "scale-105 bg-warning text-white ring-8 ring-warning/30 shadow-[0_0_60px_rgba(245,158,11,0.6)]" :
              "border-4 border-danger/80 bg-card text-danger shadow-[0_0_30px_rgba(225,29,72,0.15)] hover:scale-105 hover:bg-danger hover:text-white active:scale-95"
            }`}
          >
            {status === "counting" ? (
              <span className="font-[family-name:var(--font-jakarta)] text-7xl font-black">{countdown}</span>
            ) : (
              <>
                <AlertOctagon size={72} strokeWidth={1.5} className={status === "active" ? "animate-pulse" : ""} />
                <span className="mt-3 font-[family-name:var(--font-jakarta)] text-3xl font-black uppercase tracking-widest">
                  {status === "active" ? "SOS ON" : "SOS"}
                </span>
              </>
            )}
          </button>
        </div>

        {/* Content Section */}
        <div className="w-full">
          <AnimatePresence mode="popLayout">
            {status === "active" ? (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }} className="grid grid-cols-1 gap-8 md:grid-cols-2">
                
                {/* Left Column */}
                <div className="flex flex-col gap-6">
                  {/* Dynamic Deployment Sequence (from DTO) */}
                  <div className="glass-card flex flex-col rounded-3xl border-danger/30 p-8 shadow-danger/5">
                    <h3 className="mb-8 font-[family-name:var(--font-jakarta)] text-xl font-bold text-foreground">Deployment Sequence</h3>
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

                  {/* AI Agent Status Card (from DTO) */}
                  {data && (
                    <div className="glass-card flex flex-col rounded-3xl border-primary/20 bg-primary/5 p-6 shadow-primary/5">
                      <div className="flex items-center gap-2 mb-3">
                        <Bot size={20} className="text-primary animate-pulse" />
                        <h3 className="font-[family-name:var(--font-jakarta)] text-md font-bold uppercase tracking-wider text-primary">Intelligence Coordinator</h3>
                      </div>
                      <p className="text-sm font-bold text-foreground mb-1">{data.agent_status.action}</p>
                      <p className="text-xs font-medium text-muted-foreground mb-3">{data.agent_status.context}</p>
                      <div className="bg-background/50 rounded-xl p-3 border border-primary/10">
                        <span className="text-xs font-bold uppercase text-primary block mb-1">Agent Recommendation</span>
                        <span className="text-sm font-semibold">{data.agent_status.recommendation}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Column */}
                <div className="flex flex-col gap-5">
                  {/* Dynamic Safe Zones (from DTO) */}
                  <div className="grid grid-cols-2 gap-5">
                    {!data ? (
                      <>
                        <div className="h-28 bg-secondary/50 rounded-3xl animate-pulse" />
                        <div className="h-28 bg-secondary/50 rounded-3xl animate-pulse" />
                      </>
                    ) : (
                      data.safe_zones.map(zone => (
                        <ServiceCard 
                          key={zone.id}
                          icon={zone.type === 'Police' ? ShieldAlert : Hospital} 
                          title={zone.name} 
                          desc={`${zone.distance} (${zone.eta})`} 
                          color={zone.type === 'Police' ? 'text-primary' : 'text-success'} 
                        />
                      ))
                    )}
                  </div>

                  {/* Telemetry Tracking Data (from DTO) */}
                  {data && (
                     <div className="glass-card flex flex-col rounded-3xl border-border/50 p-6 gap-4">
                       <div className="flex items-center justify-between border-b border-border/50 pb-4">
                          <div className="flex flex-col">
                            <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-1"><MapPin size={12}/> Live Location</span>
                            <span className="text-sm font-bold mt-1 tracking-wider text-primary">GPS ACTIVE: LIVE TRACKING</span>
                          </div>
                          <span className="text-[10px] bg-secondary/80 px-2 py-1 rounded-md font-bold text-muted-foreground">Accuracy: {data.live_location.accuracy}m</span>
                       </div>
                       
                       <div className="flex flex-col gap-2">
                         <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-1">Notifying Contacts</span>
                         {data.contacts.map(contact => (
                           <div key={contact.id} className="flex items-center justify-between">
                             <span className="text-sm font-semibold">{contact.name} <span className="text-xs text-muted-foreground font-normal">({contact.relationship})</span></span>
                             <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                               contact.notification_status === 'Notified' ? 'bg-success/15 text-success border border-success/20' : 'bg-warning/15 text-warning border border-warning/20'
                             }`}>
                               {contact.notification_status}
                             </span>
                           </div>
                         ))}
                       </div>
                     </div>
                  )}

                  {/* Actions */}
                  <Button size="lg" onClick={handleDialEmergency} className="h-16 w-full rounded-2xl bg-foreground text-lg font-bold text-background shadow-xl transition-transform hover:-translate-y-1 hover:bg-foreground/90 gap-3">
                    <PhoneCall size={22} /> Dial Emergency (112)
                  </Button>
                  <Button size="lg" onClick={handleShareLocation} variant="outline" className="h-16 w-full rounded-2xl border-danger/50 text-lg font-bold text-danger backdrop-blur-sm hover:bg-danger/10 gap-3">
                    <Share2 size={22} /> Share Live Tracking Link
                  </Button>
                  <Button size="lg" variant="ghost" onClick={cancelSOS} className="mt-2 h-12 w-full rounded-full font-medium text-muted-foreground hover:bg-secondary gap-2">
                    <XCircle size={18} /> Cancel False Alarm
                  </Button>
                </div>
              </motion.div>
            ) : status === "counting" ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex w-full justify-center">
                <Button size="lg" onClick={cancelSOS} className="h-14 w-full max-w-sm rounded-full bg-secondary text-lg font-bold text-foreground hover:bg-secondary/80">
                  Cancel SOS
                </Button>
              </motion.div>
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="glass-card flex flex-col items-center justify-center rounded-3xl border-dashed border-border/50 px-6 py-12 text-center">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-secondary/50 text-muted-foreground">
                  <MapPin size={28} />
                </div>
                <h3 className="font-[family-name:var(--font-jakarta)] text-xl font-bold text-foreground">Passive Telemetry Active</h3>
                <p className="mt-2 max-w-md text-sm font-light leading-relaxed text-muted-foreground">
                  Your agent is actively monitoring your surroundings. No external contacts will be notified unless the SOS protocol is manually initiated.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function TimelineStep({ text, completed, active, timestamp }: { text: string, completed?: boolean, active?: boolean, timestamp?: string }) {
  return (
    <div className="relative z-10 flex items-start gap-5">
      <div className="mt-0.5 flex shrink-0 items-center justify-center bg-card">
        {completed ? <CheckCircle2 size={24} className="text-success" /> : active ? <Loader2 size={24} className="animate-spin text-danger" /> : <div className="h-6 w-6 rounded-full border-2 border-muted" />}
      </div>
      <div className="flex flex-col">
        <span className={`text-md ${active ? "font-bold text-danger" : completed ? "font-semibold text-foreground" : "font-medium text-muted-foreground"}`}>{text}</span>
        {timestamp && <span className="text-xs text-muted-foreground font-medium">{timestamp}</span>}
      </div>
    </div>
  );
}

function ServiceCard({ icon: Icon, title, desc, color }: { icon: any, title: string, desc: string, color: string }) {
  return (
    <div className="glass-card flex flex-col gap-3 rounded-3xl border-border/50 p-5">
      <Icon size={28} className={color} />
      <div className="flex flex-col">
        <h4 className="font-[family-name:var(--font-jakarta)] text-md font-bold text-foreground">{title}</h4>
        <p className="text-sm font-medium text-muted-foreground">{desc}</p>
      </div>
    </div>
  );
}