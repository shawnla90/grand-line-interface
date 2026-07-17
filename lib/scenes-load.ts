/**
 * lib/scenes-load.ts — the server-only door to the scene registry.
 *
 * Split from lib/scenes.ts for exactly the reason lib/schema.ts is split from
 * lib/canon.ts: this file imports node:fs, and a VALUE import of it from a
 * client component drags node:fs into the browser bundle and fails the build.
 * lib/scenes.ts stays pure so anything can import the types and the resolver.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { NarrativeScenes, type NarrativeScenes as Scenes } from "./scenes";

const SCENES_PATH = join(process.cwd(), "data", "generated", "narrative_scenes.json");

let cached: Scenes | null = null;

/** Validated at read time, module-cached, throws on a malformed artifact. */
export function loadScenes(): Scenes {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(SCENES_PATH, "utf8"));
  const parsed = NarrativeScenes.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `data/generated/narrative_scenes.json failed schema validation:\n${issues}\n\n` +
        `Do not "fix" this in the app. Re-run scripts/sync_scenes.py, or fix the contract ` +
        `in the asset track — this artifact is derived, not authored.`,
    );
  }
  cached = parsed.data;
  return cached;
}
