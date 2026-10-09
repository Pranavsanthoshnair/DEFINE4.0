"use client";

import React, { useRef } from "react";
import { usePointerTilt } from "@/hooks/usePointerTilt";

interface TiltProps {
  children: React.ReactNode;
  maxDegreeX?: number;
  maxDegreeY?: number;
  perspective?: number;
  className?: string;
  style?: React.CSSProperties;
}

export default function Tilt({
  children,
  maxDegreeX = 10,
  maxDegreeY = 16,
  perspective = 800,
  className = "",
  style = {},
}: TiltProps) {
  const ref = useRef<HTMLDivElement>(null);
  const tiltStyle = usePointerTilt(ref, { maxDegreeX, maxDegreeY, perspective });

  return (
    <div
      ref={ref}
      className={className}
      style={{
        ...style,
        ...tiltStyle,
        transformStyle: "preserve-3d",
      }}
    >
      {children}
    </div>
  );
}
