import Sidebar from "@/components/layout/Sidebar";

/**
 * Shared shell for all authenticated/inner pages.
 * Provides the sidebar rail, decorative blobs, and main content area.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Fixed decorative background blobs */}
      <div className="blob blob-1" aria-hidden="true" />
      <div className="blob blob-2" aria-hidden="true" />

      <Sidebar />

      <main
        className="flex-1 overflow-auto"
        style={{ padding: "var(--gap)", position: "relative", zIndex: 1 }}
      >
        {children}
      </main>
    </div>
  );
}
