import type { Metadata } from "next";
import "./globals.css";
import MockProvider from "@/components/MockProvider";
import { DemoModeProvider } from "@/context/DemoModeContext";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
  description:
    "Create, launch, and analyse multilingual outbound calling campaigns powered by AI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body className="min-h-full antialiased">
        <MockProvider>
          <DemoModeProvider>
            {children}
          </DemoModeProvider>
        </MockProvider>
      </body>
    </html>
  );
}
