import type { Metadata } from "next";
import "./globals.css";
import MockProvider from "@/components/MockProvider";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
  description:
    "Create, launch, and analyse multilingual outbound calling campaigns powered by AI.",
};

/**
 * Runs synchronously before first paint to set the data-theme attribute.
 * Prevents a flash of the wrong theme when the user has dark mode stored.
 * Must be a plain string inserted via dangerouslySetInnerHTML — no defer/async.
 */
const themeScript = `
(function(){
  try {
    var t = localStorage.getItem('veylo-theme');
    var dark = window.matchMedia('(prefers-color-scheme:dark)').matches;
    document.documentElement.setAttribute(
      'data-theme',
      (t === 'dark' || t === 'light') ? t : (dark ? 'dark' : 'light')
    );
  } catch(e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <head>
        {/* Anti-flash theme script — must execute before the browser paints */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full antialiased">
        {/*
          MockProvider starts the MSW service worker only when
          NEXT_PUBLIC_USE_MOCKS=true. In production it renders children
          immediately with zero overhead.
        */}
        <MockProvider>
          {children}
        </MockProvider>
      </body>
    </html>
  );
}
