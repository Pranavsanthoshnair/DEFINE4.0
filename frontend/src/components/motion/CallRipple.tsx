"use client";

import React, { useRef, useEffect, useState } from "react";
import { useReducedMotion } from "@/hooks/useReducedMotion";

export interface Recipient {
  id: string;
  name: string;
  language: string;
  status: "confirmed" | "declined" | "no_answer" | "busy" | "voicemail" | "callback";
  phone?: string;
}

export interface CallRippleProps {
  recipients?: Recipient[];
  hostLabel?: string;
  className?: string;
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: "#17263A",
  declined: "#E10600",
  no_answer: "#E10600",
  busy: "#E10600",
  voicemail: "#FFD700",
  callback: "#B7D8F5",
};

export default function CallRipple({
  recipients = [],
  hostLabel = "VY",
  className = "",
}: CallRippleProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  // Store active recipients in a ref so data updates do not restart animation
  const recipientsRef = useRef(recipients);
  recipientsRef.current = recipients;

  const pointerXRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let startTime = performance.now();
    let driftAngle = 0;

    // Pointer listener for constellation yaw
    const handlePointerMove = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      const normX = (e.clientX - rect.left) / rect.width - 0.5;
      pointerXRef.current = normX * 0.3; // max yaw
    };

    container.addEventListener("pointermove", handlePointerMove);

    const resizeCanvas = () => {
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    const resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(container);
    resizeCanvas();

    const drawFrame = (now: number) => {
      const rect = container.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const cx = w / 2;
      const cy = h / 2;
      const elapsedSec = (now - startTime) / 1000;

      ctx.clearRect(0, 0, w, h);

      // Dark radial background stage
      const bgGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, Math.max(w, h) * 0.6);
      bgGrad.addColorStop(0, "rgba(23, 38, 58, 0.95)");
      bgGrad.addColorStop(1, "rgba(10, 18, 28, 0.98)");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Orbit parameters
      const orbits = [Math.min(w, h) * 0.22, Math.min(w, h) * 0.35, Math.min(w, h) * 0.46];
      const flattenY = 0.44;

      // Draw dashed elliptical orbits
      ctx.save();
      ctx.strokeStyle = "rgba(183, 216, 245, 0.25)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 6]);
      orbits.forEach((r) => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, r, r * flattenY, 0, 0, Math.PI * 2);
        ctx.stroke();
      });
      ctx.restore();

      // Host Node in Centre
      const hostPulsePeriod = 1.4;
      const pulseProgress = (elapsedSec % hostPulsePeriod) / hostPulsePeriod;
      const pulseRadius = 24 + pulseProgress * 28;
      const pulseAlpha = (1 - pulseProgress) * 0.7;

      // Host pulse ring
      ctx.beginPath();
      ctx.arc(cx, cy, pulseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 215, 0, ${pulseAlpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Host glowing core
      ctx.beginPath();
      ctx.arc(cx, cy, 22, 0, Math.PI * 2);
      ctx.fillStyle = "#E10600";
      ctx.shadowColor = "#FFD700";
      ctx.shadowBlur = 18;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Host text
      ctx.fillStyle = "#FFFDF8";
      ctx.font = "800 13px 'Manrope', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(hostLabel, cx, cy);

      // Recipients rendering
      const list = recipientsRef.current;
      driftAngle = reducedMotion ? 0 : elapsedSec * 0.08 + pointerXRef.current;

      list.forEach((rec, idx) => {
        const orbitIndex = idx % orbits.length;
        const radius = orbits[orbitIndex];
        const baseAngle = (idx / Math.max(list.length, 1)) * Math.PI * 2;
        const angle = baseAngle + driftAngle;

        // Position on 2.5D flattened ellipse
        const x = cx + Math.cos(angle) * radius;
        const y = cy + Math.sin(angle) * radius * flattenY;

        // Scale node by depth (sin angle)
        const depthScale = 0.75 + (Math.sin(angle) + 1) * 0.25; // 0.75 to 1.25
        const nodeRadius = 8 * depthScale;

        // Sequential reveal delay (80ms per item)
        const revealTime = idx * 0.08;
        const isRevealed = reducedMotion || elapsedSec >= revealTime;

        if (isRevealed) {
          // Beam from host to node
          const beamProgress = reducedMotion ? 1 : Math.min((elapsedSec - revealTime) / 0.3, 1);
          const beamX = cx + (x - cx) * beamProgress;
          const beamY = cy + (y - cy) * beamProgress;

          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(beamX, beamY);
          ctx.strokeStyle = "rgba(255, 215, 0, 0.4)";
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Node fill color based on status
          const color = STATUS_COLORS[rec.status] || "#B7D8F5";
          ctx.beginPath();
          ctx.arc(x, y, nodeRadius, 0, Math.PI * 2);
          ctx.fillStyle = color;

          if (rec.status === "confirmed" || rec.status === "callback") {
            ctx.shadowColor = color;
            ctx.shadowBlur = 12;
          }
          ctx.fill();
          ctx.shadowBlur = 0;

          // Unanswered nodes keep a pulsing red outline
          if (rec.status === "no_answer" || rec.status === "busy") {
            ctx.beginPath();
            ctx.arc(x, y, nodeRadius + 3, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(225, 6, 0, ${0.5 + Math.sin(elapsedSec * 4) * 0.4})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }

          // Node expanding ripple ring on reveal
          const rippleTime = elapsedSec - revealTime;
          if (!reducedMotion && rippleTime >= 0 && rippleTime <= 0.6) {
            const rProgress = rippleTime / 0.6;
            ctx.beginPath();
            ctx.arc(x, y, nodeRadius + rProgress * 20, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(183, 216, 245, ${1 - rProgress})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }
      });

      if (!reducedMotion) {
        animationFrameId = requestAnimationFrame(drawFrame);
      }
    };

    if (reducedMotion) {
      drawFrame(performance.now());
    } else {
      animationFrameId = requestAnimationFrame(drawFrame);
    }

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      container.removeEventListener("pointermove", handlePointerMove);
      resizeObserver.disconnect();
    };
  }, [hostLabel, reducedMotion]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full overflow-hidden rounded-xl ${className}`}
      style={{ height: 380, background: "#0D1622" }}
      role="img"
      aria-label="Live call outcome ripple constellation graph showing active participant connection statuses"
    >
      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* Accessible visual legend overlay */}
      <div className="absolute top-3 left-3 flex gap-3 text-xs font-mono text-white/80 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-md border border-white/10">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#17263A] border border-white/40" /> Confirmed</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#E10600]" /> Declined/No Answer</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#FFD700]" /> Voicemail</span>
      </div>
    </div>
  );
}
