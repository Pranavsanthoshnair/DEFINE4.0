"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_GROUPS = [
  {
    label: "WORKSPACE",
    items: [
      { href: "/overview",   label: "Overview",          icon: "M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" },
      { href: "/campaigns",  label: "Campaigns",         icon: "M3 11v2a2 2 0 0 0 2 2h2l5 4V5L7 9H5a2 2 0 0 0-2 2zM16 8a5 5 0 0 1 0 8", badge: true },
      { href: "/contacts",   label: "Audience & Contacts", icon: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" },
      { href: "/templates",  label: "Templates",         icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8" },
      { href: "/calls",      label: "Call History",      icon: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.15 12 19.79 19.79 0 0 1 1.07 3.38 2 2 0 0 1 3 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16z" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/analytics",  label: "Analytics & ROI",   icon: "M18 20V10M12 20V4M6 20v-6" },
      { href: "/insights",   label: "Audience Insights", icon: "M12 3a9 9 0 1 0 9 9h-9z" },
    ],
  },
  {
    label: "ORGANISATION",
    items: [
      { href: "/team",       label: "Team & Access",     icon: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" },
      { href: "/settings",   label: "Settings",          icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" },
    ],
  },
];

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Brand Logo & Header — Pinned at top */}
      <Link
        href="/"
        onClick={onNavigate}
        className="flex items-center gap-2.5 mb-5 no-underline select-none px-1 flex-none"
      >
        <img 
          src="/logo.png" 
          alt="Veylo" 
          width={32} 
          height={32} 
          style={{ objectFit: "contain", flex: "none" }} 
          aria-hidden="true" 
        />
        <span style={{ font: "800 19px 'Manrope', sans-serif", letterSpacing: "-.03em", color: "#17263A" }}>
          Vey<b style={{ color: "#EA1D2C", fontWeight: 800 }}>lo</b>
        </span>
      </Link>

      {/* Nav groups — middle scrollable area */}
      <div className="flex-1 overflow-y-auto min-h-0 pr-0.5 space-y-4" style={{ scrollbarWidth: "none" }}>
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="px-3 mb-1.5" style={{ font: "700 10px/1 'Manrope', sans-serif", letterSpacing: ".12em", color: "#8A9BB0" }}>
              {group.label}
            </p>
            {group.items.map((item) => {
              const active = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className="flex items-center gap-3 w-full rounded-xl mb-1 no-underline transition-all duration-150 group"
                  style={{
                    padding: "8px 12px",
                    background: active ? "#17263A" : "transparent",
                    color: active ? "#ffffff" : "#5A6E84",
                    fontWeight: active ? 700 : 500,
                    fontSize: 13,
                    fontFamily: "'Manrope', sans-serif",
                    textDecoration: "none",
                    boxShadow: active ? "0 2px 8px rgba(23,38,58,.18)" : "none",
                  }}
                >
                  <svg
                    viewBox="0 0 24 24" width="17" height="17"
                    fill="none" stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"
                    aria-hidden="true"
                    style={{ flex: "none", color: active ? "#EA1D2C" : "currentColor" }}
                  >
                    <path d={item.icon} />
                  </svg>
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="w-2 h-2 rounded-full bg-[#EA1D2C] flex-none animate-pulse" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Account / Plan widget — Pinned at bottom */}
      <div className="mt-auto pt-3 border-t border-black/5 flex-none">
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl" style={{ background: "rgba(183,216,245,.25)" }}>
          <span
            className="grid place-items-center rounded-full flex-none text-white text-xs font-bold shadow-xs"
            style={{ width: 28, height: 28, background: "#17263A", fontFamily: "Manrope, sans-serif" }}
          >
            VI
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold truncate" style={{ color: "#17263A", fontFamily: "Manrope, sans-serif" }}>Veylo Intelligence</p>
            <p className="text-[11px] font-medium truncate" style={{ color: "#16a34a" }}>● Exotel Carrier Live</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close on route change
  useEffect(() => { setOpen(false); }, [pathname]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const fn = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [open]);

  return (
    <>
      {/* ── Desktop sidebar (lg+) ─────────────────────────────────────── */}
      <aside
        className="hidden lg:flex flex-col select-none"
        style={{
          position: "fixed",
          top: 0,
          bottom: 0,
          left: 0,
          width: 220,
          height: "100vh",
          maxHeight: "100vh",
          zIndex: 40,
          padding: "20px 14px 16px",
          background: "rgba(242,245,248,.95)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderRight: "1px solid rgba(23,38,58,.08)",
          boxSizing: "border-box",
          overflow: "hidden",
        }}
        aria-label="Primary navigation"
      >
        <NavContent />
      </aside>

      {/* ── Mobile top bar ────────────────────────────────────────────── */}
      <div
        className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4 h-14"
        style={{
          background: "rgba(242,245,248,.96)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(23,38,58,.08)",
        }}
      >
        <Link href="/overview" className="flex items-center gap-2 no-underline">
          <img 
            src="/logo.png" 
            alt="Veylo" 
            width={28} 
            height={28} 
            style={{ objectFit: "contain", flex: "none" }} 
            aria-hidden="true" 
          />
          <span style={{ font: "800 17px 'Manrope', sans-serif", letterSpacing: "-.03em", color: "#17263A" }}>
            Vey<b style={{ color: "#EA1D2C", fontWeight: 800 }}>lo</b>
          </span>
        </Link>
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label="Toggle menu"
          className="flex items-center justify-center rounded-lg"
          style={{ width: 36, height: 36, background: "rgba(23,38,58,.06)", border: "1px solid rgba(23,38,58,.08)" }}
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#17263A" strokeWidth="2" strokeLinecap="round">
            {open
              ? <path d="M6 18L18 6M6 6l12 12" />
              : <path d="M3 6h18M3 12h18M3 18h18" />}
          </svg>
        </button>
      </div>

      {/* ── Mobile drawer ─────────────────────────────────────────────── */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0"
            style={{ background: "rgba(10,14,20,.45)", backdropFilter: "blur(2px)" }}
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            className="absolute left-0 top-0 bottom-0 flex flex-col overflow-hidden"
            style={{
              width: 260,
              padding: "20px 14px 16px",
              background: "#F2F5F8",
              boxShadow: "4px 0 24px rgba(23,38,58,.18)",
              animation: "slideInLeft .22s ease-out",
            }}
          >
            <NavContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
