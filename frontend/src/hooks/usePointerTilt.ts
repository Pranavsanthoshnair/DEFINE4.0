"use client";

import { useEffect, useState, RefObject } from "react";
import { useReducedMotion } from "./useReducedMotion";

interface PointerTiltOptions {
  maxDegreeX?: number;
  maxDegreeY?: number;
  perspective?: number;
}

export function usePointerTilt<T extends HTMLElement>(
  ref: RefObject<T | null>,
  options: PointerTiltOptions = {}
) {
  const { maxDegreeX = 10, maxDegreeY = 16, perspective = 800 } = options;
  const reducedMotion = useReducedMotion();
  const [style, setStyle] = useState<React.CSSProperties>({
    transform: `perspective(${perspective}px) rotateX(0deg) rotateY(0deg)`,
    transition: "transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1)",
  });

  useEffect(() => {
    const node = ref.current;
    if (!node || reducedMotion) return;

    // Disable on touch devices
    if (window.matchMedia("(pointer: coarse)").matches) return;

    let rafId: number | null = null;

    const handlePointerMove = (e: PointerEvent) => {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const rect = node.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const mouseX = e.clientX - centerX;
        const mouseY = e.clientY - centerY;

        const rotateY = (mouseX / (rect.width / 2)) * maxDegreeY;
        const rotateX = -(mouseY / (rect.height / 2)) * maxDegreeX;

        setStyle({
          transform: `perspective(${perspective}px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg)`,
          transition: "transform 0.1s ease-out",
        });
      });
    };

    const handlePointerLeave = () => {
      if (rafId) cancelAnimationFrame(rafId);
      setStyle({
        transform: `perspective(${perspective}px) rotateX(0deg) rotateY(0deg)`,
        transition: "transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)",
      });
    };

    node.addEventListener("pointermove", handlePointerMove);
    node.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      node.removeEventListener("pointermove", handlePointerMove);
      node.removeEventListener("pointerleave", handlePointerLeave);
    };
  }, [ref, maxDegreeX, maxDegreeY, perspective, reducedMotion]);

  return style;
}
