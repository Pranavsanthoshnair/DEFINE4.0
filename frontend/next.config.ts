import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Clean config — experimental flags removed for Vercel compatibility
  reactStrictMode: true,
  images: {
    unoptimized: false,
  },
};

export default nextConfig;
