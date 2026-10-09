import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";

export default function InnerLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
