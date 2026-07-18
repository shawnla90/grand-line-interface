/**
 * Saga-pack selection for the shared 2.5D simulation host.
 *
 * East Blue keeps its original one-bit flag. New packs use the comma-separated
 * NEXT_PUBLIC_STORY_SIMULATION_PACKS allowlist. Both are build-time values in
 * Next, and an empty allowlist means the generic runtime stays out of the app.
 *
 * The pack roster itself is GENERATED: config/story-packs.generated.ts is
 * emitted by sync_story_simulation_pack.py from the synced artifacts, so a new
 * signed pack reaches this module (ids, aliases, chapter gates, import thunks)
 * with zero hand-written code — the intake is data + env only.
 */

import { EAST_BLUE_2D_ON } from "@/config/east-blue-simulations";
import { GENERATED_PACKS, type GeneratedPackId } from "@/config/story-packs.generated";

export type StoryPackId = GeneratedPackId;

const PACK_ALIASES: Record<string, StoryPackId> = {};
for (const pack of GENERATED_PACKS) {
  PACK_ALIASES[pack.id] = pack.id;
  for (const alias of pack.aliases) PACK_ALIASES[alias] = pack.id;
}

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
  const enabled = GENERATED_PACKS.filter((pack) => ENABLED_STORY_PACKS.has(pack.id));
  const open = enabled.find((pack) => pack.firstSceneChapter <= chapter);
  if (open) return open.id;
  // Before any enabled pack's first scene, load the newest anyway and render
  // nothing until its gate. This keeps pack selection deterministic.
  return enabled[0]?.id ?? null;
}
