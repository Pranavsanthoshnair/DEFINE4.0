"use client";

import React, { useRef } from "react";
import { useInView } from "@/hooks/useInView";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface TileData {
  id: string;
  lang: string;
  code: string;
  heightPx: number;
  color: string;
}

const TILES: TileData[] = [
  { id: "en", lang: "English", code: "EN", heightPx: 34, color: "#17263A" },
  { id: "hi", lang: "Hindi", code: "HI", heightPx: 70, color: "#E10600" },
  { id: "ml", lang: "Malayalam", code: "ML", heightPx: 52, color: "#FFD700" },
  { id: "ta", lang: "Tamil", code: "TA", heightPx: 96, color: "#B7D8F5" },
];

export default function IsometricTileSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { threshold: 0.15, once: true });
  const reducedMotion = useReducedMotion();

  return (
    <section
      ref={containerRef}
      className="relative w-full py-20 bg-[#0D1622] overflow-hidden text-white my-12 rounded-2xl border border-slate-800"
      aria-label="Multilingual Isometric Language Stage"
    >
      <div className="max-w-xl mx-auto text-center mb-12 px-4">
        <span className="text-xs font-mono tracking-widest text-[var(--yellow)] uppercase">Multilingual Engine</span>
        <h2 className="text-3xl font-extrabold tracking-tight mt-2 text-white">
          Four Languages. One Unified Campaign.
        </h2>
        <p className="text-sm text-slate-400 mt-2">
          Language tiles rise dynamically based on audience segment distribution.
        </p>
      </div>

      {/* 3D Isometric Stage Container */}
      <div
        className="relative w-full max-w-2xl h-[380px] mx-auto flex items-center justify-center"
        aria-hidden="true"
        style={{ perspective: 1100 }}
      >
        {/* Inner Isometric Plane */}
        <div
          className="relative w-[340px] h-[340px] border-2 border-dashed border-slate-700/60 rounded-3xl p-6 grid grid-cols-2 gap-6"
          style={{
            transformStyle: "preserve-3d",
            transform: "rotateX(58deg) rotateZ(-34deg)",
          }}
        >
          {TILES.map((tile, idx) => {
            const isTargetHeight = isInView || reducedMotion;
            const currentHeight = isTargetHeight ? tile.heightPx : 0;
            const staggerDelay = idx * 170;

            return (
              <div key={tile.id} className="relative w-full h-full" style={{ transformStyle: "preserve-3d" }}>
                {/* Shadow Square on Base Plate */}
                <div
                  className="absolute inset-0 bg-black/60 rounded-2xl pointer-events-none transition-all duration-[1100ms]"
                  style={{
                    transform: isTargetHeight
                      ? `translate3d(${currentHeight * 0.3}px, ${currentHeight * 0.3}px, 0px)`
                      : "translate3d(0px, 0px, 0px)",
                    filter: isTargetHeight ? "blur(8px)" : "blur(0px)",
                    opacity: isTargetHeight ? 0.7 : 0.3,
                    transitionTimingFunction: "cubic-bezier(0.3, 1.7, 0.4, 1)",
                    transitionDelay: `${staggerDelay}ms`,
                  }}
                />

                {/* Rising Language Tile */}
                <div
                  className="relative w-full h-full rounded-2xl p-4 flex flex-col justify-between border border-white/20 shadow-xl cursor-pointer"
                  style={{
                    backgroundColor: tile.color === "#FFD700" ? "#D4AC0D" : tile.color,
                    color: tile.color === "#FFD700" || tile.color === "#B7D8F5" ? "#17263A" : "#FFFDF8",
                    transformStyle: "preserve-3d",
                    transform: `translateZ(${currentHeight}px)`,
                    transition: `transform 1.1s cubic-bezier(0.3, 1.7, 0.4, 1) ${staggerDelay}ms`,
                  }}
                >
                  <span className="text-2xl font-extrabold">{tile.code}</span>
                  <div className="flex justify-between items-end">
                    <span className="text-xs font-bold">{tile.lang}</span>
                    <span className="text-[10px] font-mono opacity-80">{tile.heightPx}px</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
