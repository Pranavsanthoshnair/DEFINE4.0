"use client";

import React, { Suspense, useEffect } from "react";
import { usePathname } from "next/navigation";
import { useReducedMotion } from "@/hooks/useReducedMotion";

function TemplateContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.scrollTo(0, 0);
    }
  }, [pathname]);

  if (reducedMotion) {
    return <>{children}</>;
  }

  return (
    <div
      key={pathname}
      className="page-transition-wrapper w-full"
      style={{
        animation: "pageFadeIn 0.22s cubic-bezier(0.2, 0.8, 0.2, 1) forwards",
      }}
    >
      {children}
    </div>
  );
}

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <TemplateContent>{children}</TemplateContent>
    </Suspense>
  );
}
