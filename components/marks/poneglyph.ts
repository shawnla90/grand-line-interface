/**
 * components/marks/poneglyph.ts — the stele mark.
 *
 * A cube of indestructible stone with the Void Century cut into it. Drawn as a
 * squat rectangle with a chamfered top and three scratch-lines of "text", in
 * inks nothing else on this chart uses: everything else here is brass, straw,
 * or a crew's colour, so the stones read as a category rather than a faction.
 *
 * TWO INKS, BECAUSE THE STORY SAYS SO. Road Poneglyphs are RED on the page —
 * that is how the story talks about them ("the red poneglyphs") and how a
 * reader who has met one recognizes the next. So `road` carries an aged
 * crimson and every other kind keeps the cube-blue. The colour is itself
 * chapter-gated by the layer above: a stone only renders after its
 * revealed_chapter, so the red never appears before the reader has been shown
 * a red stone.
 *
 * Pure module — a string of SVG, no React, no DOM. The map pools these into
 * HTML markers the same way it pools flags and portraits.
 */

import type { PoneglyphKind } from "@/lib/canon";

/** The cube-blue every non-Road stone wears. Kept under its old name — it is
 *  also the category ink (the legend chip counts stones of every kind). */
export const PONEGLYPH_INK = "#5f7d9c";
/** The aged crimson of the four stones that triangulate Laugh Tale. */
export const ROAD_PONEGLYPH_INK = "#a12a33";
export const PONEGLYPH_GLYPH = "#0d1a26";

/** The ONE place kind→ink is written; mark, glint and tooltip all come through
 *  here so they cannot disagree about what a red stone is. */
export function poneglyphInk(kind: PoneglyphKind): string {
  return kind === "road" ? ROAD_PONEGLYPH_INK : PONEGLYPH_INK;
}

export function poneglyphSvg(size = 18, kind: PoneglyphKind = "historical"): string {
  const ink = poneglyphInk(kind);
  const w = size;
  const h = Math.round(size * 1.16);
  return `<svg width="${w}" height="${h}" viewBox="0 0 18 21" fill="none" aria-hidden="true">
  <path d="M3.2 5.4 5.6 2.4h6.8l2.4 3v13.2H3.2z" fill="${ink}" stroke="#0a121c" stroke-width=".8" stroke-linejoin="round"/>
  <path d="M3.2 5.4h11.6" stroke="#0a121c" stroke-width=".7" opacity=".55"/>
  <g stroke="${PONEGLYPH_GLYPH}" stroke-width="1" opacity=".62" stroke-linecap="round">
    <path d="M5.4 8.6h7.2"/><path d="M5.4 11.4h4.6"/><path d="M5.4 14.2h6.2"/>
  </g>
</svg>`;
}
