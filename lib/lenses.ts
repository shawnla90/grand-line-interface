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

import type {
  FruitType, HakiType, StatusKind, World, WorldFruitReveal, WorldHakiFact,
} from "./canon";
import { statusHoldersAt } from "./canon";
import { affiliationColor, crewColor } from "./crews";

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
  /** Only unrostered presence characters carry one: "Marine", "Warlord", … */
  affiliation?: string | null;
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
 * The master filter: pick one thing and everything else on the presence layer
 * dims to near-invisible. Pure predicate — map orbs, HTML marker pools, the
 * legend and any future renderer all go through it, so they can never disagree
 * about who matches.
 *
 * SINGLE-SELECT on purpose. A set-valued focus ("Emperors AND Logia users")
 * multiplies the URL encoding, the chip state, and the spoiler-audit matrix,
 * while the grammar people actually reach for is "show me just the Red Hair
 * Pirates". If multi-select is ever wanted it is `Focus[]` with OR semantics
 * over this same predicate, and none of the below has to change.
 */
export type Focus =
  | { kind: "crew"; slug: string }
  | { kind: "fruit"; type: FruitType }
  /** Anyone whose fruit the reader has seen — "who has a power at all". */
  | { kind: "fruit-all" }
  | { kind: "haki"; type: HakiType }
  | { kind: "status"; status: StatusKind }
  | { kind: "affiliation"; name: string }
  /** The stones. Matches no PERSON — it isolates the poneglyph layer itself, so
   *  every presence orb dims and the steles are what is left lit. */
  | { kind: "poneglyph" };

/** Stable string for URLs and React keys: focus=status:yonko, focus=crew:red-hair-pirates. */
export function focusKey(f: Focus): string {
  switch (f.kind) {
    case "crew": return `crew:${f.slug}`;
    case "fruit": return `fruit:${f.type}`;
    case "fruit-all": return "fruit:*";
    case "haki": return `haki:${f.type}`;
    case "status": return `status:${f.status}`;
    case "affiliation": return `affiliation:${f.name}`;
    case "poneglyph": return "poneglyph:*";
  }
}

/** Parse a ?focus= param. Unknown/garbage -> null; never throws on a URL. */
export function parseFocus(raw: string | null | undefined): Focus | null {
  if (!raw) return null;
  const i = raw.indexOf(":");
  if (i < 0) return null;
  const kind = raw.slice(0, i);
  const val = raw.slice(i + 1);
  if (!val) return null;
  if (kind === "crew") return { kind: "crew", slug: val };
  if (kind === "fruit") {
    if (val === "*") return { kind: "fruit-all" };
    return FRUIT_TYPE_ORDER.includes(val as FruitType)
      ? { kind: "fruit", type: val as FruitType }
      : null;
  }
  if (kind === "haki") {
    return HAKI_RANK.includes(val as HakiType) ? { kind: "haki", type: val as HakiType } : null;
  }
  if (kind === "status") {
    return STATUS_KINDS.includes(val as StatusKind)
      ? { kind: "status", status: val as StatusKind }
      : null;
  }
  if (kind === "affiliation") return { kind: "affiliation", name: val };
  if (kind === "poneglyph") return { kind: "poneglyph" };
  return null;
}

export const STATUS_KINDS: StatusKind[] = ["yonko", "warlord", "supernova"];

export const STATUS_STYLE: Record<StatusKind, LensInk> = {
  yonko: { color: "#d9a441", label: "Emperors" },
  warlord: { color: "#8c9ab5", label: "Warlords" },
  supernova: { color: "#c2708a", label: "Supernovas" },
};

/**
 * A focus with its holder set already resolved.
 *
 * Status and affiliation are set-membership questions about the WORLD at a
 * chapter, not properties of an entity, so they cannot be answered by a pure
 * per-entity predicate. Resolving once per frame keeps matchesFocus a slug test
 * instead of an O(statuses) scan per orb per paint.
 */
export type ResolvedFocus = { focus: Focus; holders: Set<string> | null };

export function resolveFocus(world: World, focus: Focus, ch: number): ResolvedFocus {
  if (focus.kind === "status") {
    return { focus, holders: statusHoldersAt(world, focus.status, ch) };
  }
  if (focus.kind === "affiliation") {
    const holders = new Set<string>();
    for (const c of world.presence.characters) {
      if (c.affiliation === focus.name) holders.add(c.slug);
    }
    return { focus, holders };
  }
  return { focus, holders: null };
}

export function matchesFocus(
  rf: ResolvedFocus | Focus,
  e: PowerCarrier & { slug?: string },
  ch: number,
): boolean {
  const focus = "kind" in rf ? rf : rf.focus;
  const holders = "kind" in rf ? null : rf.holders;
  // The stones are not people: focusing them dims every presence orb, which is
  // the whole point — "show me the secrets, not the sailors".
  if (focus.kind === "poneglyph") return false;
  if (focus.kind === "crew") return e.crewSlug === focus.slug || e.slug === focus.slug;
  if (focus.kind === "fruit") return revealedFruit(e, ch)?.type === focus.type;
  if (focus.kind === "fruit-all") return revealedFruit(e, ch) !== null;
  if (focus.kind === "haki") {
    // includes, not top-rank: "focus Armament" shows every revealed armament
    // user even when Conqueror outranks it for their orb color
    return revealedHaki(e, ch).some((h) => h.type === focus.type);
  }
  // status / affiliation: a holder set was resolved for this frame. The crew
  // slug counts too, so isolating Emperors at ch. 700 lights up Big Mom's whole
  // crew and not just the flag.
  if (!holders) return false;
  return (!!e.slug && holders.has(e.slug)) || (!!e.crewSlug && holders.has(e.crewSlug));
}

/**
 * One color per entity per lens per chapter — the single dispatch the map and
 * legend share. kind matters only to the crew lens: an unrostered presence
 * character has no crew flag to borrow an ink from, so it falls back to its
 * affiliation — which is what keeps an admiral and a Warlord from reading as
 * the same grey dot in the crowd at Marineford.
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
  if (e.kind === "warlord" && !e.crewSlug) return affiliationColor(e.affiliation);
  return crewColor(e.crewSlug);
}
