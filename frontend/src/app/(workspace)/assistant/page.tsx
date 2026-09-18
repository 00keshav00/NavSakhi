"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Bot, Send, Mic, Activity, MapPin, CloudRain, ShieldCheck, 
  AlertTriangle, Radio, Settings, Navigation, Clock, Network, Cpu, Database
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAssistant } from "@/hooks/useAssistant";

export default function AssistantPage() {
  const { messages, latestContext, isTyping, sendMessage } = useAssistant();
  const [inputValue, setInputValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping]);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim() && !isTyping) {
      sendMessage(inputValue);
      setInputValue("");
    }
  };

  const handleSuggestion = (query: string) => {
    if (!isTyping) {
      sendMessage(query);
    }
  };

  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12">
      
      {/* Left Panel: Agent & Context (~25%) */}
      <aside className="relative z-10 flex h-full flex-col border-r border-border bg-card/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] backdrop-blur-3xl lg:col-span-3">
        <ScrollArea className="flex-1 p-6">
          <div className="flex items-center gap-3 mb-8 pb-4 border-b border-border/50">
            <div className="bg-primary/20 p-2 rounded-xl text-primary">
              <Bot size={28} className={latestContext?.agent_status.status === 'Analyzing' ? 'animate-pulse' : ''} />
            </div>
            <div className="flex flex-col">
              <h2 className="font-[family-name:var(--font-jakarta)] text-lg font-extrabold text-foreground leading-none">Intelligence</h2>
              <span className="text-xs font-bold uppercase tracking-widest text-primary mt-1">Coordinator</span>
            </div>
          </div>

          <div className="flex flex-col gap-6">
            
            {/* Agent Status */}
            <div className="flex flex-col gap-2">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">System Status</h3>
              <div className="glass-card flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                <span className="text-sm font-semibold">{latestContext?.agent_status.status || 'Initializing...'}</span>
                {isTyping && <Activity size={14} className="text-primary animate-pulse" />}
              </div>
            </div>

            {/* Journey Context */}
            {latestContext?.context && (
              <div className="flex flex-col gap-3">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Active Context</h3>
                
                <ContextPill icon={Navigation} label="Destination" value={latestContext.context.destination || 'None'} />
                <ContextPill icon={ShieldCheck} label="Safety Score" value={`${latestContext.context.safety_score}%`} color="text-success" />
                <ContextPill icon={CloudRain} label="Weather" value={latestContext.context.weather || 'Unknown'} />
                <ContextPill icon={Clock} label="ETA" value={latestContext.context.eta || '--'} />
                
              </div>
            )}

            {/* Provider Health */}
            {latestContext?.provider_health && (
               <div className="flex flex-col gap-3 mt-4">
                 <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Provider Uplinks</h3>
                 <div className="flex flex-col gap-2">
                   {latestContext.provider_health.map(provider => (
                     <div key={provider.name} className="flex items-center justify-between">
                       <span className="text-xs font-medium text-muted-foreground">{provider.name}</span>
                       <span className="relative flex h-2 w-2">
                         {provider.status === 'Connected' ? (
                           <>
                             <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                             <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                           </>
                         ) : (
                           <span className="relative inline-flex rounded-full h-2 w-2 bg-warning"></span>
                         )}
                       </span>
                     </div>
                   ))}
                 </div>
               </div>
            )}

          </div>
        </ScrollArea>
      </aside>

      {/* Center Panel: Chat Interface (~50%) */}
      <main className="relative flex h-full flex-col bg-background/95 lg:col-span-6 border-r border-border/50 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
        
        {/* Chat History */}
        <ScrollArea className="flex-1 p-6">
          <div className="flex flex-col gap-6 pb-20">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div 
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`px-5 py-3 rounded-2xl ${
                      msg.role === 'user' 
                        ? 'bg-foreground text-background rounded-tr-sm' 
                        : 'glass-card bg-primary/10 border-primary/20 text-foreground rounded-tl-sm'
                    }`}>
                      <p className="text-sm font-medium leading-relaxed">{msg.content}</p>
                    </div>
                    <span className="text-[10px] font-bold text-muted-foreground mt-1.5 px-1">{msg.timestamp}</span>
                  </div>
                </motion.div>
              ))}
              
              {isTyping && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex w-full justify-start">
                  <div className="glass-card bg-secondary/50 px-5 py-4 rounded-2xl rounded-tl-sm flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 glass-card border-t border-border/50 bg-card/80 backdrop-blur-xl p-4">
          
          {/* Quick Actions */}
          <div className="flex gap-2 mb-3 overflow-x-auto no-scrollbar pb-1">
            {latestContext?.quick_suggestions.map((sug, i) => (
              <button 
                key={i} 
                onClick={() => handleSuggestion(sug)}
                disabled={isTyping}
                className="whitespace-nowrap px-3 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-xs font-bold text-primary hover:bg-primary hover:text-white transition-colors disabled:opacity-50"
              >
                {sug}
              </button>
            ))}
          </div>

          <form onSubmit={handleSend} className="relative flex items-center gap-2">
            <Button type="button" variant="ghost" size="icon" className="shrink-0 h-12 w-12 rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground">
              <Mic size={20} />
            </Button>
            <div className="relative flex-1">
              <Input 
                value={inputValue} 
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isTyping}
                placeholder="Ask your Intelligence Coordinator..." 
                className="h-12 w-full rounded-full border-border/50 bg-secondary/30 pl-5 pr-14 text-sm font-medium focus-visible:ring-primary/50"
              />
              <Button type="submit" disabled={!inputValue.trim() || isTyping} size="icon" className="absolute right-1 top-1 bottom-1 h-10 w-10 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-transform active:scale-95 disabled:opacity-50 disabled:scale-100">
                <Send size={16} className="ml-1" />
              </Button>
            </div>
          </form>
        </div>
      </main>

      {/* Right Panel: Reasoning & Memory (~25%) */}
      <aside className="relative z-10 flex h-full flex-col bg-card/40 lg:col-span-3">
        <ScrollArea className="flex-1 p-6">
          <div className="flex flex-col gap-6">
            
            <div className="flex items-center gap-2 mb-2">
              <Cpu size={16} className="text-muted-foreground" />
              <h3 className="font-[family-name:var(--font-jakarta)] text-sm font-bold uppercase tracking-wider text-muted-foreground">Inspector</h3>
            </div>

            {/* Confidence Gauge */}
            {latestContext?.reasoning && (
              <div className="glass-card flex flex-col gap-3 rounded-2xl p-5 border-border/50">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Confidence</span>
                  <span className={`text-xl font-black ${
                    latestContext.reasoning.confidence >= 90 ? 'text-success' : 
                    latestContext.reasoning.confidence >= 70 ? 'text-warning' : 'text-danger'
                  }`}>{latestContext.reasoning.confidence}%</span>
                </div>
                <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                   <motion.div 
                     initial={{ width: 0 }} animate={{ width: `${latestContext.reasoning.confidence}%` }}
                     className={`h-full rounded-full ${
                      latestContext.reasoning.confidence >= 90 ? 'bg-success' : 
                      latestContext.reasoning.confidence >= 70 ? 'bg-warning' : 'bg-danger'
                     }`}
                   />
                </div>
              </div>
            )}

            {/* Reasoning Trace */}
            {latestContext?.reasoning && (
               <div className="glass-card flex flex-col gap-4 rounded-2xl p-5 border-border/50 bg-secondary/10">
                 <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                   <Network size={14} className="text-primary"/> Logic Trace
                 </h3>
                 <div className="flex flex-col gap-3 relative">
                   <div className="absolute top-2 bottom-2 left-[5px] w-0.5 bg-border/50" />
                   {latestContext.reasoning.summary.map((step, i) => (
                     <div key={i} className="flex items-start gap-3 relative z-10">
                       <div className="w-3 h-3 rounded-full border-2 border-primary bg-background shrink-0 mt-0.5" />
                       <span className="text-xs font-medium text-muted-foreground leading-tight">{step}</span>
                     </div>
                   ))}
                 </div>
               </div>
            )}

            {/* Memory Panel */}
            {latestContext?.memory && (
               <div className="flex flex-col gap-3 mt-4">
                 <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                   <Database size={12}/> Pinned Memory
                 </h3>
                 <div className="flex flex-col gap-2">
                   {latestContext.memory.pinned_info.map((info, i) => (
                     <div key={i} className="bg-background/50 border border-border/50 rounded-lg p-3 text-xs font-medium text-foreground">
                       {info}
                     </div>
                   ))}
                 </div>
               </div>
            )}

          </div>
        </ScrollArea>
      </aside>

    </div>
  );
}

// ---------------------------------------------------------
// Sub-components
// ---------------------------------------------------------

function ContextPill({ icon: Icon, label, value, color }: { icon: any, label: string, value: string, color?: string }) {
  return (
    <div className="glass-card flex items-center gap-3 rounded-xl p-3 border-border/50 bg-background/50">
      <div className={`p-2 rounded-lg bg-secondary/50 ${color || 'text-muted-foreground'}`}>
        <Icon size={16} />
      </div>
      <div className="flex flex-col">
        <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold text-foreground">{value}</span>
      </div>
    </div>
  );
}
