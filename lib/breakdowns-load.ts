/**
 * lib/breakdowns-load.ts — the server-only door to the breakdown registry.
 *
 * Split from lib/breakdowns.ts for the same reason lib/scenes-load.ts is split
 * from lib/scenes.ts: this file imports node:fs, and a VALUE import of it from
 * a client component drags node:fs into the browser bundle and fails the build.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { BreakdownsFile, type Breakdown } from "./breakdowns";

const BREAKDOWNS_PATH = join(process.cwd(), "canon", "breakdowns.json");

let cached: Breakdown[] | null = null;

/** Validated at read time, module-cached, throws loudly on a malformed file. */
export function loadBreakdowns(): Breakdown[] {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(BREAKDOWNS_PATH, "utf8"));
  const parsed = BreakdownsFile.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `canon/breakdowns.json failed schema validation:\n${issues}\n\n` +
        `Fix the row, don't loosen the schema — the regexes on video_path and ` +
        `locked_poster_path are what keep a breakdown from pointing at an ` +
        `arbitrary file, and scripts/check_breakdowns.py asserts the bytes exist.`,
    );
  }
  cached = parsed.data.breakdowns;
  return cached;
}
