import path from "node:path";
import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

/** Directory containing this config (the Next.js app root). */
const appDir = path.dirname(fileURLToPath(import.meta.url));

// Static export is for `next build` / the production Dockerfile only. Keep it off for
// `next dev` (including Docker Compose) so the dev server behaves normally.
const useStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

/**
 * When `NEXT_PUBLIC_API_URL` is empty, the browser calls same-origin `/api/*` and the
 * dev server rewrites to FastAPI (so CORS is not required for local work).
 * Set `NEXT_PUBLIC_API_URL` (e.g. in Docker) to call the API host directly instead.
 */
const backendOrigin = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  // Repo root also has a package-lock.json; set tracing root so Next does not
  // infer the monorepo parent (see "multiple lockfiles" dev warning).
  outputFileTracingRoot: appDir,
  ...(useStaticExport
    ? {
        output: "export" as const,
        // S3 + CloudFront map URLs like /dashboard/ to object key dashboard/index.html.
        // Without this, Next emits dashboard.html while users request /dashboard (404).
        trailingSlash: true,
      }
    : {}),
  images: {
    unoptimized: true,
  },
  ...(!useStaticExport
    ? {
        // Next dev rewrite proxy defaults to 30s (see next/dist/server/lib/router-utils/proxy-request.js).
        // POST /applications/tailor often exceeds that (LLM chain); without this, the proxy resets (ECONNRESET).
        experimental: {
          proxyTimeout: 120_000,
        },
        async rewrites() {
          if (process.env.NEXT_PUBLIC_API_URL) {
            return [];
          }
          if (process.env.NEXT_DISABLE_API_REWRITE === "1") {
            return [];
          }
          return [
            {
              source: "/api/:path*",
              destination: `${backendOrigin}/api/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
