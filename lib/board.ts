/**
 * lib/board.ts — the war table. Pure: no fs, no fetch, no render.
 *
 * The voyage line answers where the Straw Hats are at a chapter; this module
 * answers where EVERYONE ELSE is — the emperors, admirals and wildcards whose
 * positions are the state of the story. It is the same discipline as the rest
 * of the atlas: a pure function of the chapter, built from hand-authored
 * windows (canon/key_players.json), gated twice per player:
 *
 *   1. the character's debut must have passed — a NAME is a spoiler by itself
 *      (the lib/entry.ts rule, reused not reinvented);
 *   2. the player's first position window must have opened — the board is
 *      endgame-weighted by design, and a player with no authored window yet
 *      has nothing honest to say.
 *
 * A player whose active window has CLOSED (to_chapter passed) stays on the
 * board as "off your chart" — position unknown is an honest state the story
 * itself uses (Law after Winner Island). Players not yet on the board ship as
 * a COUNT, the same bounded leak the iceberg documents in lib/theories.ts.
 */

import { z } from "zod";
import { isIslandFogged, presenceWindowAt, type World, type WorldPresenceWindow } from "./canon";
import type { Canon } from "./schema";

/* -------------------------------------------------------------------------- */
/* schema — strict, hand-authored, fail loud                                  */
/* -------------------------------------------------------------------------- */

export const BoardConfidence = z.enum(["canon", "derived", "guess"]);

export const PositionWindow = z.object({
  from_chapter: z.number().int().min(1),
  to_chapter: z.number().int().min(1).nullable(),
  island_slug: z.string().nullable(),
  label: z.string().min(1),
  source_ref: z.string().min(1),
  canon_confidence: BoardConfidence,
  verified: z.boolean(),
});
export type PositionWindow = z.infer<typeof PositionWindow>;

export const FormWindow = z.object({
  from_chapter: z.number().int().min(1),
  form: z.string().min(1),
  source_ref: z.string().min(1),
  canon_confidence: BoardConfidence,
  verified: z.boolean(),
});
export type FormWindow = z.infer<typeof FormWindow>;

export const KeyPlayer = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/),
  role: z.string().min(1),
  position_timeline: z.array(PositionWindow).min(1),
  form_timeline: z.array(FormWindow),
});
export type KeyPlayer = z.infer<typeof KeyPlayer>;

export const KeyPlayersFile = z
  .object({ players: z.array(KeyPlayer).min(1) })
  .and(z.record(z.string(), z.unknown()));
export type KeyPlayersFile = z.infer<typeof KeyPlayersFile>;

/* -------------------------------------------------------------------------- */
/* derivations                                                                */
/* -------------------------------------------------------------------------- */

export type BoardCard = {
  slug: string;
  /** From canon.characters, debut-gated before it gets here. */
  name: string;
  role: string;
  /**
   * The active position, or null = "off your chart": a window opened and then
   * closed, and nothing has replaced it. Rendered as an honest unknown.
   */
  position: {
    label: string;
    islandSlug: string | null;
    islandName: string | null;
    sinceChapter: number;
    sourceRef: string;
    confidence: z.infer<typeof BoardConfidence>;
  } | null;
  /** The strongest form the reader has SEEN by this chapter, or null. */
  form: { label: string; sinceChapter: number; sourceRef: string } | null;
  verified: boolean;
};

export type BoardState = {
  cards: BoardCard[];
  /** Players whose gates have not both passed. A number, never names. */
  offBoard: number;
};

/** Adapt an authored position window to the shape presenceWindowAt reads.
 *  Only fromChapter/toChapter matter to the resolver; the rest rides along. */
function toResolverWindows(windows: PositionWindow[]): (WorldPresenceWindow & { _src: PositionWindow })[] {
  return windows.map((w, i) => ({
    order: i + 1,
    islandSlug: w.island_slug,
    label: w.label,
    fromChapter: w.from_chapter,
    toChapter: w.to_chapter,
    lng: 0,
    lat: 0,
    verified: w.verified,
    confidence: w.canon_confidence,
    sourceRef: w.source_ref,
    _src: w,
  }));
}

export function boardAtChapter(
  players: KeyPlayer[],
  canon: Canon,
  world: World,
  chapter: number,
): BoardState {
  const cards: BoardCard[] = [];
  let offBoard = 0;

  for (const p of players) {
    const matches = canon.characters.filter((c) => c.slug === p.slug);
    const c = matches.length > 0 ? matches.reduce((a, b) => (a.id <= b.id ? a : b)) : null;
    const debutPassed = c !== null && c.debut_chapter !== null && c.debut_chapter <= chapter;
    const firstWindow = p.position_timeline[0].from_chapter;
    if (!debutPassed || firstWindow > chapter) {
      offBoard += 1;
      continue;
    }

    const active = presenceWindowAt(toResolverWindows(p.position_timeline), chapter);
    let islandName: string | null = null;
    if (active?.islandSlug) {
      const island = world.islands.find((i) => i.slug === active.islandSlug);
      // check_board.py guarantees a window never opens before its island's
      // debut, so an ACTIVE window's island is never fogged. The check here is
      // belt-and-braces: if data and guard ever disagree, leak nothing.
      if (island && !isIslandFogged(island, chapter)) islandName = island.name;
    }

    let form: FormWindow | null = null;
    for (const f of p.form_timeline) {
      if (f.from_chapter <= chapter) form = f;
    }

    cards.push({
      slug: p.slug,
      name: c!.name,
      role: p.role,
      position: active
        ? {
            label: active.label,
            islandSlug: islandName ? active.islandSlug : null,
            islandName,
            sinceChapter: active.fromChapter,
            sourceRef: active.sourceRef,
            confidence: active.confidence,
          }
        : null,
      form: form ? { label: form.form, sinceChapter: form.from_chapter, sourceRef: form.source_ref } : null,
      verified: p.position_timeline.every((w) => w.verified),
    });
  }

  return { cards, offBoard };
}
