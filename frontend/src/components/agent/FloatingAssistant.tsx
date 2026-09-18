"use client";

import { useState } from "react";
import { Bot, X, Send, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

export function FloatingAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-8 right-8 z-50 animate-float"
          >
            <button
              onClick={() => setIsOpen(true)}
              className="group relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary to-iris text-white shadow-xl shadow-primary/30 transition-all hover:scale-110 active:scale-95"
            >
              <Bot size={30} className="transition-transform group-hover:rotate-12" />
              <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-background bg-black text-[10px] font-bold text-white shadow-sm dark:border-border">
                1
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
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-8 right-8 z-50 flex h-[550px] w-[380px] flex-col overflow-hidden rounded-3xl glass shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-border/50 bg-card/50 p-5 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-primary to-iris text-white shadow-inner">
                  <Bot size={20} />
                  <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-card bg-success"></div>
                </div>
                <div className="flex flex-col">
                  <span className="font-[family-name:var(--font-jakarta)] text-sm font-bold tracking-wide text-foreground">Agent Core</span>
                  <span className="flex items-center gap-1 text-xs font-medium text-primary">
                    <Sparkles size={10} /> Active Telemetry
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                onClick={() => setIsOpen(false)}
              >
                <X size={18} />
              </Button>
            </div>

            <ScrollArea className="flex-1 bg-background/10 p-5">
              <div className="flex flex-col gap-5">
                <motion.div 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex w-max max-w-[85%] flex-col gap-1.5"
                >
                  <div className="rounded-2xl rounded-tl-sm border border-border/50 bg-secondary/80 p-4 text-sm font-light leading-relaxed text-foreground/90 shadow-sm backdrop-blur-sm">
                    Secure connection established. I am currently monitoring environmental parameters and routing data. How can I assist you today?
                  </div>
                  <span className="ml-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">System • Just now</span>
                </motion.div>
              </div>
            </ScrollArea>

            <div className="border-t border-border/50 bg-card/50 p-4 backdrop-blur-md">
              <div className="relative flex items-center">
                <Input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Query agent..."
                  className="h-12 rounded-full border-border/50 bg-background/50 pr-14 text-sm placeholder:text-muted-foreground/50 focus-visible:ring-1 focus-visible:ring-primary"
                />
                <Button
                  size="icon"
                  className="absolute right-1.5 h-9 w-9 rounded-full bg-foreground text-background shadow-md transition-transform hover:scale-105 hover:bg-foreground/90"
                >
                  <Send size={16} />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}