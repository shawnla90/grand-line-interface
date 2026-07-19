/**
 * lib/breakdowns.ts — chapter breakdown videos, the pure half.
 *
 * Stays free of node:fs so a client component can value-import the types and
 * the gate without dragging the filesystem into the browser bundle. The
 * server-only door is lib/breakdowns-load.ts, same split as scenes/schema.
 *
 * The gate here is deliberately NOT the Uncharted envelope the rest of the
 * atlas uses. Everywhere else, a fogged entity and a nonexistent one must be
 * byte-identical, because a 200 confirming "this exists, you just can't see it"
 * IS the spoiler. A breakdown is different: the video is already public on
 * TikTok and YouTube, so its existence is not a secret worth protecting, and a
 * locked-out reader is better served by "catch up to 1188" than by a page that
 * pretends nothing is there.
 *
 * What that costs us: the locked state admits something notable happens at this
 * chapter. What it must NOT cost us is the content. `lockedView()` returns the
 * chapter number and a PRE-BLURRED poster path and nothing else — no title, no
 * beats, no theory slugs, no video path. Hiding the real poster with CSS would
 * ship the full frame in the payload and make the wall cosmetic.
 */

import { z } from "zod";
import { int, one } from "./entry";

export const Breakdown = z.object({
  chapter: z.number().int().positive(),
  title: z.string().min(1),
  /** the cut itself, served from public/ */
  video_path: z.string().regex(/^\/art\/breakdowns\//),
  poster_path: z.string().regex(/^\/art\/breakdowns\//),
  /** shown INSTEAD of poster_path when locked; must be a separate baked file */
  locked_poster_path: z.string().regex(/^\/art\/breakdowns\//),
  duration_s: z.number().positive(),
  /** one line per beat, for the transcript rail under the player */
  beats: z.array(z.object({ at: z.number().nonnegative(), text: z.string().min(1) })),
  /** slugs in canon/theories.json this cut argues for */
  theory_refs: z.array(z.string()),
  credit: z.object({
    line: z.string().min(1),
    source_ref: z.string().min(1),
  }),
});
export type Breakdown = z.infer<typeof Breakdown>;

export const BreakdownsFile = z.object({ breakdowns: z.array(Breakdown) });

export type BreakdownView =
  | { state: "locked"; chapter: number; locked_poster_path: string }
  | { state: "charted"; data: Breakdown }
  | { state: "none" };

/** Everything a locked reader is allowed to know. Keep this lean on purpose. */
function lockedView(b: Breakdown): BreakdownView {
  return { state: "locked", chapter: b.chapter, locked_poster_path: b.locked_poster_path };
}

/**
 * The reader's stated chapter, UNCLAMPED — for breakdown gating only.
 *
 * Everywhere else the atlas runs ?ch through clampChapter(), which caps it at
 * the world's chapterMax: the horizon its own canon can describe. That is right
 * for the atlas and WRONG here. chapterMax is currently 1185 (derived from the
 * furthest arc/island/join in data/canon.json), so a breakdown of ch. 1188 run
 * through the clamp compares 1185 >= 1188 and can NEVER unlock — the page would
 * be permanently walled no matter what the reader does. Breakdowns cover
 * chapters BEYOND the atlas horizon by design; the manga ships faster than the
 * canon file gets updated.
 *
 * So this reads what the reader actually said. It still fails closed: a missing,
 * malformed, or non-positive ?ch returns 0, which unlocks nothing. ?ep is
 * deliberately not honoured — the episode bridge only spans the clamped range,
 * so it cannot express "I have read past the horizon."
 */
export function readerChapterForBreakdown(sp: {
  [k: string]: string | string[] | undefined;
}): number {
  const ch = int(one(sp.ch));
  return ch !== null && ch > 0 ? ch : 0;
}

/**
 * A breakdown unlocks only once the reader has actually read the chapter it
 * covers. Fails closed: no ?ch means no cut.
 */
export function breakdownAt(
  breakdowns: Breakdown[],
  chapter: number,
  readerChapter: number,
): BreakdownView {
  const b = breakdowns.find((x) => x.chapter === chapter);
  if (!b) return { state: "none" };
  return readerChapter >= b.chapter ? { state: "charted", data: b } : lockedView(b);
}

/** Only the cuts the reader has unlocked, newest first — for an index page. */
export function unlockedBreakdowns(breakdowns: Breakdown[], readerChapter: number): Breakdown[] {
  return breakdowns
    .filter((b) => readerChapter >= b.chapter)
    .sort((a, b) => b.chapter - a.chapter);
}
