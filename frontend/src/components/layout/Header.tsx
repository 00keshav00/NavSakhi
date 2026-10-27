"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { 
  Sun, Moon, ShieldAlert, User, LogOut, Settings as SettingsIcon,
  ChevronDown, Search, BookOpen, Compass, Info, ShieldCheck, AlertTriangle,
  HelpCircle, Sparkles
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const currentTheme = resolvedTheme || theme;
  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSosInfoOpen, setIsSosInfoOpen] = useState(false);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = () => {
    useAuthStore.getState().logout();
    toast.info("Signed out", { description: "Session ended. Please sign in to continue." });
    router.push("/login");
  };

  const navItems = [
    { name: "Dashboard", href: "/home" },
    { name: "Journey", href: "/journey" },
    { name: "Live Monitor", href: "/live" },
    { name: "Community", href: "/community" },
    { name: "AI Assistant", href: "/assistant" },
    { name: "Resources", href: "/resources" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full h-16 border-b border-border/80 bg-background/80 backdrop-blur-xl shrink-0 transition-colors">
      <div className="mx-auto flex h-full items-center justify-between px-4 sm:px-6 lg:px-8 max-w-7xl">
        
        {/* Left: Brand & Identity */}
        <div className="flex items-center gap-3">
          <Link href="/home" className="flex items-center gap-2.5 group">
            <div className="relative h-10 w-36 sm:w-44 flex items-center">
              <Image 
                src="/images/navsakhi/navsakhi_logo_official.png" 
                alt="NavSakhi - Safer Journeys • Stronger Women" 
                width={175} 
                height={56} 
                className="h-9 sm:h-10 w-auto object-contain transition-transform group-hover:scale-[1.02]" 
                priority 
              />
            </div>
          </Link>
        </div>

        {/* Center: Desktop Horizontal Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 bg-secondary/40 p-1 rounded-full border border-border/60">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`relative px-4 py-1.5 rounded-full text-xs font-bold transition-all duration-200 ${
                  isActive
                    ? "bg-card text-primary shadow-xs border border-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-card/50"
                }`}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Right: Actions, Theme Toggle, Profile & Emergency SOS */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          
          {/* Theme Toggle Button with Restrained Spring/Rotation */}
          {mounted && (
            <button
              type="button"
              onClick={() => setTheme(nextTheme)}
              className="relative p-2 rounded-full text-muted-foreground hover:text-foreground hover:bg-secondary border border-transparent hover:border-border transition-colors overflow-hidden"
              title={`Switch to ${nextTheme === "dark" ? "Dark" : "Light"} Mode`}
              aria-label={`Switch to ${nextTheme === "dark" ? "Dark" : "Light"} Mode`}
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={currentTheme}
                  initial={{ rotate: -90, scale: 0.6, opacity: 0 }}
                  animate={{ rotate: 0, scale: 1, opacity: 1 }}
                  exit={{ rotate: 90, scale: 0.6, opacity: 0 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] as const }}
                  className="flex items-center justify-center"
                >
                  {currentTheme === "dark" ? (
                    <Sun size={17} className="text-amber-400" />
                  ) : (
                    <Moon size={17} className="text-foreground/80" />
                  )}
                </motion.div>
              </AnimatePresence>
            </button>
          )}

          {/* User Profile or Guest Sign In */}
          {user ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsProfileOpen((prev) => !prev)}
                className="flex items-center gap-2 p-1 rounded-full hover:bg-secondary transition-colors"
                aria-label="User Profile Menu"
                aria-expanded={isProfileOpen}
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-[#F6C8D7] flex items-center justify-center text-white font-bold text-xs shadow-xs">
                  {user?.full_name ? user.full_name[0].toUpperCase() : "U"}
                </div>
                <ChevronDown size={14} className="text-muted-foreground hidden sm:block" />
              </button>

              {isProfileOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsProfileOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-card border border-border shadow-xl p-1.5 z-50 animate-fade-in divide-y divide-border/40">
                    <div className="p-2.5">
                      <p className="text-xs font-bold text-foreground truncate">
                        {user?.full_name || "NavSakhi User"}
                      </p>
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {user?.email || "user@example.com"}
                      </p>
                    </div>

                    <div className="py-1">
                      <Link
                        href="/profile"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <User size={15} className="text-primary" /> Profile Overview
                      </Link>
                      <Link
                        href="/settings"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <SettingsIcon size={15} className="text-muted-foreground" /> Settings &amp; Contacts
                      </Link>
                      <Link
                        href="/safety-guidelines"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <ShieldCheck size={15} className="text-emerald-500" /> Safety Guidelines
                      </Link>
                      <Link
                        href="/help"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <HelpCircle size={15} className="text-indigo-500" /> Help &amp; Support
                      </Link>
                      <Link
                        href="/limitations"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <Sparkles size={15} className="text-amber-500" /> AI &amp; ML Limitations
                      </Link>
                      <Link
                        href="/terms"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <BookOpen size={15} className="text-blue-500" /> Terms &amp; Conditions
                      </Link>
                      <Link
                        href="/privacy"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <Info size={15} className="text-purple-500" /> Privacy Policy
                      </Link>
                      <Link
                        href="/accessibility"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <ShieldAlert size={15} className="text-teal-500" /> Accessibility Statement
                      </Link>
                      <Link
                        href="/about"
                        onClick={() => setIsProfileOpen(false)}
                        className="flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-foreground hover:bg-secondary rounded-xl transition-colors"
                      >
                        <Compass size={15} className="text-rose-500" /> About NavSakhi
                      </Link>
                    </div>

                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setIsProfileOpen(false);
                          handleLogout();
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-semibold text-danger hover:bg-danger/10 rounded-xl transition-colors"
                      >
                        <LogOut size={15} /> Sign Out
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="hidden lg:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-secondary/70 text-muted-foreground border border-border/60">
                Guest Explorer
              </span>
              <Link href="/login">
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-full text-xs font-bold border-primary/30 text-primary hover:bg-primary/10 px-3.5 py-1.5 h-8 shadow-2xs"
                >
                  Sign In
                </Button>
              </Link>
            </div>
          )}

          {/* Emergency SOS Action with Accessible Info Button */}
          <div className="flex items-center gap-1.5">
            <Link href="/emergency">
              <Button
                size="sm"
                className="rounded-full gap-1.5 bg-danger text-white hover:bg-danger/90 font-bold px-3 sm:px-3.5 py-1.5 text-xs shadow-md shadow-danger/25 transition-transform active:scale-95"
                aria-label="Emergency SOS"
              >
                <ShieldAlert size={15} className="shrink-0 animate-pulse-soft" />
                <span>Emergency SOS</span>
              </Button>
            </Link>
            <button
              type="button"
              onClick={() => setIsSosInfoOpen(true)}
              className="p-1.5 rounded-full text-muted-foreground hover:text-danger hover:bg-danger/10 border border-border/60 transition-colors shrink-0"
              title="Emergency SOS Demonstration Information & Scope"
              aria-label="Emergency SOS Demonstration Information"
            >
              <Info size={14} />
            </button>
          </div>

        </div>

      </div>

      {/* Emergency SOS Scope & Demonstration Limitations Modal */}
      <Dialog open={isSosInfoOpen} onOpenChange={setIsSosInfoOpen}>
        <DialogContent className="max-w-lg rounded-3xl p-6 border-border shadow-2xl bg-card text-foreground">
          <DialogHeader className="space-y-2">
            <div className="flex items-center gap-2 text-danger">
              <ShieldAlert size={20} />
              <DialogTitle className="text-base font-bold font-[family-name:var(--font-jakarta)]">
                Emergency SOS — Prototype Scope & Architecture
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground">
              Architectural disclosure for the NavSakhi personal software project prototype.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2 text-xs leading-relaxed text-muted-foreground">
            <div className="p-3.5 rounded-2xl bg-danger/10 border border-danger/20 text-foreground space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-danger">
                <AlertTriangle size={15} />
                <span>Prototype Disclosures (No Live Emergency Dispatch)</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                NavSakhi is a personal-interest software project and working prototype. In this local demonstration, 
                <strong> no real police dispatch, 112 emergency calls, or automated SMS/PSTN cellular broadcasts are conducted.</strong>
              </p>
            </div>

            <div className="space-y-2">
              <p className="font-bold text-foreground">Designed Operational Capabilities:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground text-[11px]">
                <li><strong>Local Simulation:</strong> Authenticated users can simulate the response sequence, preview staged distress payloads, and inspect nearest safe havens.</li>
                <li><strong>User-Initiated Native Sharing:</strong> When triggered explicitly by the user, the browser's native share sheet (or SMS deep-link / clipboard) generates a verified tracking link with explicit user consent.</li>
                <li><strong>Privacy & Location Consent:</strong> NavSakhi never automatically polls or transmits your GPS coordinates merely by opening the interface. Explicit user action is required.</li>
              </ul>
            </div>

            <div className="p-3 rounded-2xl bg-secondary/50 border border-border/70 text-[11px] space-y-1">
              <span className="font-bold text-foreground block">Real-World Helplines:</span>
              <p>For actual distress in India, always dial <strong>112 (National Emergency)</strong> or <strong>1091 (Women Helpline)</strong>.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
}
