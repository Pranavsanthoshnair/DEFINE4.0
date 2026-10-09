"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useReducedMotion } from "@/hooks/useReducedMotion";

const NAV_GROUPS = [
  {
    label: "WORKSPACE",
    items: [
      { href: "/overview", label: "Overview", icon: "M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" },
      { href: "/campaigns", label: "Campaigns", icon: "M3 11v2a2 2 0 0 0 2 2h2l5 4V5L7 9H5a2 2 0 0 0-2 2zM16 8a5 5 0 0 1 0 8", hasActivePulse: true },
      { href: "/contacts", label: "Contacts", icon: "M2.5 20a6.5 6.5 0 0 1 13 0M17 4.5a3.5 3.5 0 0 1 0 7M21.5 20a6 6 0 0 0-4-5.6M9 4.5a3.5 3.5 0 1 0 0 7" },
      { href: "/templates", label: "Templates", icon: "M3 5h18v14H3zM3 10h18M9 10v9" },
      { href: "/calls", label: "Call History", icon: "M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/analytics", label: "Analytics", icon: "M4 20V10M10 20V4M16 20v-7M22 20H2" },
      { href: "/insights", label: "Audience Insights", icon: "M12 3a9 9 0 1 0 9 9h-9z" },
    ],
  },
  {
    label: "ORGANISATION",
    items: [
      { href: "/team", label: "Team & Permissions", icon: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" },
      { href: "/settings", label: "Settings", icon: "M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const reducedMotion = useReducedMotion();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Handle Escape key to close mobile drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileOpen) {
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileOpen]);

  const navContent = (
    <div className="flex flex-col h-full">
      {/* Brand Logo */}
      <Link
        href="/"
        className="flex items-center gap-2 mb-5 no-underline"
        style={{ textDecoration: "none" }}
        aria-label="Veylo home"
      >
        <svg viewBox="0 0 32 32" fill="none" stroke="#17263A" strokeWidth="2" strokeLinecap="round" width="30" height="30" aria-hidden="true" style={{ flex: "none" }}>
          <path d="M9 19a10 10 0 0 1 14 0M5 14a16 16 0 0 1 22 0"/>
          <circle cx="16" cy="24" r="3.2" fill="#E10600" stroke="none"/>
          <circle cx="5" cy="14" r="2" fill="#FFD700"/>
          <circle cx="27" cy="14" r="2" fill="#FFD700"/>
          <circle cx="16" cy="6" r="2" fill="#FFD700"/>
        </svg>
        <span style={{ font: "800 19px 'Manrope'", letterSpacing: "-.03em" }}>
          Vey<b style={{ color: "var(--red)", fontWeight: 800 }}>lo</b>
        </span>
      </Link>

      {/* Nav Groups */}
      <div className="flex-1 overflow-y-auto pr-1">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-3">
            <p
              className="select-none"
              style={{
                font: "700 10px 'Manrope'",
                letterSpacing: ".14em",
                color: "#6A7A8C",
                margin: "16px 10px 6px 34px",
              }}
            >
              {group.label}
            </p>

            <nav className="relative" aria-label={group.label.toLowerCase()}>
              {/* Vertical signal track line inside group */}
              <span
                aria-hidden="true"
                style={{
                  position: "absolute",
                  left: 14,
                  top: 0,
                  bottom: 0,
                  width: 2,
                  background: "var(--blue)",
                }}
              />

              {group.items.map((item) => {
                const active = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className="group flex items-center gap-3 relative"
                    style={{
                      margin: "0 0 2px 28px",
                      padding: "9px 10px",
                      borderRadius: 0,
                      textDecoration: "none",
                      font: "600 14px 'Manrope'",
                      color: active ? "var(--ink)" : "#4A5B6E",
                      background: active ? "var(--white)" : "transparent",
                      boxShadow: active ? "inset 0 0 0 1px rgba(23,38,58,.1)" : "none",
                      transition: ".2s",
                    }}
                  >
                    {/* Active Track Signal Dot */}
                    {active && (
                      <span
                        aria-hidden="true"
                        style={{
                          position: "absolute",
                          left: -17,
                          top: "50%",
                          marginTop: -4,
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: "var(--red)",
                        }}
                      >
                        {!reducedMotion && (
                          <span
                            className="absolute -inset-1 rounded-full border border-[var(--red)] pointer-events-none"
                            style={{
                              animation: "pulseRing 2s cubic-bezier(0, 0, 0.2, 1) infinite",
                            }}
                          />
                        )}
                      </span>
                    )}

                    {/* SVG Icon */}
                    <svg
                      viewBox="0 0 24 24"
                      width="19"
                      height="19"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.7"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{ flex: "none" }}
                      className={`transition-all duration-200 ${
                        active ? "text-[var(--red)]" : "group-hover:-translate-x-1 group-hover:text-[var(--red)]"
                      }`}
                      aria-hidden="true"
                    >
                      <path d={item.icon} />
                    </svg>

                    <span>{item.label}</span>

                    {/* Running Campaign Pulsing Red Dot */}
                    {item.hasActivePulse && (
                      <span className="relative flex h-2 w-2 ml-auto">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--red)] opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--red)]" />
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Account Widget */}
      <div className="mt-auto pt-3">
        <div
          className="flex items-center gap-2"
          style={{
            padding: 10,
            borderRadius: 12,
            background: "rgba(183,216,245,.3)",
            font: "600 13px/1.3 'Manrope'",
          }}
        >
          <span
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: "var(--ink)",
              color: "var(--white)",
              display: "grid",
              placeItems: "center",
              fontSize: 12,
              flex: "none",
            }}
          >
            TS
          </span>
          <span>Tech Summit Org</span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar Rail */}
      <aside
        className="fixed inset-y-0 left-0 z-20 hidden lg:flex flex-col overflow-y-auto"
        style={{
          width: 224,
          padding: "26px 16px",
          backdropFilter: "blur(20px) saturate(1.5)",
          WebkitBackdropFilter: "blur(20px) saturate(1.5)",
          background: "rgba(183,216,245,.34)",
          boxShadow: "inset -1px 0 0 rgba(255,255,255,.7), 24px 0 50px -42px rgba(23,38,58,.6)",
        }}
        aria-label="Primary navigation"
      >
        {navContent}
      </aside>

      {/* Mobile Bar Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4 py-3 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <Link href="/" className="font-extrabold text-lg tracking-tight no-underline">
          Vey<b className="text-[var(--red)]">lo</b>
        </Link>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-expanded={mobileOpen}
          aria-label="Toggle Navigation Drawer"
          className="p-2 rounded-lg bg-slate-100 border border-slate-200 text-slate-800 focus:outline-none"
        >
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
            {mobileOpen ? (
              <path strokeLinecap="round" d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Drawer & Scrim */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity duration-300"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div
            className="relative w-64 max-w-[80vw] bg-white h-full p-6 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out"
            style={{
              animation: reducedMotion ? "none" : "drawerSlideIn 0.3s ease-out forwards",
            }}
          >
            {navContent}
          </div>
        </div>
      )}

      {/* Desktop Layout Spacer */}
      <div className="hidden lg:block flex-none" style={{ width: 224 }} aria-hidden="true" />
    </>
  );
}
