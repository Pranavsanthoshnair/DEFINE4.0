import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function InnerLayout({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense>
        <AppShell>{children}</AppShell>
      </Suspense>
    </ErrorBoundary>
  );
}
