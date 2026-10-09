"use client";

import React, { useRef, useState, useEffect } from "react";
import { useScrollDepth } from "@/hooks/useScrollDepth";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export default function HeroDepth() {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollProgress = useScrollDepth(220);
  const reducedMotion = useReducedMotion();

  const [tilt, setTilt] = useState({ rotX: 0, rotY: 0 });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || reducedMotion) return;
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

        const rotY = (mouseX / (rect.width / 2)) * 12;
        const rotX = -(mouseY / (rect.height / 2)) * 9;

        setTilt({ rotX, rotY });
      });
    };

    const handlePointerLeave = () => {
      if (rafId) cancelAnimationFrame(rafId);
      setTilt({ rotX: 0, rotY: 0 });
    };

    node.addEventListener("pointermove", handlePointerMove);
    node.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      node.removeEventListener("pointermove", handlePointerMove);
      node.removeEventListener("pointerleave", handlePointerLeave);
    };
  }, [reducedMotion]);

  // Calculate scroll depth transforms
  const scrollTranslateZ = scrollProgress * 100;
  const scrollTranslateY = -scrollProgress * 30;
  const scrollScale = 1 + scrollProgress * 0.06;
  const scrollRotateX = scrollProgress * 10;

  const phoneTransform = mounted && !reducedMotion
    ? `translate3d(0px, ${80 * (1 - Math.min(scrollProgress * 2, 1)) + scrollTranslateY}px, ${scrollTranslateZ}px) rotateX(${75 * (1 - Math.min(scrollProgress * 2, 1)) + tilt.rotX + scrollRotateX}deg) rotateY(${tilt.rotY}deg) scale(${0.5 + 0.5 * Math.min(scrollProgress * 2, 1) * scrollScale})`
    : "none";

  return (
    <div
      ref={containerRef}
      className="hero-depth-container relative w-full h-full flex items-center justify-center overflow-hidden p-4"
      style={{ perspective: 1100, transformStyle: "preserve-3d" }}
    >
      {/* Drifting Yellow Sun */}
      <div
        className="absolute top-6 right-12 w-14 h-14 rounded-full bg-[var(--yellow)] shadow-[0_0_30px_rgba(255,215,0,0.6)] pointer-events-none"
        style={{
          animation: reducedMotion ? "none" : "sunDrift 6s ease-in-out infinite alternate",
        }}
      />

      {/* SVG Dashed Network Paths with Traveling Dots */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
        viewBox="0 0 500 400"
        fill="none"
      >
        <path
          d="M 50 350 Q 250 150 450 80"
          stroke="rgba(23, 38, 58, 0.15)"
          strokeWidth="1.5"
          strokeDasharray="4 6"
        />
        <path
          d="M 50 80 Q 250 250 450 350"
          stroke="rgba(225, 6, 0, 0.2)"
          strokeWidth="1.5"
          strokeDasharray="4 6"
        />
        {!reducedMotion && (
          <>
            <circle r="4" fill="#E10600">
              <animateMotion path="M 50 350 Q 250 150 450 80" dur="4.8s" repeatCount="indefinite" />
            </circle>
            <circle r="4" fill="#FFD700">
              <animateMotion path="M 50 80 Q 250 250 450 350" dur="5.4s" repeatCount="indefinite" />
            </circle>
          </>
        )}
      </svg>

      {/* Parallax Chips */}
      <div
        className="absolute top-16 left-8 z-20 px-3 py-1.5 rounded-full bg-white/90 shadow-lg border border-slate-200 text-xs font-bold text-slate-800"
        style={{
          transform: `translate3d(${tilt.rotY * -1.5}px, ${tilt.rotX * -1.5}px, ${130 + scrollProgress * 20}px)`,
          transition: "transform 0.15s ease-out",
        }}
      >
        <span>● Malayalam</span>
      </div>
      <div
        className="absolute bottom-20 right-8 z-20 px-3 py-1.5 rounded-full bg-white/90 shadow-lg border border-slate-200 text-xs font-bold text-slate-800"
        style={{
          transform: `translate3d(${tilt.rotY * 1.8}px, ${tilt.rotX * 1.8}px, ${150 + scrollProgress * 20}px)`,
          transition: "transform 0.15s ease-out",
        }}
      >
        <span>96.8% Reach</span>
      </div>

      {/* Main 3D Phone Mockup Container */}
      <div
        className="relative z-10 w-full max-w-[320px] bg-slate-900 border-4 border-slate-800 rounded-[38px] p-4 shadow-2xl overflow-hidden"
        style={{
          transform: phoneTransform,
          transition: "transform 0.3s cubic-bezier(0.2, 0.9, 0.25, 1)",
          transformStyle: "preserve-3d",
        }}
      >
        {/* Phone Notch */}
        <div className="w-28 h-4 bg-slate-800 rounded-full mx-auto mb-4" />

        {/* Dynamic Mobile Invitation Card */}
        <div className="bg-slate-50 rounded-2xl p-4 text-center border border-slate-200 shadow-inner">
          <div className="w-10 h-10 rounded-full bg-red-100 text-[var(--red)] font-extrabold text-sm flex items-center justify-center mx-auto mb-2 border border-red-200">
            VY
          </div>
          <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">Incoming Call</span>
          <h3 className="text-sm font-extrabold text-slate-900 mt-1">National Tech Summit</h3>
          <p className="text-[11px] text-slate-500 mb-3">12 Nov · Kochi</p>

          {/* Pulsing Waveform Bars */}
          <div className="flex items-center justify-center gap-1 my-3 h-8">
            {[0.4, 0.8, 0.5, 0.9, 0.6, 0.3, 0.7].map((heightScale, i) => (
              <span
                key={i}
                className="w-1.5 bg-[var(--red)] rounded-full"
                style={{
                  height: `${heightScale * 100}%`,
                  animation: reducedMotion ? "none" : `wavePulse 1.2s ease-in-out ${i * 0.15}s infinite alternate`,
                }}
              />
            ))}
          </div>

          <div className="flex justify-around mt-4 pt-3 border-t border-slate-200">
            <button className="w-10 h-10 rounded-full bg-slate-800 text-white font-bold text-xs flex items-center justify-center">
              ✕
            </button>
            <button className="w-10 h-10 rounded-full bg-[var(--red)] text-white font-bold text-xs flex items-center justify-center shadow-lg shadow-red-500/40">
              ✓
            </button>
          </div>
        </div>
      </div>

      {/* Blurred Ellipse Floor Shadow */}
      <div
        className="absolute bottom-4 w-64 h-12 rounded-full bg-black/40 blur-xl pointer-events-none z-0"
        style={{
          transform: `scale(${1 - scrollProgress * 0.2})`,
          transition: "transform 0.3s ease-out",
        }}
      />
    </div>
  );
}
