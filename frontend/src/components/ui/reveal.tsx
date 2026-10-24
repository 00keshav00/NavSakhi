"use client";

import React, { useState, useEffect } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

interface RevealProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  index?: number;
  delay?: number;
  duration?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
  className?: string;
  once?: boolean;
}

export function Reveal({
  children,
  index = 0,
  delay,
  duration = 0.55,
  direction = "up",
  className,
  once = true,
  ...props
}: RevealProps) {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(media.matches);
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  const computedDelay = delay !== undefined ? delay : index * 0.1;

  const getOffset = () => {
    if (prefersReducedMotion || direction === "none") return { x: 0, y: 0 };
    switch (direction) {
      case "up":
        return { x: 0, y: 24 };
      case "down":
        return { x: 0, y: -24 };
      case "left":
        return { x: 24, y: 0 };
      case "right":
        return { x: -24, y: 0 };
      default:
        return { x: 0, y: 24 };
    }
  };

  const offset = getOffset();

  return (
    <motion.div
      initial={{
        opacity: 0,
        x: offset.x,
        y: offset.y,
      }}
      whileInView={{
        opacity: 1,
        x: 0,
        y: 0,
      }}
      viewport={{
        once,
        margin: "-40px",
      }}
      transition={{
        duration: prefersReducedMotion ? 0.1 : duration,
        delay: prefersReducedMotion ? 0 : computedDelay,
        ease: [0.16, 1, 0.3, 1] as const,
      }}
      className={cn("w-full", className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export default Reveal;
