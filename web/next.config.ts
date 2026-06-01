import type { NextConfig } from "next";

const BACKEND = "http://127.0.0.1:8002";

const nextConfig: NextConfig = {
  // Prod: FastAPI servíruje build z /app/
  basePath: process.env.NODE_ENV === "production" ? "/app" : "",

  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/health",     destination: `${BACKEND}/health` },
      { source: "/ws/:path*",  destination: `${BACKEND}/ws/:path*` },
    ];
  },
};

export default nextConfig;
