"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

export function useScrollDepth(maxScroll = 220): number {
  const [progress, setProgress] = useState(0);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion || typeof window === "undefined") return;

    let rafId: number | null = null;

    const handleScroll = () => {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const current = window.scrollY || window.pageYOffset || 0;
        const clamped = Math.min(Math.max(current / maxScroll, 0), 1);
        setProgress(clamped);
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll(); // Initial call

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [maxScroll, reducedMotion]);

  return reducedMotion ? 0 : progress;
}
