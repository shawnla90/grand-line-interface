/**
 * Saga-pack selection for the shared 2.5D simulation host.
 *
 * East Blue keeps its original one-bit flag. New packs use the comma-separated
 * NEXT_PUBLIC_STORY_SIMULATION_PACKS allowlist. Both are build-time values in
 * Next, and an empty allowlist means the generic runtime stays out of the app.
 */

import { EAST_BLUE_2D_ON } from "@/config/east-blue-simulations";

export type StoryPackId = "east-blue-saga-2d" | "arabasta-saga-2d-v1";

const PACK_ALIASES: Record<string, StoryPackId> = {
  "east-blue": "east-blue-saga-2d",
  "east-blue-saga-2d": "east-blue-saga-2d",
  arabasta: "arabasta-saga-2d-v1",
  "arabasta-saga-2d-v1": "arabasta-saga-2d-v1",
};

// Direct property access is intentional: Next can inline this public variable.
const RAW_PACKS = process.env.NEXT_PUBLIC_STORY_SIMULATION_PACKS ?? "";

export const ENABLED_STORY_PACKS = new Set<StoryPackId>(
  RAW_PACKS.split(",")
    .map((value) => PACK_ALIASES[value.trim().toLowerCase()])
    .filter((value): value is StoryPackId => Boolean(value)),
);

if (EAST_BLUE_2D_ON) ENABLED_STORY_PACKS.add("east-blue-saga-2d");

export const ANY_STORY_SIMULATIONS_ON = ENABLED_STORY_PACKS.size > 0;

export function storyPackFromAlias(value: string | null | undefined): StoryPackId | null {
  if (!value) return null;
  return PACK_ALIASES[value.trim().toLowerCase()] ?? null;
}

/** The newest enabled saga owns the globe once its first verified scene opens. */
export function selectStoryPack(chapter: number, forced?: StoryPackId): StoryPackId | null {
  if (forced) return forced;
  if (ENABLED_STORY_PACKS.has("arabasta-saga-2d-v1") && chapter >= 107) {
    return "arabasta-saga-2d-v1";
  }
  if (ENABLED_STORY_PACKS.has("east-blue-saga-2d")) return "east-blue-saga-2d";
  // If Arabasta is the only enabled pack, load it early but render nothing
  // until the chapter-107 gate. This keeps pack selection deterministic.
  if (ENABLED_STORY_PACKS.has("arabasta-saga-2d-v1")) return "arabasta-saga-2d-v1";
  return null;
}
