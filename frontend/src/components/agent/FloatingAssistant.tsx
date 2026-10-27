"use client";

import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Bot, X, Send, Sparkles, AlertTriangle, ShieldCheck, Navigation, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAssistant } from "@/hooks/useAssistant";
import { MarkdownMessage } from "@/components/assistant/MarkdownMessage";

export function FloatingAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const pathname = usePathname();
  const viewportRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wasFocusedRef = useRef(false);
  const { messages, isTyping, sendMessage, latestContext } = useAssistant();

  // Viewport-scoped scroll handler to protect reading position
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const scrolledUp = distanceFromBottom > 90;
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

  // Internal container auto-scroll: only triggers if user is near bottom
  useEffect(() => {
    if (isOpen && !isUserScrolledUp) {
      scrollToBottom("smooth");
    }
  }, [messages, isTyping, isOpen]);

  // When assistant opens, scroll to bottom and focus input
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => scrollToBottom("auto"), 50);
      setTimeout(() => {
        inputRef.current?.focus();
        wasFocusedRef.current = true;
      }, 100);
    }
  }, [isOpen]);

  // Restore focus to input once typing/streaming completes unless user explicitly moved elsewhere
  useEffect(() => {
    if (!isTyping && isOpen && wasFocusedRef.current) {
      const activeEl = document.activeElement;
      const isOtherInteractive =
        activeEl &&
        activeEl !== document.body &&
        activeEl !== inputRef.current &&
        (activeEl.tagName === "BUTTON" ||
          activeEl.tagName === "A" ||
          activeEl.getAttribute("role") === "button");
      if (!isOtherInteractive) {
        inputRef.current?.focus();
      }
    }
  }, [isTyping, isOpen]);

  // Handle Escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Do not show floating assistant on the dedicated assistant page
  if (pathname === "/assistant") {
    return null;
  }

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed && !isTyping) {
      wasFocusedRef.current = true;
      sendMessage(trimmed);
      setInputValue("");
      setIsUserScrolledUp(false);
      setShowScrollBottom(false);
      setTimeout(() => scrollToBottom("smooth"), 50);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  };

  const handleSuggestion = (prompt: string) => {
    if (!isTyping) {
      sendMessage(prompt);
      setIsUserScrolledUp(false);
      setShowScrollBottom(false);
      setTimeout(() => scrollToBottom("smooth"), 50);
    }
  };

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom,0px))] md:bottom-6 right-4 sm:right-6 z-40"
          >
            <button
              type="button"
              onClick={() => setIsOpen(true)}
              className="group relative flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-primary to-indigo-600 text-white shadow-2xl shadow-primary/40 transition-all hover:scale-110 active:scale-95 border-2 border-white/20 focus:outline-none focus:ring-4 focus:ring-primary/40 cursor-pointer"
              title="Open NavSakhi AI Companion"
              aria-label="Open AI Assistant"
            >
              <Bot size={28} className="transition-transform group-hover:rotate-12" />
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-background bg-emerald-500 text-[10px] font-extrabold text-white shadow-sm">
                AI
              </span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.95 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom,0px))] md:bottom-6 right-3 sm:right-6 z-50 flex h-[520px] max-h-[calc(100vh-6.5rem-env(safe-area-inset-bottom,0px))] w-[360px] sm:w-[390px] max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-3xl bg-slate-950/98 border border-slate-800 shadow-2xl backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-900/60 p-3.5 sm:p-4 backdrop-blur-md shrink-0">
              <div className="flex items-center gap-3">
                <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-indigo-600 text-white shadow-inner">
                  <Bot size={18} />
                  <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900 bg-emerald-500" />
                </div>
                <div className="flex flex-col">
                  <span className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
                    NavSakhi Companion
                  </span>
                  <span className="flex items-center gap-1 text-[11px] font-medium text-primary">
                    <Sparkles size={10} />
                    {latestContext?.agent_status.status || "Active Assistant"}
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                onClick={() => setIsOpen(false)}
                title="Close assistant"
                aria-label="Close assistant"
              >
                <X size={16} />
              </Button>
            </div>

            {/* Conversation Messages with Container-Scoped Independent Scrolling */}
            <div className="flex-1 min-h-0 relative flex flex-col bg-slate-950/40">
              <ScrollArea 
                viewportRef={viewportRef}
                onScroll={handleScroll}
                className="flex-1 min-h-0 h-full p-3.5 sm:p-4"
              >
                <div className="flex flex-col gap-3">
                  {/* Default greeting if messages are empty */}
                  {messages.length === 0 ? (
                    <div className="space-y-3">
                      <div className="rounded-2xl rounded-tl-sm border border-slate-800 bg-slate-900/80 p-3.5 text-xs text-slate-200 shadow-sm leading-relaxed">
                        Hello! I am your NavSakhi travel companion. You can ask me about safe route options, emergency resources, or discuss any travel anxiety. How can I support you right now?
                      </div>

                      {/* Quick suggestion pills */}
                      <div className="flex flex-col gap-1.5 pt-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
                          Quick Inquiries
                        </span>
                        <button
                          type="button"
                          onClick={() => handleSuggestion("I am feeling unsafe. I have to travel alone.")}
                          className="text-left text-xs p-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 font-semibold transition-colors flex items-center gap-2 cursor-pointer"
                        >
                          <AlertTriangle size={13} className="text-rose-400 shrink-0" />
                          <span>I am feeling unsafe / travel anxiety</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSuggestion("How does NavSakhi calculate route safety scores?")}
                          className="text-left text-xs p-2.5 rounded-xl border border-slate-800 bg-slate-900/70 hover:bg-slate-800 text-slate-300 transition-colors flex items-center gap-2 cursor-pointer"
                        >
                          <ShieldCheck size={13} className="text-primary shrink-0" />
                          <span>Explain environmental safety scores</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSuggestion("What emergency contacts and SOS options are available?")}
                          className="text-left text-xs p-2.5 rounded-xl border border-slate-800 bg-slate-900/70 hover:bg-slate-800 text-slate-300 transition-colors flex items-center gap-2 cursor-pointer"
                        >
                          <Navigation size={13} className="text-cyan-400 shrink-0" />
                          <span>Emergency helplines (112, 1091)</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex flex-col w-full ${msg.role === "user" ? "items-end" : "items-start"}`}
                      >
                        <div
                          className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-sm shadow-md"
                              : "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-sm shadow-sm"
                          }`}
                        >
                          <MarkdownMessage content={msg.content} isUser={msg.role === "user"} />
                        </div>
                        {msg.role === "assistant" && msg.response_source && (
                          <div className="mt-1 px-1 flex items-center gap-1.5">
                            {msg.response_source === "gemini" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-[9px] font-semibold text-indigo-400">
                                <Sparkles size={9} className="text-indigo-400" />
                                Gemini AI
                              </span>
                            ) : msg.response_source === "fallback" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[9px] font-semibold text-amber-500">
                                <ShieldCheck size={9} className="text-amber-500" />
                                NavSakhi fallback
                              </span>
                            ) : msg.response_source === "rule_based" ? (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-[9px] font-semibold text-slate-300">
                                <Bot size={9} className="text-slate-400" />
                                Rule-based response
                              </span>
                            ) : null}
                          </div>
                        )}
                      </div>
                    ))
                  )}

                  {/* Typing Indicator */}
                  {isTyping && (
                    <div className="flex w-full justify-start">
                      <div className="rounded-2xl rounded-tl-sm bg-slate-900/80 border border-slate-800 px-4 py-3 flex items-center gap-1.5 shadow-sm">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              {/* Scroll to bottom button when user has scrolled up */}
              <AnimatePresence>
                {showScrollBottom && (
                  <motion.button
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    type="button"
                    onClick={() => scrollToBottom("smooth")}
                    className="absolute bottom-2 right-4 z-10 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary text-primary-foreground text-xs font-semibold shadow-lg hover:bg-primary/90 transition-all cursor-pointer"
                  >
                    <span>Latest</span>
                    <ChevronDown size={14} />
                  </motion.button>
                )}
              </AnimatePresence>
            </div>

            {/* Input Bar (Permanently docked at the bottom of the assistant card) */}
            <form onSubmit={handleSend} className="border-t border-slate-800/80 bg-slate-900/70 p-3 backdrop-blur-md shrink-0">
              <div className="relative flex items-center">
                <Input
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onFocus={() => {
                    wasFocusedRef.current = true;
                  }}
                  onBlur={(e) => {
                    if (e.relatedTarget && (e.relatedTarget as HTMLElement).tagName === "BUTTON") {
                      wasFocusedRef.current = false;
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Ask your travel companion..."
                  disabled={isTyping}
                  className="h-10 rounded-full border-slate-700 bg-slate-950/80 pr-12 text-xs placeholder:text-slate-500 focus-visible:ring-1 focus-visible:ring-primary text-white"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={!inputValue.trim() || isTyping}
                  className="absolute right-1 h-8 w-8 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-all cursor-pointer"
                  title="Send message"
                  aria-label="Send message"
                >
                  <Send size={14} />
                </Button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}