"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Bot, Send, Mic, Activity, CloudRain, ShieldCheck, 
  AlertTriangle, Navigation, Clock, Network, Cpu, Database,
  Volume2, Square, Check, X, Globe, AlertCircle, Sparkles,
  ChevronDown
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
import { MarkdownMessage } from "@/components/assistant/MarkdownMessage";

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
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  
  const viewportRef = useRef<HTMLDivElement>(null);

  const hasUserMessages = messages.some((m) => m.role === "user");

  // Initialize responsive sidebar state based on viewport width
  useEffect(() => {
    if (typeof window !== "undefined") {
      const isDesktop = window.innerWidth >= 1024;
      setIsLeftSidebarOpen(isDesktop);
      setIsInspectorOpen(isDesktop);
    }
  }, []);

  // Handle Escape key to close open mobile/tablet drawers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (typeof window !== "undefined" && window.innerWidth < 1024) {
          setIsLeftSidebarOpen(false);
          setIsInspectorOpen(false);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
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

  // Viewport-scoped scroll handler to detect reading position
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const scrolledUp = distanceFromBottom > 120;
    setIsUserScrolledUp(scrolledUp);
    setShowScrollBottom(scrolledUp);
  };

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    if (viewportRef.current) {
      viewportRef.current.scrollTo({
        top: viewportRef.current.scrollHeight,
        behavior,
      });
      setIsUserScrolledUp(false);
      setShowScrollBottom(false);
    }
  };

  // Auto scroll to bottom only when user is not actively reading past messages
  useEffect(() => {
    if (!isUserScrolledUp) {
      scrollToBottom("smooth");
    }
  }, [messages, isTyping]);

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim() && !isTyping) {
      if (voice.recognitionState === "listening") {
        voice.stopListening();
      }
      sendMessage(inputValue);
      setInputValue("");
      setIsUserScrolledUp(false);
      setShowScrollBottom(false);
      setTimeout(() => scrollToBottom("smooth"), 50);
    }
  };

  const handleSuggestion = (query: string) => {
    if (!isTyping) {
      sendMessage(query);
      setIsUserScrolledUp(false);
      setShowScrollBottom(false);
      setTimeout(() => scrollToBottom("smooth"), 50);
    }
  };

  const isListening = voice.recognitionState === "listening";

  return (
    <div className="relative flex h-full w-full overflow-hidden bg-background">
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

      {/* Mobile Drawer Backdrop */}
      {(isLeftSidebarOpen || isInspectorOpen) && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs lg:hidden transition-opacity"
          onClick={() => {
            setIsLeftSidebarOpen(false);
            setIsInspectorOpen(false);
          }}
          aria-hidden="true"
        />
      )}
      
      {/* Left Panel: Intelligence Coordinator */}
      <aside 
        id="assistant-coordinator-panel"
        className={`
          ${isLeftSidebarOpen ? "flex" : "hidden"}
          fixed lg:static inset-y-0 left-0 z-50 lg:z-10
          w-72 sm:w-80 lg:w-72 xl:w-80 shrink-0 h-full flex-col
          border-r border-border bg-card/95 lg:bg-card/60 backdrop-blur-3xl
          shadow-2xl lg:shadow-[4px_0_24px_rgba(0,0,0,0.02)]
          transition-all duration-200
        `}
        role="region"
        aria-label="Intelligence Coordinator"
      >
        {/* Mobile Header with close button */}
        <div className="flex lg:hidden items-center justify-between px-4 py-3 border-b border-border/50 bg-secondary/30 shrink-0">
          <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
            <Bot size={16} className="text-primary" /> Intelligence Coordinator
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsLeftSidebarOpen(false)}
            className="h-8 w-8 p-0 rounded-lg text-muted-foreground hover:text-foreground"
            aria-label="Close intelligence panel"
          >
            <X size={16} />
          </Button>
        </div>

        <ScrollArea className="flex-1 min-h-0 p-4 sm:p-6">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border/50">
            <div className="bg-primary/20 p-2 rounded-xl text-primary shrink-0">
              <Bot size={26} className={latestContext?.agent_status.status === 'Analyzing' ? 'animate-pulse' : ''} />
            </div>
            <div className="flex flex-col">
              <h2 className="font-[family-name:var(--font-jakarta)] text-base font-extrabold text-foreground leading-none">Intelligence</h2>
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary mt-1">Coordinator</span>
            </div>
          </div>

          <div className="flex flex-col gap-5">
            
            {/* System & Voice Status */}
            <div className="flex flex-col gap-2">
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">System Status</h3>
              <div className="glass-card flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                <span className="text-xs font-semibold">{latestContext?.agent_status.status || 'Initializing...'}</span>
                {isTyping && <Activity size={14} className="text-primary animate-pulse" />}
              </div>
            </div>

            {/* Voice Preferences Controls */}
            <div className="flex flex-col gap-2.5 p-3 rounded-xl border border-border/60 bg-secondary/20">
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
              <div className="flex flex-col gap-2.5">
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
               <div className="flex flex-col gap-2.5 mt-2">
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
      <main className="relative flex flex-1 flex-col h-full min-h-0 min-w-0 bg-background/95 border-r border-border/50 shadow-[4px_0_24px_rgba(0,0,0,0.02)] transition-all overflow-hidden">
        
        {/* Chat Header Bar (shrink-0) */}
        <div className="flex items-center justify-between px-3 sm:px-6 py-2.5 sm:py-3 border-b border-border/60 bg-card/60 backdrop-blur-md shrink-0 z-10">
          <div className="flex items-center gap-2">
            {/* Toggle Coordinator Button */}
            <Button
              type="button"
              variant={isLeftSidebarOpen ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setIsLeftSidebarOpen(!isLeftSidebarOpen)}
              className="h-8 px-2.5 text-xs font-semibold text-muted-foreground hover:text-foreground gap-1.5 rounded-xl border border-border/60 transition-colors"
              title={isLeftSidebarOpen ? "Hide Intelligence Coordinator" : "Show Intelligence Coordinator"}
              aria-expanded={isLeftSidebarOpen}
              aria-controls="assistant-coordinator-panel"
            >
              <Bot size={14} className={isLeftSidebarOpen ? "text-primary" : "text-muted-foreground"} />
              <span className="hidden sm:inline">Coordinator</span>
            </Button>

            <div className="h-4 w-px bg-border/60 mx-0.5 hidden sm:block" />

            <div className="flex items-center gap-2 min-w-0">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <span className="text-xs font-bold text-foreground font-[family-name:var(--font-jakarta)] truncate">
                NavSakhi Travel Companion
              </span>
              <span className="text-[10px] text-muted-foreground hidden md:inline shrink-0">&bull; Active Telemetry</span>
            </div>
          </div>

          {/* Toggle Inspector Button */}
          <Button
            type="button"
            variant={isInspectorOpen ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setIsInspectorOpen(!isInspectorOpen)}
            className="h-8 px-2.5 sm:px-3 text-xs font-semibold text-muted-foreground hover:text-foreground gap-1.5 rounded-xl border border-border/60 transition-colors"
            title={isInspectorOpen ? "Hide reasoning inspector" : "Show reasoning inspector"}
            aria-expanded={isInspectorOpen}
            aria-controls="assistant-inspector-panel"
          >
            <Cpu size={14} className={isInspectorOpen ? "text-primary" : "text-muted-foreground"} />
            <span className="hidden sm:inline">{isInspectorOpen ? "Hide Inspector" : "Show Inspector"}</span>
            <span className="sm:hidden">{isInspectorOpen ? "Close Details" : "Inspector"}</span>
          </Button>
        </div>

        {/* Scrollable Message History Area (flex-1 min-h-0) */}
        <div className="relative flex-1 min-h-0 w-full overflow-hidden">
          <ScrollArea 
            viewportRef={viewportRef}
            onScroll={handleScroll}
            className="h-full w-full"
          >
            <div className="p-4 sm:p-6 flex flex-col gap-6 max-w-4xl mx-auto w-full">
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
                          <MarkdownMessage content={msg.content} isUser={msg.role === 'user'} />
                        </div>

                        <div className="flex items-center gap-2 mt-1.5 px-1">
                          <span className="text-[10px] font-bold text-muted-foreground">{formatMessageTime(msg.timestamp)}</span>

                          {/* Provenance Badge for Assistant Messages */}
                          {msg.role === "assistant" && msg.response_source && (
                            msg.response_source === "gemini" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-[9.5px] font-semibold text-indigo-400">
                                <Sparkles size={10} className="text-indigo-400" />
                                Gemini AI
                              </span>
                            ) : msg.response_source === "fallback" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[9.5px] font-semibold text-amber-500">
                                <ShieldCheck size={10} className="text-amber-500" />
                                NavSakhi fallback
                              </span>
                            ) : msg.response_source === "rule_based" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-secondary border border-border text-[9.5px] font-semibold text-muted-foreground">
                                <Bot size={10} className="text-muted-foreground" />
                                Rule-based response
                              </span>
                            ) : null
                          )}

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
            </div>
          </ScrollArea>

          {/* Floating "Scroll to latest" button */}
          <AnimatePresence>
            {showScrollBottom && (
              <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                type="button"
                onClick={() => scrollToBottom("smooth")}
                className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 px-3.5 py-1.5 rounded-full bg-primary text-primary-foreground text-xs font-bold shadow-lg hover:bg-primary/90 transition-all flex items-center gap-1.5 cursor-pointer"
                aria-label="Scroll to newest messages"
              >
                <span>New messages</span>
                <ChevronDown size={14} />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        {/* Input Area (shrink-0, permanently docked at bottom of center column) */}
        <div className="shrink-0 border-t border-border/50 bg-card/85 backdrop-blur-xl p-3 sm:p-4 space-y-2.5 z-20">
          
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

      {/* Right Panel: Reasoning & Memory */}
      <aside 
        id="assistant-inspector-panel"
        className={`
          ${isInspectorOpen ? "flex" : "hidden"}
          fixed lg:static inset-y-0 right-0 z-50 lg:z-10
          w-72 sm:w-80 lg:w-72 xl:w-80 shrink-0 h-full flex-col
          border-l border-border/60 bg-card/98 lg:bg-card/40 backdrop-blur-2xl
          shadow-2xl lg:shadow-none
          transition-all duration-200
        `}
        role="region"
        aria-label="Reasoning Inspector"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50 bg-secondary/30 shrink-0">
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
        <ScrollArea className="flex-1 min-h-0 p-4 lg:p-6 pb-20 lg:pb-6">
          <div className="flex flex-col gap-5">
            
            <div className="hidden lg:flex items-center gap-2 mb-1">
              <Cpu size={15} className="text-muted-foreground" />
              <h3 className="font-[family-name:var(--font-jakarta)] text-xs font-bold uppercase tracking-wider text-muted-foreground">Inspector</h3>
            </div>

            {/* Confidence Gauge */}
            {latestContext?.reasoning && (
              latestContext.reasoning.confidence != null ? (
                <div className="glass-card flex flex-col gap-3 rounded-2xl p-4 border-border/50">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Confidence</span>
                    <span className={`text-lg font-black ${
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
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Model Confidence</span>
                    <span className="text-[9px] font-semibold text-muted-foreground px-2 py-0.5 rounded-full bg-secondary">Uncalibrated</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground/80 leading-relaxed">
                    No empirical uncertainty calibration is active. NavSakhi does not display unverified confidence percentages.
                  </p>
                </div>
              )
            )}

            {/* Reasoning Trace */}
            {latestContext?.reasoning && (
               <div className="glass-card flex flex-col gap-3.5 rounded-2xl p-4 border-border/50 bg-secondary/10">
                 <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                   <Network size={13} className="text-primary"/> Logic Trace
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
               <div className="flex flex-col gap-2.5 mt-2">
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
    <div className="glass-card flex items-center gap-3 rounded-xl p-2.5 border-border/50 bg-background/50">
      <div className={`p-1.5 rounded-lg bg-secondary/50 ${color || 'text-muted-foreground'}`}>
        <Icon size={15} />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold text-foreground truncate">{value}</span>
      </div>
    </div>
  );
}
