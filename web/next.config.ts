import type { NextConfig } from "next";

const BACKEND = "http://127.0.0.1:8002";
const IS_PROD = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Prod: FastAPI servíruje build z /app/
  basePath: IS_PROD ? "/app" : "",

  // Static export for `web_dist/` (served by FastAPI on `/app`).
  output: "export",
  images: { unoptimized: true },
};

// Dev convenience: proxy API/WS to the Python backend.
// Note: rewrites are not applied for static export, so we omit them in prod
// to avoid confusing warnings during `next build`.
if (!IS_PROD) {
  nextConfig.rewrites = async () => ([
    { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
    { source: "/health",     destination: `${BACKEND}/health` },
    { source: "/ws/:path*",  destination: `${BACKEND}/ws/:path*` },
  ]);
}

export default nextConfig;
