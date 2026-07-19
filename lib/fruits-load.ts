/**
 * lib/fruits-load.ts — the server-only door to the fruit lineages.
 * Same split, same reason, as lib/theories-load.ts and lib/board-load.ts.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { FruitLineageFile, type FruitLineage } from "./fruits";

const LINEAGE_PATH = join(process.cwd(), "canon", "fruit_lineage.json");

let cached: FruitLineage[] | null = null;

/** Validated at read time, module-cached, throws on a malformed file. */
export function loadFruitLineages(): FruitLineage[] {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(LINEAGE_PATH, "utf8"));
  const parsed = FruitLineageFile.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `canon/fruit_lineage.json failed schema validation:\n${issues}\n\n` +
        `This file is HAND-AUTHORED — fix the row, don't loosen the schema. ` +
        `scripts/check_fruit_lineage.py should have caught this first; run it.`,
    );
  }
  cached = parsed.data.lineages;
  return cached;
}
