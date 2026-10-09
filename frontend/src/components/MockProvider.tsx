"use client";

/**
 * MockProvider — conditionally starts the MSW browser service worker.
 *
 * NEXT_PUBLIC_USE_MOCKS=true  → start MSW; all /api/* requests intercepted.
 * NEXT_PUBLIC_USE_MOCKS other → unregister any stale MSW worker, then render.
 *
 * The "Failed to convert value to 'Response'" error happens when a stale
 * mockServiceWorker.js is still registered from a previous dev session.
 * We actively unregister it on every load when mocks are disabled.
 */

import { useEffect, useState } from "react";

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export default function MockProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!USE_MOCKS);

  useEffect(() => {
    if (USE_MOCKS) {
      // Start MSW worker
      import("../../mocks/handlers")
        .then(async ({ handlers }) => {
          const { setupWorker } = await import("msw/browser");
          const worker = setupWorker(...handlers);
          await worker.start({ quiet: true });
          setReady(true);
        })
        .catch((err) => {
          console.error("[MSW] failed to start:", err);
          setReady(true);
        });
    } else {
      // Unregister any stale MSW service workers from previous sessions
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.getRegistrations().then((registrations) => {
          for (const reg of registrations) {
            // Only remove MSW worker (mockServiceWorker.js), not others
            if (reg.active?.scriptURL?.includes("mockServiceWorker")) {
              reg.unregister();
              console.info("[MockProvider] Unregistered stale MSW service worker.");
            }
          }
        });
      }
      setReady(true);
    }
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}
