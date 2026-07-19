/**
 * GENERATED — DO NOT EDIT.
 *
 * Emitted by scripts/sync_story_simulation_pack.py (via
 * scripts/story_pack_registry.py) from the synced pack artifacts in
 * data/generated/. The literal import() paths are load-bearing: they are
 * how Next emits one optional chunk per signed pack, which is why this
 * registry is a generated source file instead of runtime data.
 * check_story_simulations.py fails if this file drifts from the artifacts.
 */

export const GENERATED_PACKS = [
  {
    id: "sabaody-saga-2d-v1",
    aliases: ["sabaody"],
    firstSceneChapter: 502,
    load: () => import("@/data/generated/story_simulations/sabaody-saga-2d-v1.json"),
  },
  {
    id: "enies-lobby-saga-2d-v1",
    aliases: ["enies-lobby"],
    firstSceneChapter: 387,
    load: () => import("@/data/generated/story_simulations/enies-lobby-saga-2d-v1.json"),
  },
  {
    id: "skypiea-saga-2d-v1",
    aliases: ["skypiea"],
    firstSceneChapter: 279,
    load: () => import("@/data/generated/story_simulations/skypiea-saga-2d-v1.json"),
  },
  {
    id: "arabasta-saga-2d-v1",
    aliases: ["arabasta"],
    firstSceneChapter: 107,
    load: () => import("@/data/generated/story_simulations/arabasta-saga-2d-v1.json"),
  },
  {
    id: "east-blue-saga-2d",
    aliases: ["east-blue"],
    firstSceneChapter: 1,
    load: () => import("@/data/generated/east_blue_simulations.json"),
  },
] as const; // sorted firstSceneChapter DESC — the newest saga owns the globe

export type GeneratedPackId = (typeof GENERATED_PACKS)[number]["id"];
