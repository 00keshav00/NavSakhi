"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { 
  Home, Map as MapIcon, ShieldAlert, Users, MoreHorizontal,
  Bot, BookOpen, User, Settings, LogOut, Sun, Moon, X,
  ShieldCheck, HelpCircle, Sparkles, Scale, Info
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";

export function MobileNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, resolvedTheme, setTheme } = useTheme();
  const currentTheme = resolvedTheme || theme;
  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const user = useAuthStore((state) => state.user);

  const handleLogout = () => {
    setIsMoreOpen(false);
    useAuthStore.getState().logout();
    toast.info("Signed out", { description: "Session ended. Please sign in to continue." });
    router.push("/login");
  };

  return (
    <>
      {/* Fixed Bottom Navigation Bar */}
      <nav 
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-card/95 backdrop-blur-2xl border-t border-border/80 px-3 py-1.5 shadow-[0_-4px_20px_rgba(0,0,0,0.06)]"
        aria-label="Mobile Navigation"
      >
        <div className="flex items-center justify-around max-w-md mx-auto">
          
          {/* 1. Home / Dashboard */}
          <Link
            href="/home"
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-xl transition-colors ${
              pathname === "/home" ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Home size={19} />
            <span className="text-[10px] tracking-tight">Home</span>
          </Link>

          {/* 2. Journey */}
          <Link
            href="/journey"
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-xl transition-colors ${
              pathname === "/journey" ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <MapIcon size={19} />
            <span className="text-[10px] tracking-tight">Journey</span>
          </Link>

          {/* 3. Center Floating Emergency SOS */}
          <Link
            href="/emergency"
            className="flex flex-col items-center -mt-5 relative z-10 group"
            aria-label="Emergency SOS"
          >
            <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-danger to-[#FF6B8B] text-white flex items-center justify-center shadow-lg shadow-danger/30 transition-transform active:scale-95 group-hover:scale-105 border-2 border-background">
              <ShieldAlert size={22} className="animate-pulse-soft" />
            </div>
            <span className="text-[10px] font-black tracking-wider text-danger mt-0.5">SOS</span>
          </Link>

          {/* 4. Community */}
          <Link
            href="/community"
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-xl transition-colors ${
              pathname === "/community" ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Users size={19} />
            <span className="text-[10px] tracking-tight">Community</span>
          </Link>

          {/* 5. More Menu Toggle */}
          <button
            type="button"
            onClick={() => setIsMoreOpen(true)}
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-xl transition-colors ${
              isMoreOpen ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
            }`}
            aria-label="More Options Menu"
          >
            <MoreHorizontal size={19} />
            <span className="text-[10px] tracking-tight">More</span>
          </button>

        </div>
      </nav>

      {/* Slide-Up Sheet for "More" Menu */}
      {isMoreOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-xs animate-fade-in"
            onClick={() => setIsMoreOpen(false)}
          />
          <div 
            className="md:hidden fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl bg-card border-t border-border p-5 pb-8 shadow-2xl animate-slide-up space-y-4 max-w-lg mx-auto"
            role="dialog"
            aria-label="More navigation items"
          >
            <div className="flex items-center justify-between border-b border-border/50 pb-3">
              {user ? (
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-[#F6C8D7] flex items-center justify-center text-white font-bold text-xs">
                    {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-foreground truncate">{user?.full_name || "NavSakhi User"}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{user?.email || "user@example.com"}</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-muted-foreground font-bold text-xs">
                    G
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-foreground">Guest Explorer</p>
                    <p className="text-[10px] text-muted-foreground">Unauthenticated mode</p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2">
                {!user && (
                  <Link
                    href="/login"
                    onClick={() => setIsMoreOpen(false)}
                    className="px-3 py-1 rounded-full text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Sign In
                  </Link>
                )}
                <button
                  type="button"
                  onClick={() => setIsMoreOpen(false)}
                  className="p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary"
                  aria-label="Close menu"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-[50vh] overflow-y-auto pr-1">
              <Link
                href="/assistant"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <Bot size={17} className="text-primary" />
                <span>AI Assistant</span>
              </Link>

              <Link
                href="/resources"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <BookOpen size={17} className="text-rose-500" />
                <span>Resources</span>
              </Link>

              <Link
                href="/safety-guidelines"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <ShieldCheck size={17} className="text-emerald-500" />
                <span>Safety Guidelines</span>
              </Link>

              <Link
                href="/about"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <Info size={17} className="text-purple-500" />
                <span>About &amp; Pillars</span>
              </Link>

              <Link
                href="/help"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <HelpCircle size={17} className="text-indigo-500" />
                <span>Help &amp; FAQ</span>
              </Link>

              <Link
                href="/limitations"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <Sparkles size={17} className="text-amber-500" />
                <span>AI Limitations</span>
              </Link>

              <Link
                href="/privacy"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <Scale size={17} className="text-purple-500" />
                <span>Privacy Policy</span>
              </Link>

              <Link
                href="/terms"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <BookOpen size={17} className="text-blue-500" />
                <span>Terms of Use</span>
              </Link>

              <Link
                href="/accessibility"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <ShieldAlert size={17} className="text-teal-500" />
                <span>Accessibility</span>
              </Link>

              <Link
                href="/settings"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-2.5 p-3 rounded-2xl bg-secondary/40 hover:bg-secondary text-foreground text-xs font-bold transition-colors"
              >
                <Settings size={17} className="text-muted-foreground" />
                <span>Settings</span>
              </Link>
            </div>

            <div className="pt-2 border-t border-border/50 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setTheme(nextTheme)}
                className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground py-2"
                aria-label={`Switch to ${nextTheme === "dark" ? "Dark" : "Light"} Mode`}
              >
                {currentTheme === "dark" ? (
                  <>
                    <Sun size={15} className="text-amber-400" /> Light Mode
                  </>
                ) : (
                  <>
                    <Moon size={15} /> Dark Mode
                  </>
                )}
              </button>

              {user ? (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 text-xs font-bold text-danger hover:underline py-2"
                >
                  <LogOut size={15} /> Sign Out
                </button>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setIsMoreOpen(false)}
                  className="flex items-center gap-1.5 text-xs font-bold text-primary hover:underline py-2"
                >
                  Sign In to Account
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
