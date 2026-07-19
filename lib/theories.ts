/**
 * lib/theories.ts — the iceberg, as data. Pure: no fs, no fetch, no render.
 *
 * A theory is the entity the atlas was missing: not what the reader KNOWS at a
 * chapter (islands, bounties, reveals) but what the reader WONDERS. It obeys the
 * same law as everything else — visibility is a pure function of the chapter —
 * with one twist the other entities don't have: a theory's STATUS moves. It can
 * sit open for four hundred chapters and flip to confirmed or debunked on the
 * exact page the reader watches it happen. statusAt() is that flip.
 *
 * ============================================================================
 * THE GATE IS THE TITLE, NOT THE EVIDENCE
 * ============================================================================
 * surfaces_at_chapter is authored BY HAND and is not derivable from the evidence
 * list: a theory's title can spoil harder than its first clue. "Somebody sits on
 * the empty throne" cites ch. 906 imagery, but the title's own noun is safe at
 * 906 and radioactive at 500. The authoring rule (canon/theories.json,
 * _semantics) is that every noun in the title must already be on the page at the
 * surfacing chapter. check_theories.py enforces the half of that a script can:
 * surfaces_at_chapter >= the first evidence chapter, so a theory can never
 * surface with an empty evidence trail.
 *
 * ============================================================================
 * PRE-GATED VIEW-MODELS, THE lib/entry.ts WAY
 * ============================================================================
 * Theories render on PAGES — links somebody sends somebody — so the gate runs on
 * the server and a submerged theory's title never enters the response (see
 * lib/entry.ts for the whole argument; UNCHARTED and Entry<T> are imported from
 * there so a fogged theory is byte-identical to a nonexistent slug, same
 * singleton, no oracle). TheoryVM carries only evidence rows and status windows
 * the reader has reached. The one deliberate, bounded leak is the iceberg's
 * silhouette: icebergAtChapter() reports HOW MANY theories per tier are still
 * submerged — a number, no titles, no slugs, no chapters. That count is a fact
 * about this dataset, not about the story, and it is the entire reason the page
 * works: you can see the mass under the waterline, and you cannot read it.
 */

import { z } from "zod";
import { UNCHARTED, type ChapterCtx, type Entry, charted } from "./entry";
import { isIslandFogged, type World } from "./canon";
import type { Canon } from "./schema";

/* -------------------------------------------------------------------------- */
/* schema — strict, because this file is hand-authored and must fail loud     */
/* -------------------------------------------------------------------------- */

export const TheoryStatus = z.enum(["open", "partly_confirmed", "confirmed", "debunked"]);
export type TheoryStatus = z.infer<typeof TheoryStatus>;

export const TheoryConfidence = z.enum(["canon", "derived", "guess"]);
export type TheoryConfidence = z.infer<typeof TheoryConfidence>;

export const TheoryEvidence = z.object({
  chapter: z.number().int().min(1),
  claim: z.string().min(1),
  source_ref: z.string().min(1),
  canon_confidence: TheoryConfidence,
  verified: z.boolean(),
});
export type TheoryEvidence = z.infer<typeof TheoryEvidence>;

export const TheoryStatusWindow = z.object({
  from_chapter: z.number().int().min(1),
  status: TheoryStatus,
  note: z.string().min(1),
});
export type TheoryStatusWindow = z.infer<typeof TheoryStatusWindow>;

export const TheoryRelated = z.object({
  characters: z.array(z.string()),
  islands: z.array(z.string()),
  poneglyphs: z.array(z.string()),
});

export const Theory = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/),
  title: z.string().min(1),
  tier: z.number().int().min(1).max(5),
  surfaces_at_chapter: z.number().int().min(1),
  question: z.string().min(1),
  evidence: z.array(TheoryEvidence).min(1),
  status_timeline: z.array(TheoryStatusWindow).min(1),
  related: TheoryRelated,
  canon_confidence: TheoryConfidence,
  verified: z.boolean(),
});
export type Theory = z.infer<typeof Theory>;

/** The whole file. Underscore keys are prose for humans; only `theories` is data. */
export const TheoriesFile = z
  .object({ theories: z.array(Theory).min(1) })
  .and(z.record(z.string(), z.unknown()));
export type TheoriesFile = z.infer<typeof TheoriesFile>;

export const TIERS = [1, 2, 3, 4, 5] as const;
export type Tier = (typeof TIERS)[number];

export const TIER_LABEL: Record<Tier, string> = {
  1: "Surface",
  2: "Waterline",
  3: "Submerged",
  4: "Deep",
  5: "Abyss",
};

/* -------------------------------------------------------------------------- */
/* derivations                                                                */
/* -------------------------------------------------------------------------- */

/** The active status window at a chapter: the last whose from_chapter <= ch.
 *  check_theories.py guarantees the first window opens at surfaces_at_chapter
 *  or earlier, so a surfaced theory always has one. */
export function statusAt(t: Theory, chapter: number): TheoryStatusWindow {
  let active = t.status_timeline[0];
  for (const w of t.status_timeline) {
    if (w.from_chapter <= chapter) active = w;
  }
  return active;
}

/**
 * What a theory page (or an iceberg card) is allowed to know at a chapter.
 * Evidence past the bookmark is NOT IN the object — pre-gated, not hidden.
 * Status resolves the same way: a chapter-1030 reader of the fruit theory gets
 * "open", and the "confirmed" window does not exist in their payload until the
 * chapter that flips it. The filter is the same <= ch everywhere.
 */
export type TheoryVM = {
  slug: string;
  title: string;
  tier: Tier;
  question: string;
  surfacedAt: number;
  status: TheoryStatus;
  statusNote: string;
  /** Only rows the reader has reached, ascending by chapter. */
  evidence: TheoryEvidence[];
  related: { characters: string[]; islands: string[]; poneglyphs: string[] };
  confidence: TheoryConfidence;
  verified: boolean;
};

export function theoryVM(t: Theory, chapter: number): TheoryVM {
  const w = statusAt(t, chapter);
  return {
    slug: t.slug,
    title: t.title,
    tier: t.tier as Tier,
    question: t.question,
    surfacedAt: t.surfaces_at_chapter,
    status: w.status,
    statusNote: w.note,
    evidence: t.evidence.filter((e) => e.chapter <= chapter),
    related: t.related,
    confidence: t.canon_confidence,
    verified: t.verified,
  };
}

/** The entry-page gate. Same singleton, same silence, as every other entry. */
export function theoryEntry(
  theories: Theory[],
  slug: string,
  ctx: ChapterCtx,
): Entry<TheoryVM> {
  const t = theories.find((x) => x.slug === slug);
  if (!t) return UNCHARTED;
  if (t.surfaces_at_chapter > ctx.chapter) return UNCHARTED;
  return charted(theoryVM(t, ctx.chapter));
}

/**
 * The whole iceberg at a chapter: per tier, the surfaced theories (full VMs,
 * pre-gated) and the COUNT of what is still down there. The count is the
 * documented leak — see the header — and it is the only field a submerged
 * theory contributes.
 */
export type IcebergTier = {
  tier: Tier;
  label: string;
  surfaced: TheoryVM[];
  submerged: number;
};

export function icebergAtChapter(theories: Theory[], chapter: number): IcebergTier[] {
  return TIERS.map((tier) => {
    const inTier = theories.filter((t) => t.tier === tier);
    const surfaced = inTier
      .filter((t) => t.surfaces_at_chapter <= chapter)
      .sort((a, b) => a.surfaces_at_chapter - b.surfaces_at_chapter)
      .map((t) => theoryVM(t, chapter));
    return {
      tier,
      label: TIER_LABEL[tier],
      surfaced,
      submerged: inTier.length - surfaced.length,
    };
  });
}

/* -------------------------------------------------------------------------- */
/* related entities, resolved at the reader's chapter                          */
/* -------------------------------------------------------------------------- */

/**
 * A related slug carries a NAME the moment it renders, and a name can be a
 * spoiler all by itself. So resolution gates each family by that family's own
 * rule — the same gates the entry pages use, not new ones:
 *   characters: debut_chapter reached (null debut = permanently unresolvable,
 *               the lib/entry.ts rule), duplicate slugs to the lowest id;
 *   islands:    isIslandFogged;
 *   poneglyphs: revealedChapter reached.
 * A slug that does not pass is simply absent — the theory page never says
 * "and one more you can't see", because the count would be the oracle.
 */
export type RelatedResolved = {
  characters: { slug: string; name: string }[];
  islands: { slug: string; name: string }[];
  poneglyphs: { slug: string; name: string }[];
};

export function resolveRelated(
  canon: Canon,
  world: World,
  related: TheoryVM["related"],
  chapter: number,
): RelatedResolved {
  const characters = related.characters.flatMap((slug) => {
    const matches = canon.characters.filter((c) => c.slug === slug);
    if (matches.length === 0) return [];
    const c = matches.reduce((a, b) => (a.id <= b.id ? a : b));
    if (c.debut_chapter === null || c.debut_chapter > chapter) return [];
    return [{ slug, name: c.name }];
  });
  const islands = related.islands.flatMap((slug) => {
    const i = world.islands.find((x) => x.slug === slug);
    if (!i || isIslandFogged(i, chapter)) return [];
    return [{ slug, name: i.name }];
  });
  const poneglyphs = related.poneglyphs.flatMap((slug) => {
    const p = world.poneglyphs.find((x) => x.slug === slug);
    if (!p || p.revealedChapter > chapter) return [];
    return [{ slug, name: p.name }];
  });
  return { characters, islands, poneglyphs };
}
