"use client";

/**
 * DemoModeContext
 * ───────────────
 * Press SPACEBAR 5 times within 2 seconds to toggle demo mode.
 * Demo mode:  pages show rich mock data (no backend needed).
 * Real mode:  pages fetch from NEXT_PUBLIC_API_BASE_URL.
 *
 * A toast banner appears at the top of the screen on toggle.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

// ── Context ───────────────────────────────────────────────────────────────────

interface DemoCtx {
  isDemo: boolean;
  toggle: () => void;
}

const DemoContext = createContext<DemoCtx>({ isDemo: false, toggle: () => {} });

export function useDemo() {
  return useContext(DemoContext);
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function DemoModeProvider({ children }: { children: React.ReactNode }) {
  const [isDemo, setIsDemo] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const spaceTimestamps = useRef<number[]>([]);

  const toggle = useCallback(() => {
    setIsDemo((prev) => {
      const next = !prev;
      setToast(next ? "🎭 Demo mode ON — showing sample data" : "🔴 Live mode — real backend connected");
      setTimeout(() => setToast(null), 3000);
      return next;
    });
  }, []);

  // 5× spacebar within 2 s
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.code !== "Space") return;
      // Ignore if user is typing in an input
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      const now = Date.now();
      spaceTimestamps.current.push(now);
      // Keep only last 5
      spaceTimestamps.current = spaceTimestamps.current.slice(-5);

      if (
        spaceTimestamps.current.length === 5 &&
        now - spaceTimestamps.current[0] < 2000
      ) {
        spaceTimestamps.current = [];
        toggle();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle]);

  return (
    <DemoContext.Provider value={{ isDemo, toggle }}>
      {children}

      {/* Toast banner */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            top: 16,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 9999,
            background: isDemo ? "#FFD700" : "#17263A",
            color: isDemo ? "#17263A" : "#fff",
            fontFamily: "Manrope, sans-serif",
            fontWeight: 700,
            fontSize: 13,
            padding: "10px 20px",
            borderRadius: 100,
            boxShadow: "0 4px 24px rgba(0,0,0,.18)",
            animation: "fadeIn .3s ease-out",
            whiteSpace: "nowrap",
          }}
        >
          {toast}
        </div>
      )}

      {/* Demo mode pill — always visible when active */}
      {isDemo && (
        <button
          onClick={toggle}
          title="Click or press Space×5 to exit demo mode"
          style={{
            position: "fixed",
            bottom: 16,
            right: 16,
            zIndex: 9998,
            background: "#FFD700",
            color: "#17263A",
            fontFamily: "Manrope, sans-serif",
            fontWeight: 800,
            fontSize: 11,
            padding: "6px 14px",
            borderRadius: 100,
            border: "2px solid #17263A",
            cursor: "pointer",
            letterSpacing: ".06em",
            boxShadow: "2px 2px 0 #17263A",
          }}
        >
          🎭 DEMO MODE
        </button>
      )}
    </DemoContext.Provider>
  );
}
