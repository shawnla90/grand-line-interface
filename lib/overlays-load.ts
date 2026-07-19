/**
 * lib/overlays-load.ts — the server-only door to the overlay registry.
 * Same split, same reason, as the other -load modules.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { OverlaysFile, type Overlay } from "./overlays";

const OVERLAYS_PATH = join(process.cwd(), "canon", "overlays.json");

let cached: Overlay[] | null = null;

/** Validated at read time, module-cached, throws on a malformed file. */
export function loadOverlays(): Overlay[] {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(OVERLAYS_PATH, "utf8"));
  const parsed = OverlaysFile.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `canon/overlays.json failed schema validation:\n${issues}\n\n` +
        `This file is a HAND-AUTHORED registry — fix the row, don't loosen the ` +
        `schema. scripts/check_overlays.py should have caught this first; run it.`,
    );
  }
  cached = parsed.data.overlays;
  return cached;
}
