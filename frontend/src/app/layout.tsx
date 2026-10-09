import type { Metadata } from "next";
import "./globals.css";
import MockProvider from "@/components/MockProvider";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
  description:
    "Create, launch, and analyse multilingual outbound calling campaigns powered by AI.",
};


export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">

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
