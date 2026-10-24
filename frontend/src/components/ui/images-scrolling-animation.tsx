"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { motion, useAnimationControls } from "framer-motion";
import { cn } from "@/lib/utils";
import { Sparkles, Compass } from "lucide-react";

export interface ScrollingImageItem {
  src: string;
  title: string;
  category: string;
  alt: string;
}

const DEFAULT_NAVSAKHI_IMAGES: ScrollingImageItem[] = [
  {
    src: "/images/navsakhi/metro_commuter_transit.jpg",
    title: "Platform Waiting & Line Sync",
    category: "Metro Transit Platform",
    alt: "Woman commuter checking transit schedule on platform with arriving metro train",
  },
  {
    src: "/images/navsakhi/transit_women_platform.jpg",
    title: "Rail & Suburban Connections",
    category: "Suburban Rail Network",
    alt: "Two women travelers navigating public railway platform together",
  },
  {
    src: "/images/navsakhi/transit_commuter_navigating.jpg",
    title: "First-Mile Walking Directions",
    category: "Pedestrian Navigation",
    alt: "Commuter checking navigation directions on smartphone while walking",
  },
  {
    src: "/images/navsakhi/transit_station_corridor.jpg",
    title: "Illuminated Urban Thoroughfares",
    category: "Night Roadway Lighting",
    alt: "Illuminated nighttime urban roadway with street lighting and traffic lanes",
  },
  {
    src: "/images/navsakhi/community_solidarity.jpg",
    title: "Collaborative Safety Network",
    category: "Community Route Reports",
    alt: "Women commuters collaborating on safe neighborhood route information",
  },
];

interface ImagesScrollingAnimationProps {
  images?: ScrollingImageItem[];
  speed?: number;
  direction?: "left" | "right";
  className?: string;
}

export function ImagesScrollingAnimation({
  images = DEFAULT_NAVSAKHI_IMAGES,
  speed = 28,
  direction = "left",
  className,
}: ImagesScrollingAnimationProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(media.matches);
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  // Duplicate items twice to enable seamless seamless infinite loop
  const displayItems = [...images, ...images];

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden py-8 sm:py-12 select-none",
        className
      )}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
    >
      {/* Edge gradient masks for seamless fade */}
      <div className="pointer-events-none absolute left-0 top-0 bottom-0 z-10 w-12 sm:w-28 bg-gradient-to-r from-background to-transparent" />
      <div className="pointer-events-none absolute right-0 top-0 bottom-0 z-10 w-12 sm:w-28 bg-gradient-to-l from-background to-transparent" />

      <div
        className={cn(
          "flex items-center gap-5 sm:gap-6 w-max",
          prefersReducedMotion ? "overflow-x-auto no-scrollbar" : ""
        )}
      >
        <motion.div
          className="flex items-center gap-5 sm:gap-6 shrink-0"
          animate={
            prefersReducedMotion
              ? {}
              : {
                  x: direction === "left" ? ["0%", "-50%"] : ["-50%", "0%"],
                }
          }
          transition={
            prefersReducedMotion
              ? {}
              : {
                  x: {
                    repeat: Infinity,
                    repeatType: "loop",
                    duration: speed,
                    ease: "linear",
                  },
                }
          }
          style={{
            animationPlayState: isPaused ? "paused" : "running",
          }}
        >
          {displayItems.map((item, index) => (
            <div
              key={`${item.src}-${index}`}
              className="group relative h-64 sm:h-72 w-72 sm:w-80 shrink-0 overflow-hidden rounded-3xl border border-border/80 bg-card/60 backdrop-blur-md shadow-md transition-all duration-300 hover:shadow-xl hover:border-primary/40 hover:-translate-y-1"
            >
              <Image
                src={item.src}
                alt={item.alt}
                fill
                sizes="(max-width: 768px) 288px, 320px"
                className="object-cover transition-transform duration-700 ease-out group-hover:scale-105"
              />
              
              {/* Overlay gradient - dark translucent to preserve photo colors in light mode */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent pointer-events-none" />

              {/* Category pill top left */}
              <div className="absolute top-3.5 left-3.5 z-10">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-black/60 text-white backdrop-blur-md border border-white/20 shadow-xs">
                  <Compass size={12} className="text-primary" />
                  {item.category}
                </span>
              </div>

              {/* Title bottom */}
              <div className="absolute bottom-4 left-4 right-4 z-10">
                <h3 className="font-[family-name:var(--font-jakarta)] text-sm sm:text-base font-extrabold text-white leading-snug drop-shadow-md">
                  {item.title}
                </h3>
              </div>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
