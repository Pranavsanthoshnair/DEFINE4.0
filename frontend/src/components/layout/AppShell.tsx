import Sidebar from "@/components/layout/Sidebar";

/**
 * AppShell — wraps all authenticated pages.
 * Desktop: fixed 220px sidebar + scrollable main.
 * Mobile:  fixed 56px top bar + full-width main with top padding.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--white, #FFFDF8)" }}>
      {/* Subtle decorative blobs — hidden on mobile to reduce clutter */}
      <div aria-hidden="true" className="hidden lg:block fixed pointer-events-none" style={{ width: 360, height: 360, borderRadius: "50%", background: "rgba(255,215,0,.18)", bottom: -120, left: -80, zIndex: 0 }} />
      <div aria-hidden="true" className="hidden lg:block fixed pointer-events-none" style={{ width: 300, height: 300, borderRadius: "50%", background: "rgba(183,216,245,.28)", top: -80, right: -60, zIndex: 0 }} />

      <Sidebar />

      {/* Main content — offset by sidebar on desktop, top-bar on mobile */}
      <main
        className="relative z-10 lg:ml-[220px] pt-14 lg:pt-0 min-h-screen"
        style={{ padding: "var(--page-pad, 28px) var(--page-pad, 28px)" }}
      >
        {/* Mobile: add top spacing so content isn't under the top bar */}
        <div className="lg:pt-0">
          {children}
        </div>
      </main>
    </div>
  );
}
