"use client";

import React, { useRef, useState, useEffect } from "react";
import { useInView } from "@/hooks/useInView";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface RevealProps {
  children: React.ReactNode;
  direction?: "center" | "left" | "right";
  staggerIndex?: number;
  className?: string;
  style?: React.CSSProperties;
  as?: React.ElementType;
}

export default function Reveal({
  children,
  direction = "center",
  staggerIndex = 0,
  className = "",
  style = {},
  as: Component = "div",
}: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { threshold: 0.15, once: true });
  const reducedMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [arrived, setArrived] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isInView) {
      const delayMs = staggerIndex * 90;
      const timer = setTimeout(() => {
        // Drop animation styles after 1s so hover effects work cleanly
        const resetTimer = setTimeout(() => {
          setArrived(true);
        }, 1000);
        return () => clearTimeout(resetTimer);
      }, delayMs);
      return () => clearTimeout(timer);
    }
  }, [isInView, staggerIndex]);

  // SSR or reduced motion: return completely visible
  if (!mounted || reducedMotion || arrived) {
    return (
      <Component ref={ref} className={className} style={style}>
        {children}
      </Component>
    );
  }

  // Define starting 3D transform based on direction specification
  let startTransform = "perspective(1000px) translate3d(0, 50px, -240px) rotateX(24deg)";
  if (direction === "left") {
    startTransform = "perspective(1000px) translate3d(-90px, 30px, -220px) rotateY(26deg)";
  } else if (direction === "right") {
    startTransform = "perspective(1000px) translate3d(90px, 30px, -220px) rotateY(-26deg)";
  }

  const animationStyle: React.CSSProperties = {
    ...style,
    transformOrigin: "bottom center",
    transform: isInView ? "perspective(1000px) translate3d(0,0,0) rotateX(0deg) rotateY(0deg)" : startTransform,
    opacity: isInView ? 1 : 0,
    transition: `transform 1s cubic-bezier(0.2, 0.9, 0.25, 1) ${staggerIndex * 90}ms, opacity 0.6s cubic-bezier(0.2, 0.9, 0.25, 1) ${staggerIndex * 90}ms`,
    willChange: isInView ? "auto" : "transform, opacity",
  };

  return (
    <Component ref={ref} className={className} style={animationStyle}>
      {children}
    </Component>
  );
}
