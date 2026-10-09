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
      { href: "/contacts",   label: "Contacts",          icon: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" },
      { href: "/templates",  label: "Templates",         icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8" },
      { href: "/calls",      label: "Call History",      icon: "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.15 12 19.79 19.79 0 0 1 1.07 3.38 2 2 0 0 1 3 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16z" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/analytics",  label: "Analytics",         icon: "M18 20V10M12 20V4M6 20v-6" },
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
    <div className="flex flex-col h-full flex-1 min-h-0">
      {/* Brand */}
      <Link
        href="/"
        onClick={onNavigate}
        className="flex items-center gap-2.5 mb-6 no-underline select-none shrink-0"
      >
        <img 
          src="/logo.png" 
          alt="Veylo" 
          width={44} 
          height={44} 
          style={{ objectFit: "contain", flex: "none" }} 
          aria-hidden="true" 
        />
        <span style={{ font: "800 18px 'Manrope', sans-serif", letterSpacing: "-.03em", color: "#17263A" }}>
          Vey<span style={{ color: "#EA1D2C" }}>lo</span>
        </span>
      </Link>

      {/* Nav groups */}
      <div 
        className="flex-1 overflow-y-auto min-h-0 pr-1 -mr-1"
        style={{ 
          scrollbarWidth: "thin", 
          scrollbarColor: "rgba(23,38,58,.15) transparent",
          scrollBehavior: "smooth",
          WebkitOverflowScrolling: "touch"
        }}
      >
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-1">
            <p className="px-3 mb-1 mt-4 first:mt-0" style={{ font: "700 10px/1 'Manrope', sans-serif", letterSpacing: ".12em", color: "#8A9BB0" }}>
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
                  className="flex items-center gap-3 w-full rounded-xl mb-0.5 no-underline transition-all duration-150 group"
                  style={{
                    padding: "8px 10px",
                    background: active ? "rgba(23,38,58,.08)" : "transparent",
                    color: active ? "#17263A" : "#5A6E84",
                    fontWeight: active ? 700 : 500,
                    fontSize: 14,
                    fontFamily: "'Manrope', sans-serif",
                    textDecoration: "none",
                  }}
                >
                  <svg
                    viewBox="0 0 24 24" width="17" height="17"
                    fill="none" stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round"
                    aria-hidden="true"
                    style={{ flex: "none", color: active ? "#EA1D2C" : undefined }}
                  >
                    <path d={item.icon} />
                  </svg>
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="w-1.5 h-1.5 rounded-full bg-[#EA1D2C] flex-none animate-pulse" />
                  )}
                  {active && (
                    <span className="w-1 h-4 rounded-full bg-[#EA1D2C] flex-none" />
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Account widget */}
      <div className="mt-4 pt-4 border-t border-black/5 shrink-0">
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl" style={{ background: "rgba(183,216,245,.25)" }}>
          <span
            className="grid place-items-center rounded-full flex-none text-white text-xs font-bold"
            style={{ width: 32, height: 32, background: "#17263A", fontFamily: "Manrope, sans-serif" }}
          >
            TS
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold truncate" style={{ color: "#17263A", fontFamily: "Manrope, sans-serif" }}>Tech Summit Org</p>
            <p className="text-xs truncate" style={{ color: "#8A9BB0" }}>Free plan</p>
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
        className="hidden lg:flex flex-col fixed inset-y-0 left-0 z-20"
        style={{
          width: 220,
          height: "100dvh",
          padding: "24px 12px",
          background: "rgba(242,245,248,.92)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderRight: "1px solid rgba(23,38,58,.07)",
        }}
        aria-label="Primary navigation"
      >
        <NavContent />
      </aside>

      {/* ── Mobile top bar ────────────────────────────────────────────── */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4 h-14" style={{ background: "rgba(242,245,248,.95)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", borderBottom: "1px solid rgba(23,38,58,.07)" }}>
        <Link href="/overview" className="flex items-center gap-2 no-underline">
          <svg viewBox="0 0 32 32" fill="none" stroke="#17263A" strokeWidth="2" strokeLinecap="round" width="24" height="24" aria-hidden="true">
            <path d="M9 19a10 10 0 0 1 14 0M5 14a16 16 0 0 1 22 0" />
            <circle cx="16" cy="24" r="3.2" fill="#E10600" stroke="none" />
          </svg>
          <span style={{ font: "800 17px 'Manrope', sans-serif", letterSpacing: "-.03em", color: "#17263A" }}>
            Vey<span style={{ color: "#EA1D2C" }}>lo</span>
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
          {/* Scrim */}
          <div
            className="absolute inset-0"
            style={{ background: "rgba(10,14,20,.45)", backdropFilter: "blur(2px)" }}
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          {/* Panel */}
          <div
            className="absolute left-0 top-0 bottom-0 flex flex-col"
            style={{
              width: 260,
              padding: "20px 14px",
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
