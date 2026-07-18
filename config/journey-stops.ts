/**
 * config/journey-stops.ts — everything the cinematic journey stops for.
 *
 * Two families, one mechanism (the JourneyMoment dwell):
 *   - SCENE stops: 2.5D story simulations (built from world.events by
 *     config/east-blue-simulations.ts; ride the EAST_BLUE_2D flag).
 *   - MODEL spotlights: 3D models whose anchors the voyage line never
 *     touches, so the waypoint-keyed deep list structurally cannot visit
 *     them — Marineford has existed on this chart since the world-government
 *     triangle shipped, and the journey simply never looked at it. These ride
 *     the RUNTIME_3D flag and use the directory-dive camera with orbit.
 *
 * Chapters are chosen so every component the camera sees is already revealed
 * (the GLB's own node gates keep withholding the rest): Enies Lobby reveals
 * ch358 and the Gates ch376, so the ch430 visit shows the judicial island era;
 * Impel Down (525) and the tarai current (522) complete the triangle by the
 * ch552 war visit. Spoiler math is enforced by scripts/audit_journey.py.
 */

import type { JourneyMoment } from "@/lib/journey";
import { EAST_BLUE_2D_ON, buildEastBlueMoments } from "@/config/east-blue-simulations";

const RUNTIME_3D_ON = process.env.NEXT_PUBLIC_RUNTIME_3D_ASSETS === "1";

/** True when the journey carries story/model stops at all — the 150s cut. */
export const STORY_JOURNEY_ON = EAST_BLUE_2D_ON || RUNTIME_3D_ON;

/** Anchors come from data/generated/runtime_assets.json (the models' own
 * declared positions) — hand-carried here because this file must stay tiny
 * and the artifact is 60KB. If a model's anchor moves, move it here too. */
const MODEL_SPOTLIGHTS: JourneyMoment[] = [
  { chapter: 105, kind: "model", label: "Whisky Peak", fact: "The first Grand Line welcome — too warm to be true.", focus: [-121.5765, -5.8639] },
  { chapter: 430, kind: "model", label: "Enies Lobby & the Gates of Justice", fact: "The judicial island, where the world's law meets the sea.", focus: [-92.4053, 11.8445] },
  { chapter: 490, kind: "model", label: "Mary Geoise — the Red Line's summit", fact: "The holy land above the world, where the Celestial Dragons rule.", focus: [-2.7363, -9.3782] },
  { chapter: 516, kind: "model", label: "Amazon Lily", fact: "Kuja island — the empress's home sea.", focus: [165.1452, 12.0706] },
  { chapter: 552, kind: "model", label: "Marineford", fact: "The Navy's fortress, where the war for the era was fought.", focus: [-92.4053, 11.8445] },
];

/** All the stops the journey should make, in the world the reader has. */
export function buildJourneyStops(world: Parameters<typeof buildEastBlueMoments>[0]): JourneyMoment[] {
  const stops: JourneyMoment[] = [];
  if (EAST_BLUE_2D_ON) stops.push(...buildEastBlueMoments(world).map((m) => ({ ...m, kind: "scene" as const })));
  if (RUNTIME_3D_ON) stops.push(...MODEL_SPOTLIGHTS);
  return stops.sort((a, b) => a.chapter - b.chapter);
}
