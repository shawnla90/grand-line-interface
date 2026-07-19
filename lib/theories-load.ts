/**
 * lib/theories-load.ts — the server-only door to the iceberg.
 *
 * Split from lib/theories.ts for the same reason lib/scenes-load.ts is split
 * from lib/scenes.ts: this file imports node:fs, and a VALUE import of it from
 * a client component drags node:fs into the browser bundle and fails the build.
 * lib/theories.ts stays pure so anything can import the types and derivations.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { TheoriesFile, type Theory } from "./theories";

const THEORIES_PATH = join(process.cwd(), "canon", "theories.json");

let cached: Theory[] | null = null;

/** Validated at read time, module-cached, throws on a malformed file. */
export function loadTheories(): Theory[] {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(THEORIES_PATH, "utf8"));
  const parsed = TheoriesFile.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `canon/theories.json failed schema validation:\n${issues}\n\n` +
        `This file is HAND-AUTHORED — fix the row, don't loosen the schema. ` +
        `scripts/check_theories.py should have caught this first; run it.`,
    );
  }
  cached = parsed.data.theories;
  return cached;
}
