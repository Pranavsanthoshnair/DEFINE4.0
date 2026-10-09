"use client";

import React, { useRef, useState, useEffect } from "react";
import { useInView } from "@/hooks/useInView";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface SplitTextProps {
  text: string;
  className?: string;
  as?: React.ElementType;
  style?: React.CSSProperties;
}

export default function SplitText({
  text,
  className = "",
  as: Component = "h1",
  style = {},
}: SplitTextProps) {
  const containerRef = useRef<HTMLElement>(null);
  const isInView = useInView(containerRef, { threshold: 0.15, once: true });
  const reducedMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || reducedMotion) {
    return (
      <Component className={className} style={style}>
        {text}
      </Component>
    );
  }

  const words = text.split(" ");
  let globalLetterCount = 0;

  return (
    <Component
      ref={containerRef}
      className={`split-text-container ${className}`}
      style={{ ...style, perspective: 800 }}
      aria-label={text}
    >
      {words.map((word, wordIdx) => {
        const letters = Array.from(word);
        return (
          <span
            key={wordIdx}
            className="split-word"
            style={{ display: "inline-block", whiteSpace: "nowrap", marginRight: "0.25em" }}
            aria-hidden="true"
          >
            {letters.map((char, charIdx) => {
              const letterIndex = globalLetterCount++;
              const delayMs = letterIndex * 30;

              const charStyle: React.CSSProperties = {
                display: "inline-block",
                transformOrigin: "bottom center",
                transform: isInView
                  ? "rotateX(0deg) translateZ(0px)"
                  : "rotateX(-100deg) translateZ(-40px)",
                opacity: isInView ? 1 : 0,
                transition: `transform 0.85s cubic-bezier(0.2, 1.5, 0.3, 1) ${delayMs}ms, opacity 0.4s ease ${delayMs}ms`,
                cursor: "pointer",
              };

              return (
                <span key={charIdx} className="split-char-wrapper" style={{ display: "inline-block", perspective: 600 }}>
                  <span
                    className="split-char"
                    style={charStyle}
                  >
                    {char}
                  </span>
                </span>
              );
            })}
          </span>
        );
      })}
    </Component>
  );
}
