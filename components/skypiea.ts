/**
 * components/skypiea.ts — the 2.5D ascent. Pure module: no React, no DOM.
 *
 * Skypiea's PIN never moves — silhouettes, hit layers, presence anchors, and
 * select-easeTo all agree on its derived position, which already sits well
 * NORTH of the sea lane. This module makes that literal: a cloud shadow on
 * the sea at SKY_BASE says "the island above casts this"; the Knock-Up
 * Stream column connects sea to sky; and virtual waypoints make the ship
 * RIDE the column — the ascent is nothing but the voyage's existing
 * step-then-lerp interpolation, so every function here is pure f(chapter)
 * and a backward scrub re-descends for free.
 *
 * Chapter beats (manga): the Knock-Up Stream fires at ~235-237 (the eruption
 * precedes the island's debut at 239 — the column is a sea event, the island
 * name still gates on debut); the crew is aloft through the Skypiea arc; the
 * "octopus balloon" descent lands them back on the sea around 302-304.
 */

import type { WorldVoyageWaypoint } from "@/lib/canon";

export const SKY_SLUG = "skypiea";
/** The island body — skypiea's canonical derived pin. NEVER moves. */
export const SKY_BODY: [number, number] = [-91.1362, 17.0745];
/** Sea-level anchor on the lane where the Knock-Up Stream erupts. */
export const SKY_BASE: [number, number] = [-91.1362, 8.2];
/** Where the octopus balloon sets them back down, east of the stream. */
export const DESCENT_BASE: [number, number] = [-88.6, 7.9];

export const ASCENT = { start: 235, top: 237, dwellEnd: 300, splash: 304 } as const;

/** 0 on the sea, 1 at the sky island — the ship's "altitude" as f(chapter). */
export function altitudeT(ch: number): number {
  if (ch <= ASCENT.start) return 0;
  if (ch < ASCENT.top) return (ch - ASCENT.start) / (ASCENT.top - ASCENT.start);
  if (ch <= ASCENT.dwellEnd) return 1;
  if (ch < ASCENT.splash) return 1 - (ch - ASCENT.dwellEnd) / (ASCENT.splash - ASCENT.dwellEnd);
  return 0;
}

/** True only while the ship is riding up or falling down — the cinematic beats. */
export function inTransit(ch: number): boolean {
  const t = altitudeT(ch);
  return t > 0 && t < 1;
}

/** The sea point under the ship during a transit (ascent base or splash-down). */
export function transitBase(ch: number): [number, number] {
  return ch <= ASCENT.dwellEnd ? SKY_BASE : DESCENT_BASE;
}

/**
 * The Knock-Up Stream's visibility: erupts through the ascent, stays as a
 * faint standing column while the crew is aloft (it IS how they got up
 * there), and settles to a whisper of a trace afterwards.
 */
export function columnOpacity(ch: number): number {
  if (ch < ASCENT.start) return 0;
  if (ch < ASCENT.top) return 0.8 * ((ch - ASCENT.start) / (ASCENT.top - ASCENT.start));
  if (ch <= ASCENT.splash) return 0.35;
  return 0.06;
}

/**
 * The voyage with the ascent written in: virtual waypoints route the ship
 * sea -> stream base -> UP the column -> dwell aloft -> splash down -> onward.
 * Map-side only — canon/voyage_legs.json and worldAtChapter never see these.
 */
export function expandSkyWaypoints(waypoints: WorldVoyageWaypoint[]): WorldVoyageWaypoint[] {
  const i = waypoints.findIndex((w) => w.slug === SKY_SLUG);
  if (i === -1) return waypoints;
  const sky = waypoints[i];
  const virtual = (chapter: number, lng: number, lat: number, label: string): WorldVoyageWaypoint => ({
    order: sky.order,
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
    virtual(ASCENT.start, SKY_BASE[0], SKY_BASE[1], "Knock-Up Stream"),
    { ...sky, chapter: ASCENT.top },
    virtual(ASCENT.dwellEnd, sky.lng, sky.lat, "Skypiea — aloft"),
    virtual(ASCENT.splash, DESCENT_BASE[0], DESCENT_BASE[1], "splash-down"),
    ...waypoints.slice(i + 1),
  ];
}
