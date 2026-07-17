import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

/**
 * Pin the Turbopack root to THIS project.
 *
 * Without it, Next walks up looking for a lockfile, finds one in the home
 * directory (~/package-lock.json), and infers the workspace root as
 * /Users/shawnos.ai — so it resolves modules against and filesystem-watches the
 * entire home folder. Turbopack scopes module resolution to the root ("files
 * outside of the project root are not resolved"), so an over-broad root is both a
 * performance problem and a correctness hazard.
 */
const nextConfig: NextConfig = {
  turbopack: {
    root: dirname(fileURLToPath(import.meta.url)),
  },

  /**
   * The OG route reads its fonts with join(process.cwd(), "assets", "fonts") at
   * runtime. File tracing follows imports, not runtime path joins, so without
   * this the standalone output ships the route and not the bytes it needs — and
   * the failure is a broken share card in production, which nothing local
   * reproduces.
   */
  outputFileTracingIncludes: {
    "/api/og/[family]/[slug]": ["./assets/fonts/**"],
  },
};

export default nextConfig;
