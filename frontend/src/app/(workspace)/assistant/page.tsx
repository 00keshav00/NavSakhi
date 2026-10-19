"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Bot, Send, Mic, Activity, CloudRain, ShieldCheck, 
  AlertTriangle, Navigation, Clock, Network, Cpu, Database,
  Volume2, Square, Check, X, Globe, AlertCircle, Sparkles
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { useAssistant } from "@/hooks/useAssistant";
import { useVoiceAssistant } from "@/hooks/useVoiceAssistant";
import { mergeTranscriptWithInput, SUPPORTED_VOICE_LANGUAGES } from "@/utils/voiceUtils";
import { VoiceConsentModal } from "@/components/assistant/VoiceConsentModal";
import { AIChatInput } from "@/components/ui/ai-chat-input";

function formatMessageTime(rawTime?: string): string {
  if (!rawTime) return "";
  try {
    const d = new Date(rawTime);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  } catch {
    // fallback
  }
  return rawTime;
}

export default function AssistantPage() {
  const { messages, latestContext, isTyping, sendMessage } = useAssistant();
  const [inputValue, setInputValue] = useState("");
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const hasUserMessages = messages.some((m) => m.role === "user");

  // Initialize Inspector open state on larger desktop screens
  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth >= 1024) {
      setIsInspectorOpen(true);
    }
  }, []);

  // Initialize Voice Assistant Hook
  const voice = useVoiceAssistant({
    onTranscriptReceived: (transcript) => {
      setInputValue((prev) => mergeTranscriptWithInput(prev, transcript));
    },
  });

  // Auto-read incoming assistant replies if autoReadAloud is enabled
  useEffect(() => {
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "assistant") {
        voice.handleIncomingMessage(lastMsg.id, lastMsg.content, lastMsg.role);
      }
    }
  }, [messages, voice]);

  // Auto scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping, voice.recognitionState]);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim() && !isTyping) {
      // If voice recognition is still listening, stop it
      if (voice.recognitionState === "listening") {
        voice.stopListening();
      }
      sendMessage(inputValue);
      setInputValue("");
    }
  };

  const handleSuggestion = (query: string) => {
    if (!isTyping) {
      sendMessage(query);
    }
  };

  const isListening = voice.recognitionState === "listening";

  return (
    <div className="grid h-screen w-full grid-cols-1 overflow-hidden bg-background lg:grid-cols-12">
      {/* Screen Reader Announcements */}
      <div aria-live="polite" className="sr-only">
        {isListening
          ? "Microphone listening. Speak your question."
          : voice.synthesisState === "speaking"
          ? "Speaking assistant response aloud."
          : voice.error
          ? `Voice error: ${voice.error}`
          : ""}
      </div>

      {/* Voice Privacy Consent Modal */}
      <VoiceConsentModal
        isOpen={voice.needsConsentModal}
        onConsent={voice.grantConsent}
        onDecline={voice.denyConsent}
      />
      
      {/* Left Panel: Agent & Context (~25%) */}
      <aside className="relative z-10 hidden lg:flex h-full flex-col border-r border-border bg-card/60 shadow-[4px_0_24px_rgba(0,0,0,0.02)] backdrop-blur-3xl lg:col-span-3">
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
            
            {/* System & Voice Status */}
            <div className="flex flex-col gap-2">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">System Status</h3>
              <div className="glass-card flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                <span className="text-sm font-semibold">{latestContext?.agent_status.status || 'Initializing...'}</span>
                {isTyping && <Activity size={14} className="text-primary animate-pulse" />}
              </div>
            </div>

            {/* Voice Preferences Controls */}
            <div className="flex flex-col gap-2.5 p-3.5 rounded-xl border border-border/60 bg-secondary/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Volume2 size={15} className="text-primary" />
                  <span className="text-xs font-bold text-foreground">Auto-read replies</span>
                </div>
                <Switch
                  checked={voice.autoReadAloud}
                  onCheckedChange={voice.toggleAutoReadAloud}
                  disabled={!voice.isSynthesisSupported}
                  aria-label="Toggle auto-read replies aloud"
                />
              </div>

              {/* Voice Language Selector */}
              <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[11px]">
                <span className="text-muted-foreground font-medium flex items-center gap-1">
                  <Globe size={12} className="text-primary" /> Voice Language
                </span>
                <select
                  value={voice.selectedLanguage}
                  onChange={(e) => voice.setSelectedLanguage(e.target.value)}
                  className="bg-background text-foreground text-[11px] font-semibold rounded-md px-1.5 py-0.5 border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                  aria-label="Select voice assistant language"
                >
                  {SUPPORTED_VOICE_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Journey Context */}
            {latestContext?.context && (
              <div className="flex flex-col gap-3">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Active Context</h3>
                
                <ContextPill 
                  icon={Navigation} 
                  label="Destination" 
                  value={latestContext.context.destination || (latestContext.context.active_journey ? 'In Progress' : 'No Active Journey')} 
                />
                <ContextPill 
                  icon={ShieldCheck} 
                  label="Safety Score" 
                  value={
                    latestContext.context.safety_score != null 
                      ? `${latestContext.context.safety_score}%` 
                      : latestContext.context.active_journey 
                        ? 'Unavailable' 
                        : 'No Active Route'
                  } 
                  color={latestContext.context.safety_score != null ? 'text-success' : 'text-muted-foreground'} 
                />
                <ContextPill 
                  icon={CloudRain} 
                  label="Weather" 
                  value={latestContext.context.weather || (latestContext.context.active_journey ? 'Not Monitored' : '--')} 
                />
                <ContextPill 
                  icon={Clock} 
                  label="ETA" 
                  value={latestContext.context.eta || '--'} 
                />

                {/* Synthetic Environmental Proxy Disclosure */}
                {latestContext.context.safety_score != null && (
                  <div className="p-2.5 rounded-xl bg-secondary/30 border border-border/40 text-[10px] text-muted-foreground leading-relaxed mt-1">
                    <span className="font-semibold text-foreground">Proxy Disclosure:</span> Route score reflects synthetic environmental proxy indicators (infrastructure & service proximity). Does not guarantee personal safety.
                  </div>
                )}
                
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

      {/* Center Panel: Chat Interface */}
      <main className={`relative flex h-full flex-col bg-background/95 border-r border-border/50 shadow-[4px_0_24px_rgba(0,0,0,0.02)] transition-all ${
        isInspectorOpen ? "lg:col-span-6" : "lg:col-span-9"
      }`}>
        
        {/* Chat Header Bar */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-border/60 bg-card/60 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-foreground font-[family-name:var(--font-jakarta)]">
              NavSakhi Intelligence Coordinator
            </span>
            <span className="text-[10px] text-muted-foreground hidden sm:inline">&bull; Active Telemetry</span>
          </div>
          <Button
            type="button"
            variant={isInspectorOpen ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setIsInspectorOpen(!isInspectorOpen)}
            className="h-8 px-2.5 sm:px-3 text-xs font-semibold text-muted-foreground hover:text-foreground gap-1.5 rounded-xl border border-border/60 transition-colors"
            title={isInspectorOpen ? "Hide reasoning inspector panel" : "Show reasoning inspector panel"}
            aria-expanded={isInspectorOpen}
            aria-controls="assistant-inspector-panel"
          >
            <Cpu size={14} className={isInspectorOpen ? "text-primary" : "text-muted-foreground"} />
            <span className="hidden sm:inline">{isInspectorOpen ? "Hide Inspector" : "Show Inspector"}</span>
            <span className="sm:hidden">{isInspectorOpen ? "Close Details" : "Inspector"}</span>
          </Button>
        </div>

        {/* Chat History / Centered Empty State */}
        <ScrollArea className="flex-1 p-4 sm:p-6">
          <div className="flex flex-col gap-6 pb-48 sm:pb-36">
            {!hasUserMessages ? (
              <div className="flex flex-col items-center justify-center min-h-[50vh] max-w-xl mx-auto text-center px-4 py-8">
                {/* Assistant Welcome Badge */}
                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-4 shadow-xs">
                  <Bot size={32} />
                </div>
                
                <h2 className="text-xl sm:text-2xl font-bold text-foreground font-[family-name:var(--font-jakarta)] tracking-tight">
                  NavSakhi Intelligence Assistant
                </h2>
                
                <p className="text-xs sm:text-sm text-muted-foreground mt-2 mb-6 max-w-md leading-relaxed">
                  Your safety copilot for transit planning, real-time environmental context, and verified emergency guidance. How can I help you today?
                </p>

                {/* 3 Genuine Interactive Capabilities */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left">
                  <button
                    type="button"
                    onClick={() => handleSuggestion("Plan a safe route with well-lit transit options")}
                    className="p-3.5 rounded-2xl border border-border/70 bg-card/70 hover:bg-primary/5 hover:border-primary/40 transition-all group flex flex-col justify-between text-left shadow-xs cursor-pointer"
                  >
                    <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-2.5 group-hover:scale-105 transition-transform">
                      <Navigation size={16} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                        Safe Route Planning
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                        Find transit routes prioritizing well-lit, active corridors.
                      </div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSuggestion("How does NavSakhi calculate route safety scores?")}
                    className="p-3.5 rounded-2xl border border-border/70 bg-card/70 hover:bg-primary/5 hover:border-primary/40 transition-all group flex flex-col justify-between text-left shadow-xs cursor-pointer"
                  >
                    <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-2.5 group-hover:scale-105 transition-transform">
                      <ShieldCheck size={16} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                        Safety Score Proxies
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                        Understand lighting, transit access, and risk indicators.
                      </div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleSuggestion("What emergency helplines and SOS features are available?")}
                    className="p-3.5 rounded-2xl border border-border/70 bg-card/70 hover:bg-primary/5 hover:border-primary/40 transition-all group flex flex-col justify-between text-left shadow-xs cursor-pointer"
                  >
                    <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-2.5 group-hover:scale-105 transition-transform">
                      <AlertTriangle size={16} />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                        Emergency Support
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                        Access Women Helpline 1091, 112 SOS, and safe havens.
                      </div>
                    </div>
                  </button>
                </div>

                {/* Subtle initial greeting below if assistant sent one */}
                {messages.length > 0 && messages[0].role === "assistant" && (
                  <div className="mt-6 p-3 rounded-xl bg-secondary/30 border border-border/50 text-[11px] text-muted-foreground max-w-md">
                    <span className="font-semibold text-foreground">Initial Greeting: </span>
                    {messages[0].content}
                  </div>
                )}
              </div>
            ) : (
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

                      <div className="flex items-center gap-2 mt-1.5 px-1">
                        <span className="text-[10px] font-bold text-muted-foreground">{formatMessageTime(msg.timestamp)}</span>

                        {/* Read Aloud Button for Assistant Messages */}
                        {msg.role === "assistant" && voice.isSynthesisSupported && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => voice.speakMessage(msg.id, msg.content)}
                            aria-label={voice.speakingMessageId === msg.id ? "Stop reading message aloud" : "Read message aloud"}
                            className="h-6 px-2 text-[10px] font-bold text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 rounded-full"
                          >
                            {voice.speakingMessageId === msg.id ? (
                              <>
                                <Square size={10} className="text-primary fill-primary animate-pulse" />
                                <span className="text-primary">Stop</span>
                              </>
                            ) : (
                              <>
                                <Volume2 size={11} className="text-muted-foreground" />
                                <span>Read aloud</span>
                              </>
                            )}
                          </Button>
                        )}
                      </div>
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
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="absolute bottom-16 md:bottom-0 left-0 right-0 glass-card border-t border-border/50 bg-card/85 backdrop-blur-xl p-3 sm:p-4 space-y-2.5 z-30">
          
          {/* Active Listening Floating Bar */}
          {isListening && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              className="p-3 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-between gap-3 shadow-lg"
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <span className="relative flex h-3 w-3 shrink-0">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-bold text-primary flex items-center gap-1.5">
                    <span>Listening ({voice.selectedLanguage})...</span>
                  </div>
                  <p className="text-xs text-foreground font-medium truncate">
                    {voice.interimTranscript || "Speak now... words will appear here."}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={voice.cancelListening}
                  className="h-8 px-2.5 text-xs text-muted-foreground hover:text-destructive gap-1 rounded-xl"
                  aria-label="Discard spoken audio transcription"
                >
                  <X size={13} />
                  <span>Cancel</span>
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={voice.stopListening}
                  className="h-8 px-3 text-xs bg-primary text-primary-foreground hover:bg-primary/90 gap-1 rounded-xl font-bold"
                  aria-label="Finish voice input"
                >
                  <Check size={13} />
                  <span>Done</span>
                </Button>
              </div>
            </motion.div>
          )}

          {/* Safety Notice Banner */}
          {voice.safetyNotice && (
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <AlertCircle size={14} className="text-amber-600 shrink-0" />
                <span className="text-[11px] leading-tight font-medium">{voice.safetyNotice}</span>
              </div>
              <button
                type="button"
                onClick={voice.clearSafetyNotice}
                className="text-muted-foreground hover:text-foreground text-xs p-1"
                aria-label="Dismiss safety notice"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* Error Banner */}
          {voice.error && (
            <div className="p-2.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <AlertTriangle size={14} className="shrink-0" />
                <span className="text-[11px] leading-tight font-medium">{voice.error}</span>
              </div>
              <button
                type="button"
                onClick={voice.clearError}
                className="text-muted-foreground hover:text-foreground text-xs p-1"
                aria-label="Dismiss error notice"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* Integrated AIChatInput Component */}
          <AIChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSend}
            isTyping={isTyping}
            isListening={isListening}
            onVoiceToggle={isListening ? voice.stopListening : voice.startListening}
            isVoiceSupported={voice.recognitionState !== "unsupported"}
            quickSuggestions={hasUserMessages ? (latestContext?.quick_suggestions || []) : []}
            onSelectSuggestion={handleSuggestion}
          />
        </div>
      </main>

      {/* Mobile Drawer Backdrop */}
      {isInspectorOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs lg:hidden transition-opacity"
          onClick={() => setIsInspectorOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Right Panel: Reasoning & Memory (~25%) */}
      {isInspectorOpen && (
        <aside 
          id="assistant-inspector-panel"
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[75vh] flex-col rounded-t-3xl border-t border-border bg-card/98 shadow-2xl backdrop-blur-2xl lg:static lg:inset-auto lg:z-20 lg:max-h-none lg:h-full lg:col-span-3 lg:rounded-none lg:border-t-0 lg:border-l lg:border-border/60 lg:bg-card/40 lg:shadow-none animate-in slide-in-from-bottom duration-200"
          role="region"
          aria-label="Reasoning Inspector"
        >
          <div className="flex lg:hidden items-center justify-between px-4 py-3 border-b border-border/50 bg-secondary/30 shrink-0">
            <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <Cpu size={14} className="text-primary" /> Reasoning Inspector
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsInspectorOpen(false)}
              className="h-8 w-8 p-0 rounded-lg text-muted-foreground hover:text-foreground"
              aria-label="Close inspector"
            >
              <X size={16} />
            </Button>
          </div>
          <ScrollArea className="flex-1 p-4 lg:p-6 pb-20 lg:pb-6">
            <div className="flex flex-col gap-6">
              
              <div className="hidden lg:flex items-center gap-2 mb-2">
                <Cpu size={16} className="text-muted-foreground" />
                <h3 className="font-[family-name:var(--font-jakarta)] text-sm font-bold uppercase tracking-wider text-muted-foreground">Inspector</h3>
              </div>

            {/* Confidence Gauge */}
            {latestContext?.reasoning && (
              latestContext.reasoning.confidence != null ? (
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
              ) : (
                <div className="glass-card flex flex-col gap-2 rounded-2xl p-4 border-border/50">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Model Confidence</span>
                    <span className="text-[10px] font-semibold text-muted-foreground px-2 py-0.5 rounded-full bg-secondary">Uncalibrated</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground/80 leading-relaxed">
                    No empirical uncertainty calibration is active. NavSakhi does not display unverified confidence percentages.
                  </p>
                </div>
              )
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
                 {latestContext.memory.pinned_info.length > 0 ? (
                   <div className="flex flex-col gap-2">
                     {latestContext.memory.pinned_info.map((info, i) => (
                       <div key={i} className="bg-background/50 border border-border/50 rounded-lg p-3 text-xs font-medium text-foreground">
                         {info}
                       </div>
                     ))}
                   </div>
                 ) : (
                   <p className="text-[11px] text-muted-foreground/70 italic px-1">
                     No pinned preferences or notes stored.
                   </p>
                 )}
               </div>
            )}

          </div>
        </ScrollArea>
      </aside>
      )}

    </div>
  );
}

// ---------------------------------------------------------
// Sub-components
// ---------------------------------------------------------

function ContextPill({ 
  icon: Icon, 
  label, 
  value, 
  color 
}: { 
  icon: React.ComponentType<{ size?: number; className?: string }>; 
  label: string; 
  value: string; 
  color?: string;
}) {
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
