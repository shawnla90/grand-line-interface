/**
 * lib/fruits.ts — the devil fruit codex. Pure: no fs, no fetch, no render.
 *
 * The index derivation walks the SAME carrier scan as fruitEntry in
 * lib/entry.ts — presence rosters, never characters[].fruit_id — because that
 * file already litigated why: the raw join is a chapter-1044 spoiler sitting
 * on a chapter-1 character. A fruit exists here once anyone's authored reveal
 * exists, and is KNOWN to the reader once the earliest reveal chapter passes.
 * Only 35 of 213 fruits are chartable; coverage grows by authoring reveals
 * (canon/fruit_reveals.json), not by writing code.
 *
 * Lineage (canon/fruit_lineage.json) is the new layer: where a fruit has BEEN
 * — inheritances, thefts, prizes, the rules of its nature — as chapter-gated
 * events hanging off a fruit that must already be chartable. A lineage for a
 * fruit the reader hasn't met is not in the payload at all.
 */

import { z } from "zod";
import type { World } from "./canon";

/* -------------------------------------------------------------------------- */
/* lineage schema — strict, hand-authored, fail loud                          */
/* -------------------------------------------------------------------------- */

export const LineageKind = z.enum(["revealed", "inherited", "taken", "staked", "lore"]);
export type LineageKind = z.infer<typeof LineageKind>;

export const LineageEvent = z.object({
  chapter: z.number().int().min(1),
  kind: LineageKind,
  note: z.string().min(1),
  source_ref: z.string().min(1),
  canon_confidence: z.enum(["canon", "derived", "guess"]),
  verified: z.boolean(),
});
export type LineageEvent = z.infer<typeof LineageEvent>;

export const FruitLineage = z.object({
  fruit_slug: z.string().regex(/^[a-z0-9-]+$/),
  events: z.array(LineageEvent).min(1),
});
export type FruitLineage = z.infer<typeof FruitLineage>;

export const FruitLineageFile = z
  .object({ lineages: z.array(FruitLineage).min(1) })
  .and(z.record(z.string(), z.unknown()));
export type FruitLineageFile = z.infer<typeof FruitLineageFile>;

/* -------------------------------------------------------------------------- */
/* the index                                                                  */
/* -------------------------------------------------------------------------- */

export type FruitIndexRow = {
  slug: string;
  name: string;
  type: string;
  /** The earliest authored reveal — when the fruit became a fact for the reader. */
  firstKnown: number;
  /** Holders whose OWN reveal has passed, ascending. The fruitEntry rule. */
  users: { slug: string; name: string; fromChapter: number }[];
  /** Lineage events the reader has reached, ascending. Empty = no chain authored. */
  lineage: LineageEvent[];
};

export type FruitCodex = {
  revealed: FruitIndexRow[];
  /** Chartable fruits the reader hasn't met. A number, never names —
   *  the same bounded leak lib/theories.ts documents. */
  hidden: number;
};

export function fruitCodexAtChapter(
  world: World,
  lineages: FruitLineage[],
  chapter: number,
): FruitCodex {
  const carriers = [
    ...world.presence.crews.flatMap((c) =>
      c.members.map((m) => ({ slug: m.slug, name: m.name, fruit: m.fruit })),
    ),
    ...world.presence.characters.map((c) => ({ slug: c.slug, name: c.name, fruit: c.fruit })),
  ];

  const byFruit = new Map<
    string,
    { name: string; type: string; firstKnown: number; users: FruitIndexRow["users"] }
  >();
  for (const e of carriers) {
    if (!e.fruit) continue;
    const cur = byFruit.get(e.fruit.slug);
    if (!cur) {
      byFruit.set(e.fruit.slug, {
        name: e.fruit.name,
        type: e.fruit.type,
        firstKnown: e.fruit.fromChapter,
        users: [],
      });
    } else if (e.fruit.fromChapter < cur.firstKnown) {
      cur.firstKnown = e.fruit.fromChapter;
    }
    if (e.fruit.fromChapter <= chapter) {
      byFruit.get(e.fruit.slug)!.users.push({
        slug: e.slug,
        name: e.name,
        fromChapter: e.fruit.fromChapter,
      });
    }
  }

  const lineageBySlug = new Map(lineages.map((l) => [l.fruit_slug, l.events]));
  const revealed: FruitIndexRow[] = [];
  let hidden = 0;
  for (const [slug, f] of byFruit) {
    if (f.firstKnown > chapter) {
      hidden += 1;
      continue;
    }
    revealed.push({
      slug,
      name: f.name,
      type: f.type,
      firstKnown: f.firstKnown,
      users: f.users.sort((a, b) => a.fromChapter - b.fromChapter),
      lineage: (lineageBySlug.get(slug) ?? []).filter((e) => e.chapter <= chapter),
    });
  }
  revealed.sort((a, b) => a.firstKnown - b.firstKnown);
  return { revealed, hidden };
}
