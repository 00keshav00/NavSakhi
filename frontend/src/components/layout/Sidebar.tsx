"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { 
  Home, Map as MapIcon, Radio, AlertOctagon, Users, Settings, User, Bot, LogOut
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { toast } from "sonner";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [width, setWidth] = useState(() => {
    if (typeof window !== "undefined") {
      const savedWidth = localStorage.getItem("sidebarWidth");
      if (savedWidth) return Number(savedWidth);
    }
    return 280;
  });
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  
  const isCollapsed = width < 120;

  const handleLogout = () => {
    useAuthStore.getState().logout();
    toast.info("Signed out", { description: "Session ended. Please sign in to continue." });
    router.push("/login");
  };

  useEffect(() => {
    if (!isResizing) {
      localStorage.setItem("sidebarWidth", width.toString());
    }
  }, [isResizing, width]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      let newWidth = e.clientX;
      if (newWidth < 120) newWidth = 80;
      if (newWidth > 120 && newWidth < 200) newWidth = 280;
      if (newWidth > 400) newWidth = 400;
      setWidth(newWidth);
    };

    const handleMouseUp = () => setIsResizing(false);

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const navItems = [
    { name: "Dashboard", href: "/home", icon: Home },
    { name: "Journey", href: "/journey", icon: MapIcon },
    { name: "Live Monitor", href: "/live", icon: Radio },
    { name: "Community", href: "/community", icon: Users },
    { name: "AI Assistant", href: "/assistant", icon: Bot },
  ];

  const bottomItems = [
    { name: "Profile", href: "/profile", icon: User },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <motion.aside 
      ref={sidebarRef}
      animate={{ width }}
      transition={{ duration: isResizing ? 0 : 0.3, ease: "easeInOut" }}
      className="relative z-40 hidden h-full flex-col border-r border-border bg-card/80 backdrop-blur-3xl md:flex shrink-0"
    >
      <div className={`flex h-20 items-center border-b border-border/50 ${isCollapsed ? 'justify-center px-2' : 'px-6'}`}>
        <Link href="/home" className="flex items-center gap-3 transition-transform active:scale-95">
          {isCollapsed ? (
            <div className="relative w-10 h-10 flex items-center justify-center">
              <Image 
                src="/images/navsakhi/navsakhi_emblem.png" 
                alt="NavSakhi Emblem" 
                width={38} 
                height={38} 
                className="object-contain" 
              />
            </div>
          ) : (
            <div className="relative h-10 w-44 flex items-center">
              <Image 
                src="/images/navsakhi/navsakhi_logo_official.png" 
                alt="NavSakhi" 
                width={175} 
                height={56} 
                className="h-10 w-auto object-contain dark:drop-shadow-[0_0_10px_rgba(255,255,255,0.55)] dark:brightness-110" 
              />
            </div>
          )}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.name} href={item.href} title={isCollapsed ? item.name : ""}>
              <div className={`group flex items-center gap-4 rounded-xl px-4 py-3 font-medium transition-all duration-200 ${isActive ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`}>
                <item.icon size={22} className={`shrink-0 ${isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground transition-colors"}`} />
                {!isCollapsed && <span className="truncate">{item.name}</span>}
              </div>
            </Link>
          );
        })}
        
        <div className="pt-4 mt-4 border-t border-border/50">
          <Link href="/emergency" title={isCollapsed ? "Emergency SOS" : ""}>
            <div className={`group flex items-center gap-4 rounded-xl px-4 py-3 font-bold transition-all duration-200 ${pathname === "/emergency" ? "bg-danger text-white shadow-md shadow-danger/20" : "bg-danger/10 text-danger hover:bg-danger hover:text-white"}`}>
              <AlertOctagon size={22} className="shrink-0" />
              {!isCollapsed && <span className="truncate">Emergency SOS</span>}
            </div>
          </Link>
        </div>
      </nav>

      <div className="border-t border-border/50 bg-background/30 p-4 space-y-2">
        {bottomItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link key={item.name} href={item.href} title={isCollapsed ? item.name : ""}>
              <div className={`group flex items-center gap-4 rounded-xl px-4 py-3 font-medium transition-all duration-200 ${isActive ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`}>
                <item.icon size={22} className="shrink-0" />
                {!isCollapsed && <span className="truncate">{item.name}</span>}
              </div>
            </Link>
          );
        })}
        <button
          type="button"
          onClick={handleLogout}
          title={isCollapsed ? "Sign Out" : ""}
          className="w-full text-left group flex items-center gap-4 rounded-xl px-4 py-3 font-medium text-muted-foreground hover:bg-danger/10 hover:text-danger transition-all duration-200"
        >
          <LogOut size={22} className="shrink-0 transition-transform group-hover:-translate-x-0.5" />
          {!isCollapsed && <span className="truncate">Sign Out</span>}
        </button>
      </div>

      <div 
        onMouseDown={() => setIsResizing(true)}
        className="absolute -right-1 top-0 bottom-0 w-2 cursor-col-resize hover:bg-primary/50 transition-colors z-50"
      />
    </motion.aside>
  );
}