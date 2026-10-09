// This layout is a passthrough — the redirect in page.tsx fires before any rendering.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
