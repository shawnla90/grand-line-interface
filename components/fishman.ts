/**
 * components/fishman.ts — the descent. The mirror of skypiea.ts, and built the
 * same way on purpose: pure module, no React, no DOM, every function f(chapter).
 *
 * Skypiea is 10,000 metres UP and Fish-Man Island is 10,000 metres DOWN, and
 * the story treats them as the same joke told twice. So the machinery is
 * identical and only the sign changes:
 *
 *   skypiea.ts             fishman.ts
 *   altitudeT              depthT           0 at the surface, 1 at the bottom
 *   columnOpacity          shimmerOpacity   the Knock-Up Stream / the dive scar
 *   SKY_BASE (below)       DIVE_BASE (above) the sea point the ship left from
 *   transitBase            transitBase
 *   expandSkyWaypoints     expandDiveWaypoints
 *
 * The island's PIN never moves — silhouettes, hit layers, presence anchors and
 * select-easeTo all agree on its derived position. What moves is the ship, and
 * it moves because the virtual waypoints below are spliced into the voyage: the
 * dive IS the existing step-then-lerp interpolation, so a backward scrub
 * re-surfaces for free and the follow-cam needs no special case.
 *
 * Chapter beats (manga): the coated ship submerges off Sabaody around 602, the
 * long fall takes a few chapters, the crew is under for the whole Fish-Man
 * Island arc, and they are shot back to the surface around 651-653 on their way
 * to Punk Hazard. Those last two are DERIVED — verify before content ships.
 */

import type { WorldVoyageWaypoint } from "@/lib/canon";

export const FMI_SLUG = "fish-man-island";
/** The island body — fish-man-island's canonical derived pin. NEVER moves. */
export const FMI_BODY: [number, number] = [-5.9349, -2.8548];
/**
 * Where the coated ship goes under, off Sabaody.
 *
 * Deliberately a hair south of the Sabaody pin rather than on it: the crew
 * dives from the water beside the archipelago, and putting the scar exactly on
 * the island would draw the shimmer through the grove.
 */
export const DIVE_BASE: [number, number] = [-48.2843, 2.9];
/** Where they are shot back up, north-east of the island, bound for Punk Hazard. */
export const SURFACE_BASE: [number, number] = [-3.4, -1.2];

export const DESCENT = { dive: 602, deep: 605, riseStart: 651, surface: 653 } as const;

/**
 * 0 at the surface, 1 at 10,000 metres — the ship's depth as f(chapter).
 *
 * It DWELLS at 1 for the whole arc: Fish-Man Island is at the bottom, so the
 * crew is not "diving" for fifty chapters, they are down there. Only the fall
 * (602-605) and the rise (651-653) interpolate.
 */
export function depthT(ch: number): number {
  if (ch <= DESCENT.dive) return 0;
  if (ch < DESCENT.deep) return (ch - DESCENT.dive) / (DESCENT.deep - DESCENT.dive);
  if (ch <= DESCENT.riseStart) return 1;
  if (ch < DESCENT.surface) return 1 - (ch - DESCENT.riseStart) / (DESCENT.surface - DESCENT.riseStart);
  return 0;
}

/** True only while the ship is falling or rising — the cinematic beats. */
export function inTransit(ch: number): boolean {
  const t = depthT(ch);
  return t > 0 && t < 1;
}

/** The sea point above the ship during a transit (the dive scar, or the rise). */
export function transitBase(ch: number): [number, number] {
  return ch <= DESCENT.riseStart ? DIVE_BASE : SURFACE_BASE;
}

/**
 * The shimmer on the surface where the ship went under — the exact inverse of
 * the Knock-Up Stream. Skypiea's column is the sea reaching UP and is loudest at
 * the eruption; this is the sea closing OVER, so it is loudest at the dive and
 * then settles into a standing scar that says "they are still down there".
 */
export function shimmerOpacity(ch: number): number {
  if (ch < DESCENT.dive) return 0;
  if (ch < DESCENT.deep) return 0.75 * ((ch - DESCENT.dive) / (DESCENT.deep - DESCENT.dive));
  if (ch <= DESCENT.surface) return 0.3;
  return 0.05;
}

/**
 * The voyage with the dive written in: sea -> the dive point off Sabaody ->
 * DOWN to the island -> dwell on the bottom -> back up -> onward.
 *
 * The dive waypoint at 602 also fixes an inaccuracy that predates it: the crew
 * is AT Sabaody from 490 to 602, but the route's next stop was Fish-Man Island
 * at 608, so the lerp had the ship drifting slowly out to sea for a hundred
 * chapters of story that all happens on the archipelago. Now it stays put and
 * then goes under.
 *
 * Map-side only — canon/voyage_legs.json and worldAtChapter never see these.
 */
export function expandDiveWaypoints(waypoints: WorldVoyageWaypoint[]): WorldVoyageWaypoint[] {
  const i = waypoints.findIndex((w) => w.slug === FMI_SLUG);
  if (i === -1) return waypoints;
  const fmi = waypoints[i];
  const virtual = (
    chapter: number, lng: number, lat: number, label: string,
  ): WorldVoyageWaypoint => ({
    order: fmi.order,
    slug: null, // virtual: never a selectable island
    label,
    chapter,
    lng,
    lat,
    verified: false,
    confidence: "derived",
  });
  return [
    ...waypoints.slice(0, i),
    virtual(DESCENT.dive, DIVE_BASE[0], DIVE_BASE[1], "the coated ship dives"),
    { ...fmi, chapter: DESCENT.deep },
    virtual(DESCENT.riseStart, fmi.lng, fmi.lat, "Fish-Man Island — beneath the Red Line"),
    virtual(DESCENT.surface, SURFACE_BASE[0], SURFACE_BASE[1], "surfacing"),
    ...waypoints.slice(i + 1),
  ];
}
