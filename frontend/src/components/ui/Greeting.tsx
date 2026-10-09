"use client";

/**
 * Renders a time-based greeting client-side to avoid prerender issues
 * with new Date() in Next.js Cache Components mode.
 */
export default function Greeting({ suffix }: { suffix?: string }) {
  const hour = new Date().getHours();
  const word = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  return <>{suffix ? `${word}, ${suffix}` : word}</>;
}
