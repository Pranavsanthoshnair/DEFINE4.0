import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Veylo — AI Calling Campaign Platform",
  description:
    "Create, launch, and analyse multilingual outbound calling campaigns powered by AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full antialiased">
        {children}
      </body>
    </html>
  );
}
