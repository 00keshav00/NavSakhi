"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ThemeToggleProps {
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function ThemeToggle({ className = "", size = "md" }: ThemeToggleProps) {
  const [mounted, setMounted] = useState(false);
  const { theme, resolvedTheme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`w-9 h-9 rounded-full bg-secondary/30 border border-border/40 shrink-0 ${className}`}
        aria-hidden="true"
      />
    );
  }

  const currentTheme = resolvedTheme || theme || "light";
  const nextTheme = currentTheme === "dark" ? "light" : "dark";

  const iconSize = size === "sm" ? 15 : size === "lg" ? 20 : 17;

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      className={`relative flex items-center justify-center p-2 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary/70 border border-border/50 hover:border-border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary shrink-0 cursor-pointer ${className}`}
      title={`Switch to ${nextTheme === "dark" ? "Dark" : "Light"} Mode`}
      aria-label={`Switch to ${nextTheme === "dark" ? "Dark" : "Light"} Mode`}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={currentTheme}
          initial={{ rotate: -90, scale: 0.6, opacity: 0 }}
          animate={{ rotate: 0, scale: 1, opacity: 1 }}
          exit={{ rotate: 90, scale: 0.6, opacity: 0 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center justify-center"
        >
          {currentTheme === "dark" ? (
            <Sun size={iconSize} className="text-amber-400" />
          ) : (
            <Moon size={iconSize} className="text-foreground/85" />
          )}
        </motion.div>
      </AnimatePresence>
    </button>
  );
}
