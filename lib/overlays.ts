/**
 * lib/overlays.ts — the panel/animation overlay registry. Pure.
 *
 * An overlay is a piece of MEDIA (a colored panel, a fan animation) pinned to
 * an EVENT behind a chapter gate. The registry (canon/overlays.json) is empty
 * by design until drops land through docs/OVERLAY_INTAKE.md — so there is no
 * feature flag: no data, no render, and the first valid drop lights up on its
 * event page with no code change. That is the same "coverage grows by
 * authoring, not by writing code" rule every entry surface keeps.
 *
 * Gating: an overlay only ever renders THROUGH a visible event (the event
 * page already passed eventEntry's gate), plus its own from_chapter — which
 * check_overlays.py pins at >= the event's occurred_chapter, so an overlay
 * can never leak a beat the reader hasn't reached.
 */

import { z } from "zod";

export const OverlayKind = z.enum(["panel", "animation"]);
export type OverlayKind = z.infer<typeof OverlayKind>;

export const Overlay = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/),
  kind: OverlayKind,
  event_slug: z.string().min(1),
  from_chapter: z.number().int().min(1),
  /** Public path, must live under /art/overlays/. The file must exist. */
  media_path: z.string().regex(/^\/art\/overlays\//),
  /** Short display caption. Keep it beat-level, not analysis. */
  title: z.string().min(1),
  credit: z.object({
    source_ref: z.string().min(1),
    license_note: z.string().min(1),
  }),
  canon_confidence: z.enum(["canon", "derived", "guess"]),
  verified: z.boolean(),
});
export type Overlay = z.infer<typeof Overlay>;

/** Empty-by-design is a valid state — no .min(1) here, unlike the other files. */
export const OverlaysFile = z
  .object({ overlays: z.array(Overlay) })
  .and(z.record(z.string(), z.unknown()));
export type OverlaysFile = z.infer<typeof OverlaysFile>;

/** The overlays a visible event may show at this chapter, ascending by gate. */
export function overlaysForEvent(
  overlays: Overlay[],
  eventSlug: string,
  chapter: number,
): Overlay[] {
  return overlays
    .filter((o) => o.event_slug === eventSlug && o.from_chapter <= chapter)
    .sort((a, b) => a.from_chapter - b.from_chapter);
}
