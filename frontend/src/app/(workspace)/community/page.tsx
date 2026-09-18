"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  MapPin, AlertTriangle, Plus, Clock, Users, Construction, Moon, Sparkles, 
  MessageSquare, ShieldCheck, HelpCircle, Activity, Info, RefreshCcw, Layers
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import SafeMap from "@/components/map/SafeMap";
import { useCommunityIntelligence, useCreateReport } from "@/hooks/useCommunity";
import { CommunityReportResponse, VerificationStatus } from "@/types/community";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

// Zod Schema for Report Validation
const reportSchema = z.object({
  report_type: z.enum(["Harassment", "Dark Area", "Heavy Crowd", "Construction"]),
  severity: z.enum(["High", "Medium", "Low"]),
  description: z.string().min(5, "Description must be at least 5 characters.").max(500),
  is_anonymous: z.boolean().default(false),
});

type ReportFormValues = z.infer<typeof reportSchema>;

export default function CommunityPage() {
  const [typeFilter, setTypeFilter] = useState("All");
  const [verFilter, setVerFilter] = useState("All");
  const [heatmapMode, setHeatmapMode] = useState<"Verified" | "All">("Verified");
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data, isLoading, error, refresh } = useCommunityIntelligence({ type: typeFilter, verification: verFilter });
  const { submitReport, isSubmitting } = useCreateReport();

  const form = useForm<ReportFormValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      report_type: "Harassment",
      severity: "High",
      description: "",
      is_anonymous: false
    }
  });

  const onSubmit = (values: ReportFormValues) => {
    // Generate slight offset around Bangalore for demo purposes since we don't have a map picker
    const offsetLon = 77.5946 + (Math.random() * 0.02 - 0.01);
    const offsetLat = 12.9716 + (Math.random() * 0.02 - 0.01);
    
    submitReport({
      location: { type: "Point", coordinates: [offsetLon, offsetLat] },
      ...values
    }, () => {
      setIsDialogOpen(false);
      form.reset();
      refresh();
    });
  };

  const reports = data?.reports || [];
  const activeHeatmapData = heatmapMode === "Verified" ? data?.heatmap_data.verified_only : data?.heatmap_data.all_reports;

  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12">
      <aside className="relative z-10 flex h-full flex-col border-r border-border bg-card/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] backdrop-blur-3xl lg:col-span-5 dark:shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
        
        {/* Header Area */}
        <div className="flex shrink-0 flex-col border-b border-border/50 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-[family-name:var(--font-jakarta)] text-3xl font-extrabold tracking-tight text-foreground flex items-center gap-2">
                Intelligence
              </h2>
              <p className="mt-1 flex items-center gap-1.5 text-sm font-light text-muted-foreground">
                <Sparkles size={14} className="text-primary" /> Verified crowdsourced anomaly data.
              </p>
            </div>
            
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger>
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-foreground text-background shadow-lg hover:scale-105 active:scale-95 p-0 cursor-pointer transition-all">
                  <Plus size={24} />
                </div>
              </DialogTrigger>
              <DialogContent className="glass border-border/50 sm:max-w-md bg-card">
                <DialogHeader>
                  <DialogTitle className="font-[family-name:var(--font-jakarta)] text-2xl font-bold">Report Anomaly</DialogTitle>
                  <DialogDescription className="font-light">Your report will enter the community verification queue.</DialogDescription>
                </DialogHeader>
                <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4 py-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-bold uppercase text-muted-foreground">Anomaly Type</label>
                    <select {...form.register("report_type")} className="flex h-12 w-full rounded-xl border border-border/50 bg-background/50 px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                      <option value="Harassment">Harassment</option>
                      <option value="Dark Area">Dark Area</option>
                      <option value="Heavy Crowd">Heavy Crowd</option>
                      <option value="Construction">Construction</option>
                    </select>
                  </div>
                  
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-bold uppercase text-muted-foreground">Severity</label>
                    <select {...form.register("severity")} className="flex h-12 w-full rounded-xl border border-border/50 bg-background/50 px-4 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-bold uppercase text-muted-foreground">Details</label>
                    <Textarea 
                      {...form.register("description")}
                      placeholder="What's happening?" 
                      className="h-24 resize-none rounded-xl border-border/50 bg-background/50" 
                    />
                    {form.formState.errors.description && <span className="text-xs text-danger">{form.formState.errors.description.message}</span>}
                  </div>
                  
                  <label className="flex items-center gap-2 text-sm text-muted-foreground font-medium cursor-pointer">
                    <input type="checkbox" {...form.register("is_anonymous")} className="rounded border-border text-primary focus:ring-primary" />
                    Submit Anonymously
                  </label>

                  <DialogFooter className="mt-2">
                    <Button type="submit" disabled={isSubmitting} className="btn-premium h-12 w-full rounded-xl bg-primary font-bold text-primary-foreground shadow-lg shadow-primary/20">
                      {isSubmitting ? "Submitting..." : "Submit to Queue"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* Filters Area */}
          <div className="flex flex-col gap-3 mt-6">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Filter by Verification</span>
            <div className="flex gap-2 w-full">
              <FilterPill label="All Status" active={verFilter === "All"} onClick={() => setVerFilter("All")} />
              <FilterPill label="Verified" active={verFilter === "Verified"} onClick={() => setVerFilter("Verified")} color="success" />
              <FilterPill label="Pending" active={verFilter === "Pending"} onClick={() => setVerFilter("Pending")} color="warning" />
              <FilterPill label="Unverified" active={verFilter === "Unverified"} onClick={() => setVerFilter("Unverified")} color="danger" />
            </div>
            
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground mt-2">Filter by Type</span>
            <ScrollArea className="h-10 w-full whitespace-nowrap">
              <div className="flex w-max gap-2 pb-2">
                {["All", "Harassment", "Dark Area", "Heavy Crowd", "Construction"].map(filter => (
                  <button key={filter} onClick={() => setTypeFilter(filter)} className={`rounded-full border px-4 py-1.5 text-xs font-bold transition-all duration-200 ${typeFilter === filter ? "border-primary bg-primary text-primary-foreground shadow-md" : "border-transparent bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"}`}>{filter}</button>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>

        {/* Content Area */}
        <ScrollArea className="flex-1 bg-background/30 p-6">
          <AnimatePresence mode="popLayout">
            {isLoading ? (
              <CommunitySkeleton />
            ) : error ? (
               <div className="flex flex-col items-center justify-center p-10 text-center opacity-80 gap-3">
                 <AlertTriangle size={32} className="text-danger" />
                 <p className="text-sm font-medium">{error}</p>
                 <Button onClick={refresh} variant="outline">Retry</Button>
               </div>
            ) : data && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-8 pb-10">
                
                {/* Statistics Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <StatCard label="Total Reports" value={data.statistics.total} />
                  <StatCard label="Verified Safes" value={data.statistics.safe_zones} icon={<ShieldCheck size={16}/>} color="text-success" />
                  <StatCard label="Pending" value={data.statistics.pending} icon={<Clock size={16}/>} color="text-warning" />
                  <StatCard label="High Risk Areas" value={data.statistics.high_risk_areas} icon={<AlertTriangle size={16}/>} color="text-danger" />
                </div>

                {/* AI Compatibility Notice */}
                <div className="glass-card flex items-start gap-3 rounded-2xl bg-primary/5 p-4 border border-primary/20">
                  <Info size={20} className="text-primary mt-0.5 shrink-0" />
                  <p className="text-xs font-medium leading-relaxed text-muted-foreground">
                    Only <span className="font-bold text-success">Verified</span> reports are injected into the Agent's pathfinding matrix. Pending and Unverified reports remain visible for community awareness only.
                  </p>
                </div>

                {/* Trending & Insights */}
                <div className="flex flex-col gap-3">
                  <h3 className="font-[family-name:var(--font-jakarta)] text-sm font-bold uppercase tracking-wider text-muted-foreground">Trending Insights</h3>
                  <div className="glass-card rounded-2xl p-5 bg-secondary/20 flex flex-col gap-3">
                    {data.insights.map((insight, idx) => (
                      <div key={idx} className="flex items-start gap-2">
                        <Activity size={16} className="text-primary shrink-0 mt-0.5" />
                        <span className="text-sm font-medium text-foreground">{insight}</span>
                      </div>
                    ))}
                    <div className="mt-2 pt-3 border-t border-border/50 flex flex-col gap-1">
                      <span className="text-xs font-bold text-muted-foreground uppercase">Top Issues Today</span>
                      <div className="flex gap-2 flex-wrap mt-1">
                        {data.trending.most_common_incidents.map((inc, i) => (
                          <span key={i} className="px-2 py-1 bg-background rounded text-xs font-medium border border-border/50">{inc}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Reports Feed */}
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-[family-name:var(--font-jakarta)] text-sm font-bold uppercase tracking-wider text-muted-foreground">Live Feed</h3>
                    <span className="text-xs font-bold text-muted-foreground">{reports.length} Found</span>
                  </div>
                  
                  {reports.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-10 text-center opacity-50">
                      <MessageSquare size={32} className="mb-3 text-muted-foreground" />
                      <p className="text-sm font-medium">No reports match your filters.</p>
                    </div>
                  ) : (
                    reports.map((report) => (
                      <motion.div key={report._id || report.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} layout>
                        <ReportCard report={report} />
                      </motion.div>
                    ))
                  )}
                </div>

              </motion.div>
            )}
          </AnimatePresence>
        </ScrollArea>
      </aside>

      {/* Main Map Area */}
      <main className="relative hidden h-full w-full bg-background/95 lg:col-span-7 lg:block">
        
        {/* Heatmap Toggle HUD */}
        <div className="absolute top-6 right-6 z-10 glass-card bg-background/80 backdrop-blur-md rounded-xl p-2 border border-border/50 shadow-lg flex items-center gap-1">
          <Layers size={14} className="mx-2 text-muted-foreground" />
          <button 
            onClick={() => setHeatmapMode("Verified")} 
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${heatmapMode === 'Verified' ? 'bg-primary text-white shadow-md' : 'hover:bg-secondary text-muted-foreground'}`}
          >
            Verified Heatmap
          </button>
          <button 
            onClick={() => setHeatmapMode("All")} 
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${heatmapMode === 'All' ? 'bg-secondary text-foreground shadow-md' : 'hover:bg-secondary text-muted-foreground'}`}
          >
            All Data
          </button>
        </div>

        <SafeMap 
          reports={reports} // Display markers for the currently filtered reports
          // Heatmap layer integration would go here if Safemap supported heatmap rendering natively. 
          // For now, it consumes the reports array to render exact marker coordinates.
        />
      </main>
    </div>
  );
}

// ---------------------------------------------------------
// Sub-components
// ---------------------------------------------------------

function FilterPill({ label, active, onClick, color }: { label: string, active: boolean, onClick: () => void, color?: string }) {
  let baseColor = "border-primary bg-primary text-primary-foreground";
  if (color === "success") baseColor = "border-success bg-success text-white";
  if (color === "warning") baseColor = "border-warning bg-warning text-white";
  if (color === "danger") baseColor = "border-danger bg-danger text-white";

  return (
    <button 
      onClick={onClick} 
      className={`flex-1 rounded-xl border py-2 text-[10px] sm:text-xs font-bold transition-all duration-200 ${active ? `${baseColor} shadow-md` : "border-transparent bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"}`}
    >
      {label}
    </button>
  );
}

function StatCard({ label, value, icon, color }: { label: string, value: number, icon?: any, color?: string }) {
  return (
    <div className="glass-card flex flex-col gap-1 rounded-2xl p-4 bg-secondary/10">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</span>
        {icon && <span className={color}>{icon}</span>}
      </div>
      <span className={`text-2xl font-black mt-1 ${color || 'text-foreground'}`}>{value}</span>
    </div>
  );
}

function ReportCard({ report }: { report: CommunityReportResponse }) {
  let styles = { icon: AlertTriangle, color: "text-primary", bg: "bg-primary/10" };
  
  if (report.report_type === 'Harassment') styles = { icon: AlertTriangle, color: "text-danger", bg: "bg-danger/10" };
  else if (report.report_type === 'Dark Area') styles = { icon: Moon, color: "text-warning", bg: "bg-warning/10" };
  else if (report.report_type === 'Heavy Crowd') styles = { icon: Users, color: "text-primary", bg: "bg-primary/10" };
  else if (report.report_type === 'Construction') styles = { icon: Construction, color: "text-muted-foreground", bg: "bg-secondary" };

  const Icon = styles.icon;
  
  // Verification Badge Styles
  const verBadge = {
    'Verified': 'bg-success/15 text-success border-success/30',
    'Pending': 'bg-warning/15 text-warning border-warning/30',
    'Unverified': 'bg-danger/15 text-danger border-danger/30',
  }[report.verification_status];

  const VerIcon = {
    'Verified': ShieldCheck,
    'Pending': Clock,
    'Unverified': HelpCircle,
  }[report.verification_status];

  return (
    <div className="glass-card flex flex-col gap-4 rounded-3xl p-5 transition-all hover:-translate-y-1 hover:shadow-lg border-border/50 group">
      
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`flex h-12 w-12 items-center justify-center rounded-2xl shadow-inner shrink-0 ${styles.bg} ${styles.color}`}>
            <Icon size={24} />
          </div>
          <div className="flex flex-col">
            <span className="font-[family-name:var(--font-jakarta)] text-md font-bold text-foreground leading-none">{report.report_type}</span>
            <span className="mt-1 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Clock size={12} /> {report.time} &bull; {report.distance}m away
            </span>
          </div>
        </div>
        
        {/* Severity Badge */}
        <div className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest shrink-0 ${
          report.severity === 'High' ? 'border-danger/20 bg-danger/10 text-danger' : 
          report.severity === 'Medium' ? 'border-warning/20 bg-warning/10 text-warning' : 
          'border-border/50 bg-secondary/50 text-muted-foreground'
        }`}>
          {report.severity}
        </div>
      </div>
      
      <p className="text-sm font-medium leading-relaxed text-foreground/90">{report.description}</p>
      
      <div className="mt-1 flex items-center justify-between border-t border-border/50 pt-3">
        {/* Verification Status Badge */}
        <div className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${verBadge}`}>
          <VerIcon size={14} /> 
          {report.verification_status} 
          {report.verification_status === 'Verified' && report.verification_timestamp && ` (${report.verification_timestamp})`}
        </div>

        {/* Upvotes (Future Placeholder) */}
        <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground bg-secondary/50 px-2 py-1 rounded-full">
          👍 {report.upvotes}
        </div>
      </div>
    </div>
  );
}

function CommunitySkeleton() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      <div className="grid grid-cols-2 gap-4">
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
        <div className="h-20 bg-secondary/50 rounded-2xl"></div>
      </div>
      <div className="h-24 bg-secondary/50 rounded-2xl"></div>
      <div className="flex flex-col gap-4">
        <div className="h-32 bg-secondary/50 rounded-3xl"></div>
        <div className="h-32 bg-secondary/50 rounded-3xl"></div>
      </div>
    </div>
  );
}