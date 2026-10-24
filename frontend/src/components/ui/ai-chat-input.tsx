"use client";

import React, { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Mic, Square, X, Sparkles, CornerDownLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface AIChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isTyping?: boolean;
  isListening?: boolean;
  onVoiceToggle?: () => void;
  isVoiceSupported?: boolean;
  placeholder?: string;
  quickSuggestions?: string[];
  onSelectSuggestion?: (query: string) => void;
  className?: string;
}

export function AIChatInput({
  value,
  onChange,
  onSubmit,
  isTyping = false,
  isListening = false,
  onVoiceToggle,
  isVoiceSupported = true,
  placeholder,
  quickSuggestions = [],
  onSelectSuggestion,
  className,
}: AIChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isTyping) {
        onSubmit();
      }
    }
  };

  // Auto-resize textarea height based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  }, [value]);

  const defaultPlaceholder = isListening
    ? "Listening... speak now..."
    : isTyping
    ? "Intelligence Coordinator is processing..."
    : "Ask about safe corridors, transit schedules, or station safety...";

  return (
    <div className={cn("w-full space-y-3", className)}>
      {/* Quick Suggestion Pills */}
      {quickSuggestions.length > 0 && (
        <div className="flex flex-wrap sm:flex-nowrap gap-1.5 sm:gap-2 sm:overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden pb-1">
          {quickSuggestions.map((suggestion, index) => (
            <motion.button
              key={`${suggestion}-${index}`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="button"
              onClick={() => onSelectSuggestion?.(suggestion)}
              disabled={isTyping}
              className="shrink-0 text-xs font-semibold px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary hover:bg-primary hover:text-white transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-2xs"
            >
              <Sparkles size={11} className="text-primary group-hover:text-white" />
              <span>{suggestion}</span>
            </motion.button>
          ))}
        </div>
      )}

      {/* Main Composer Box */}
      <div className="relative rounded-2xl sm:rounded-3xl border border-border/80 bg-card/80 backdrop-blur-xl shadow-lg transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 p-2 sm:p-2.5">
        <div className="flex items-end gap-2">
          {/* Voice Input Button */}
          {onVoiceToggle && isVoiceSupported && (
            <Button
              type="button"
              variant={isListening ? "default" : "ghost"}
              size="icon"
              onClick={onVoiceToggle}
              disabled={isTyping}
              title={isListening ? "Stop listening" : "Start voice input"}
              aria-label={isListening ? "Stop voice input" : "Start voice input"}
              className={cn(
                "h-10 w-10 shrink-0 rounded-xl sm:rounded-2xl transition-all",
                isListening
                  ? "bg-primary text-primary-foreground shadow-md ring-2 ring-primary/40 animate-pulse"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              {isListening ? (
                <Square size={16} className="fill-current animate-pulse" />
              ) : (
                <Mic size={18} />
              )}
            </Button>
          )}

          {/* Text Input Area */}
          <div className="relative flex-1 py-1">
            <textarea
              ref={textareaRef}
              rows={1}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isTyping}
              placeholder={placeholder || defaultPlaceholder}
              className="w-full resize-none bg-transparent px-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-hidden disabled:opacity-60 max-h-36 leading-relaxed font-medium"
            />
          </div>

          {/* Clear Button (if value exists) */}
          {value.trim() && !isTyping && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => onChange("")}
              className="h-8 w-8 shrink-0 rounded-full text-muted-foreground hover:text-foreground"
              title="Clear input"
              aria-label="Clear text input"
            >
              <X size={15} />
            </Button>
          )}

          {/* Submit Button */}
          <Button
            type="button"
            onClick={onSubmit}
            disabled={!value.trim() || isTyping}
            size="icon"
            className="h-10 w-10 shrink-0 rounded-xl sm:rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 transition-transform active:scale-95 disabled:opacity-40 disabled:scale-100"
            title="Send query (Enter)"
            aria-label="Send message"
          >
            <Send size={16} className="translate-x-[-0.5px]" />
          </Button>
        </div>

        {/* Bottom Helper Line: Keyboard Hint */}
        <div className="hidden sm:flex items-center justify-between px-3 pt-1.5 pb-0.5 border-t border-border/40 text-[10px] text-muted-foreground font-medium">
          <span>Press <kbd className="px-1 py-0.5 rounded bg-muted text-foreground/80 font-mono text-[9px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-muted text-foreground/80 font-mono text-[9px]">Shift + Enter</kbd> for new line</span>
          <span className="flex items-center gap-1 text-primary font-bold">
            <CornerDownLeft size={10} /> Active Coordinator
          </span>
        </div>
      </div>
    </div>
  );
}
