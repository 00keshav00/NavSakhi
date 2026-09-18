"use client";

import { 
  Activity, 
  Map, 
  CloudRain, 
  Users, 
  CheckCircle2, 
  Bot,
  ShieldAlert,
  ArrowRight,
  Sparkles
} from "lucide-react";

const aiHistory = [
  {
    id: 1,
    date: "Today",
    events: [
      { time: "2:45 PM", title: "Journey Completed", desc: "Arrived safely at Destination. Safety score maintained above 90.", icon: CheckCircle2, color: "text-success", bg: "bg-success/10", ai: false },
      { time: "2:30 PM", title: "Alternative Suggested", desc: "Rerouted to Main Ave due to sudden crowd increase.", icon: Map, color: "text-primary", bg: "bg-primary/10", ai: true },
      { time: "2:15 PM", title: "Community Updated", desc: "Scanned 3 new local reports. No immediate threats detected.", icon: Users, color: "text-iris", bg: "bg-iris/10", ai: true },
    ]
  },
  {
    id: 2,
    date: "Yesterday",
    events: [
      { time: "6:00 PM", title: "Weather Checked", desc: "Detected heavy rain. Suggested well-lit indoor transit route.", icon: CloudRain, color: "text-info", bg: "bg-blue-500/10", ai: true },
      { time: "5:55 PM", title: "Safety Calculated", desc: "Analyzed historical crime data for the downtown sector. Score: 88/100.", icon: ShieldAlert, color: "text-warning", bg: "bg-warning/10", ai: true },
      { time: "5:50 PM", title: "Journey Planned", desc: "User initiated route to Downtown Station.", icon: Activity, color: "text-muted-foreground", bg: "bg-secondary", ai: false },
    ]
  }
];

export default function ActivityCenterPage() {
  return (
    <div className="flex h-full w-full flex-col items-center overflow-y-auto px-6 py-12 scroll-smooth">
      
      {/* Header Section */}
      <div className="mb-16 flex w-full max-w-3xl flex-col items-center text-center animate-slide-up" style={{ animationDelay: "0.1s" }}>
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-iris/20 text-primary border border-primary/20 shadow-lg shadow-primary/5">
          <Bot size={32} />
        </div>
        <h1 className="text-4xl font-[family-name:var(--font-jakarta)] font-extrabold text-foreground tracking-tight">AI Audit Log</h1>
        <p className="mt-4 text-muted-foreground max-w-lg text-lg font-light leading-relaxed">
          A transparent, cryptographically secure timeline of every calculation, check, and decision your SafeShe agent has executed.
        </p>
      </div>

      {/* Timeline Section */}
      <div className="w-full max-w-3xl animate-slide-up" style={{ animationDelay: "0.2s" }}>
        {aiHistory.map((day) => (
          <div key={day.id} className="mb-12">
            
            <h2 className="mb-8 sticky top-4 z-20 inline-flex items-center rounded-full border border-border/50 bg-background/80 px-5 py-2 text-sm font-bold text-foreground shadow-sm backdrop-blur-xl">
              {day.date}
            </h2>
            
            <div className="relative border-l-2 border-border/50 ml-6 pl-10 space-y-8">
              {day.events.map((event, i) => (
                <div key={i} className="relative group">
                  
                  {/* Timeline Node */}
                  <div className={`absolute -left-[51px] top-1 flex h-12 w-12 items-center justify-center rounded-full border-4 border-background ${event.bg} ${event.color} shadow-sm transition-transform duration-300 group-hover:scale-110 group-hover:shadow-md z-10`}>
                    <event.icon size={20} />
                  </div>

                  {/* Event Card */}
                  <div className="glass-card flex flex-col gap-3 rounded-3xl p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                    <div className="flex items-start justify-between">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-3">
                          <h3 className="font-[family-name:var(--font-jakarta)] font-bold text-foreground text-lg">{event.title}</h3>
                          {event.ai && (
                            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary border border-primary/20">
                              <Sparkles size={10} /> AI Action
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-semibold text-muted-foreground mt-1 uppercase tracking-wider">{event.time}</span>
                      </div>
                    </div>
                    
                    <p className="text-sm font-light leading-relaxed text-muted-foreground mt-1">
                      {event.desc}
                    </p>

                    {event.ai && (
                      <button className="mt-4 flex w-fit items-center gap-1.5 text-xs font-bold text-primary hover:text-primary/80 transition-colors uppercase tracking-wider">
                        View analytics <ArrowRight size={14} />
                      </button>
                    )}
                  </div>
                  
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}