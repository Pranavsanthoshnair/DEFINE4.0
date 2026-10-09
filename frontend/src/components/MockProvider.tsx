"use client";

/**
 * MockProvider — conditionally starts the MSW browser service worker.
 *
 * Why this component exists:
 *   MSW's setupWorker() is a browser-only API. Importing it at module level
 *   causes a build error because Next.js evaluates layouts on the server.
 *   We keep all MSW code out of the server bundle by:
 *   1. Marking this file "use client".
 *   2. Only calling the MSW init code inside useEffect (never on the server).
 *   3. Referencing msw via the exact file path so Turbopack's conditional
 *      exports resolver does not resolve the "node" condition to null.
 *
 * NEXT_PUBLIC_USE_MOCKS switch (inlined at build time by Next.js):
 *   "true"  → start MSW service worker; all /api/* requests are intercepted.
 *   other   → render children immediately; requests go to NEXT_PUBLIC_API_BASE_URL.
 */

import { useEffect, useState } from "react";

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export default function MockProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!USE_MOCKS);

  useEffect(() => {
    if (!USE_MOCKS) return;

    // Import handlers first — these are pure TS, safe in both environments.
    import("../../mocks/handlers").then(async ({ handlers }) => {
      // Import the MSW browser bundle via its direct file path.
      // This bypasses the package.json "exports" conditional that maps
      // the "node" condition to null and causes Turbopack to error.
      const { setupWorker } = await import(
        /* webpackIgnore: true */
        "msw/browser"
      );
      const worker = setupWorker(...handlers);
      // MSW 3.x uses `quiet: true` to suppress all unhandled-request warnings.
      // The onUnhandledRequest callback was removed in MSW 3 (StartOptions no longer has it).
      await worker.start({ quiet: true });
      setReady(true);
    }).catch((err) => {
      console.error("[MSW] failed to start:", err);
      setReady(true); // still render; don't block the app
    });
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}
