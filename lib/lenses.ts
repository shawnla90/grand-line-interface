/**
 * lib/lenses.ts — the presence lenses. Facts live in canon/; style lives in
 * code (the same split lib/crews.ts and jolly-roger.ts make). Pure module: no
 * React, no DOM, no fs — safe for the map, the legend, and any future renderer.
 *
 * A lens changes what an entity's orb color MEANS: crew affiliation (the
 * default), the revealed devil fruit's nature, or the highest revealed haki.
 * The revealedFruit/revealedHaki helpers below are the ONLY place the
 * fromChapter <= ch gate for powers is written — map and legend both go
 * through them, so the two can never disagree about what is revealed.
 *
 * Colors are chart inks on the deep-ocean ground (#071324), inside the atlas's
 * muted brass-and-vellum register — and deliberately DISTINCT from every crew
 * ink in lib/crews.ts, because crew flags stay on the map as landmarks under
 * the fruit and haki lenses.
 */

import type { FruitType, HakiType, WorldFruitReveal, WorldHakiFact } from "./canon";
import { crewColor, WARLORD_COLOR } from "./crews";

export type Lens = "crew" | "fruit" | "haki";
/** The map-facing state: "off" hides the presence layer entirely. */
export type PresenceLens = "off" | Lens;

export const PRESENCE_LENSES: PresenceLens[] = ["off", "crew", "fruit", "haki"];

export function isPresenceLens(v: unknown): v is PresenceLens {
  return v === "off" || v === "crew" || v === "fruit" || v === "haki";
}

export type LensInk = { color: string; label: string };

/** Canonical display order for fruit-type chips. */
export const FRUIT_TYPE_ORDER: FruitType[] = [
  "Paramecia", "Zoan", "Ancient Zoan", "Mythical Zoan", "Logia", "SMILE", "Artificial",
];

export const FRUIT_TYPE_STYLE: Record<FruitType, LensInk> = {
  "Paramecia":     { color: "#e0b872", label: "Paramecia" },
  "Zoan":          { color: "#8fae5f", label: "Zoan" },
  "Ancient Zoan":  { color: "#b3865a", label: "Ancient Zoan" },
  "Mythical Zoan": { color: "#b48ad6", label: "Mythical Zoan" },
  "Logia":         { color: "#6fb3d2", label: "Logia" },
  "SMILE":         { color: "#d67f6a", label: "SMILE" },
  "Artificial":    { color: "#9aa7b8", label: "Artificial" },
};

/** Fixed display order — Conqueror outranks Armament outranks Observation. */
export const HAKI_RANK: HakiType[] = ["conqueror", "armament", "observation"];

export const HAKI_STYLE: Record<HakiType, LensInk> = {
  conqueror:   { color: "#d6606f", label: "Conqueror" },
  armament:    { color: "#c8ccd6", label: "Armament" },
  observation: { color: "#79c2b1", label: "Observation" },
};

/** "Unknown" must read as LESS, not other — dimmer than every type ink. */
export const UNREVEALED_COLOR = "#4c5a72";

type PowerCarrier = {
  crewSlug?: string | null;
  fruit: WorldFruitReveal | null;
  haki: WorldHakiFact[];
};

/** The fruit fact, or null while the reader has not reached its reveal. */
export function revealedFruit(e: PowerCarrier, ch: number): WorldFruitReveal | null {
  return e.fruit && e.fruit.fromChapter <= ch ? e.fruit : null;
}

/** The haki facts revealed by this chapter (authored order: ascending fromChapter). */
export function revealedHaki(e: PowerCarrier, ch: number): WorldHakiFact[] {
  return e.haki.filter((h) => h.fromChapter <= ch);
}

/** The highest revealed haki by HAKI_RANK, or null. */
export function topHaki(e: PowerCarrier, ch: number): HakiType | null {
  const have = new Set(revealedHaki(e, ch).map((h) => h.type));
  return HAKI_RANK.find((t) => have.has(t)) ?? null;
}

/**
 * The isolate filter (Phase "identify & filter"): pick one crew, fruit type,
 * or haki type and everything else on the presence layer dims to near-
 * invisible. Pure predicate — map orbs, HTML marker pools, and any future
 * renderer all go through it, so they can never disagree about who matches.
 */
export type Focus =
  | { kind: "crew"; slug: string }
  | { kind: "fruit"; type: FruitType }
  | { kind: "haki"; type: HakiType };

export function matchesFocus(
  focus: Focus,
  e: PowerCarrier & { slug?: string },
  ch: number,
): boolean {
  if (focus.kind === "crew") return e.crewSlug === focus.slug || e.slug === focus.slug;
  if (focus.kind === "fruit") return revealedFruit(e, ch)?.type === focus.type;
  // includes, not top-rank: "focus Armament" shows every revealed armament
  // user even when Conqueror outranks it for their orb color
  return revealedHaki(e, ch).some((h) => h.type === focus.type);
}

/**
 * One color per entity per lens per chapter — the single dispatch the map and
 * legend share. kind matters only to the crew lens (standalone Warlords render
 * in the neutral warlord ink there).
 */
export function lensColor(
  lens: Lens,
  e: PowerCarrier & { kind: "member" | "warlord" },
  ch: number,
): string {
  if (lens === "fruit") {
    const f = revealedFruit(e, ch);
    return f ? FRUIT_TYPE_STYLE[f.type].color : UNREVEALED_COLOR;
  }
  if (lens === "haki") {
    const t = topHaki(e, ch);
    return t ? HAKI_STYLE[t].color : UNREVEALED_COLOR;
  }
  return e.kind === "warlord" ? WARLORD_COLOR : crewColor(e.crewSlug);
}
