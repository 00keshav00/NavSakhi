"use client";

import React, { useRef, useState, useEffect } from "react";
import { useScroll, useTransform, motion, MotionValue } from "framer-motion";
import { cn } from "@/lib/utils";

interface ContainerScrollProps {
  titleComponent: string | React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const ContainerScroll = ({
  titleComponent,
  children,
  className,
}: ContainerScrollProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    const checkMotion = () => {
      setPrefersReducedMotion(
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    };

    checkMobile();
    checkMotion();

    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  });

  const scaleDimensions = () => {
    return isMobile ? [0.9, 1] : [0.95, 1];
  };

  const rotate = useTransform(
    scrollYProgress,
    [0, 0.6],
    prefersReducedMotion ? [0, 0] : [12, 0]
  );
  const scale = useTransform(scrollYProgress, [0, 0.6], scaleDimensions());
  const translateY = useTransform(
    scrollYProgress,
    [0, 0.6],
    prefersReducedMotion ? [0, 0] : [40, 0]
  );

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative flex flex-col items-center justify-center py-4 sm:py-8 [perspective:1000px]",
        className
      )}
    >
      <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <Header translateY={translateY} titleComponent={titleComponent} />
        <Card rotate={rotate} scale={scale}>
          {children}
        </Card>
      </div>
    </div>
  );
};

interface HeaderProps {
  translateY: MotionValue<number>;
  titleComponent: string | React.ReactNode;
}

const Header = ({ translateY, titleComponent }: HeaderProps) => {
  return (
    <motion.div
      style={{
        translateY,
      }}
      className="max-w-4xl mx-auto text-center mb-8 sm:mb-12"
    >
      {titleComponent}
    </motion.div>
  );
};

interface CardProps {
  rotate: MotionValue<number>;
  scale: MotionValue<number>;
  children: React.ReactNode;
}

const Card = ({ rotate, scale, children }: CardProps) => {
  return (
    <motion.div
      style={{
        rotateX: rotate,
        scale,
      }}
      className="w-full rounded-[28px] sm:rounded-[36px] border border-border/70 bg-card/70 p-2 sm:p-4 shadow-[0_20px_50px_rgba(235,59,112,0.08)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-2xl transition-colors"
    >
      <div className="overflow-hidden rounded-[22px] sm:rounded-[28px] bg-background/90 border border-border/50">
        {children}
      </div>
    </motion.div>
  );
};
