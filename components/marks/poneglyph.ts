/**
 * components/marks/poneglyph.ts — the stele mark.
 *
 * A cube of indestructible stone with the Void Century cut into it. Drawn as a
 * squat rectangle with a chamfered top and three scratch-lines of "text", in the
 * one ink nothing else on this chart uses: everything else here is brass, straw,
 * or a crew's colour, so the stones read as a category rather than a faction.
 *
 * Pure module — a string of SVG, no React, no DOM. The map pools these into
 * HTML markers the same way it pools flags and portraits.
 */

export const PONEGLYPH_INK = "#5f7d9c";
export const PONEGLYPH_GLYPH = "#0d1a26";

export function poneglyphSvg(size = 18): string {
  const w = size;
  const h = Math.round(size * 1.16);
  return `<svg width="${w}" height="${h}" viewBox="0 0 18 21" fill="none" aria-hidden="true">
  <path d="M3.2 5.4 5.6 2.4h6.8l2.4 3v13.2H3.2z" fill="${PONEGLYPH_INK}" stroke="#0a121c" stroke-width=".8" stroke-linejoin="round"/>
  <path d="M3.2 5.4h11.6" stroke="#0a121c" stroke-width=".7" opacity=".55"/>
  <g stroke="${PONEGLYPH_GLYPH}" stroke-width="1" opacity=".62" stroke-linecap="round">
    <path d="M5.4 8.6h7.2"/><path d="M5.4 11.4h4.6"/><path d="M5.4 14.2h6.2"/>
  </g>
</svg>`;
}
