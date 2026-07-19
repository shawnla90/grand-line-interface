/**
 * lib/board-load.ts — the server-only door to the war table.
 * Same split, same reason, as lib/theories-load.ts and lib/scenes-load.ts.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { KeyPlayersFile, type KeyPlayer } from "./board";

const PLAYERS_PATH = join(process.cwd(), "canon", "key_players.json");

let cached: KeyPlayer[] | null = null;

/** Validated at read time, module-cached, throws on a malformed file. */
export function loadKeyPlayers(): KeyPlayer[] {
  if (cached) return cached;
  const raw = JSON.parse(readFileSync(PLAYERS_PATH, "utf8"));
  const parsed = KeyPlayersFile.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((i) => `  ${i.path.join(".")}: ${i.message}`)
      .join("\n");
    throw new Error(
      `canon/key_players.json failed schema validation:\n${issues}\n\n` +
        `This file is HAND-AUTHORED — fix the row, don't loosen the schema. ` +
        `scripts/check_board.py should have caught this first; run it.`,
    );
  }
  cached = parsed.data.players;
  return cached;
}
