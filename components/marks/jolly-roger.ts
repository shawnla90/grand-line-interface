/**
 * components/marks/jollyRoger.ts — original SVG crew flags.
 *
 * EVERY MARK HERE IS DRAWN FROM PRIMITIVES. No traced art, no imported image, no
 * character render. A Jolly Roger is an idea (a skull, some bones, a motif); this
 * file draws that idea in one consistent house style so the repo stays cleanly
 * open-source and forkable. That "every mark is ours" line is worth more in this
 * fandom than any ripped PNG — see README + config/brand.ts.
 *
 * Output is a plain SVG string so the SAME vector serves two callers with one
 * source of truth: the imperative MapLibre ship marker (which needs innerHTML) and
 * the React <JollyRoger> component (which wraps this). Add a crew by adding one
 * entry to ROGERS; the fallback is a generic skull-and-bones.
 */

const INK = "#0b1424"; // eye/nose negative space — reads on parchment and on ocean
const BONE = "#efe6d4"; // parchment
const STRAW = "#f0c877"; // straw-hat gold
const BAND = "#9c4436"; // hatband clay

/** Crossed bones behind every skull — shared by all crews. */
const bones = `
  <g stroke="${BONE}" stroke-width="3.1" stroke-linecap="round">
    <line x1="13" y1="35" x2="35" y2="15"/>
    <line x1="13" y1="15" x2="35" y2="35"/>
  </g>
  <g fill="${BONE}">
    <circle cx="12.4" cy="35" r="3"/><circle cx="35.6" cy="15" r="3"/>
    <circle cx="12.4" cy="15" r="3"/><circle cx="35.6" cy="35" r="3"/>
  </g>`;

/** A plain skull — cranium, jaw, eyes, nose. The shared base of every Roger. */
const skull = `
  <circle cx="24" cy="24" r="10.2" fill="${BONE}"/>
  <rect x="20.2" y="31.5" width="7.6" height="5" rx="2.2" fill="${BONE}"/>
  <circle cx="20.2" cy="24" r="2.3" fill="${INK}"/>
  <circle cx="27.8" cy="24" r="2.3" fill="${INK}"/>
  <path d="M24 26.6 l-1.5 2.5 h3 z" fill="${INK}"/>`;

/** crewSlug -> inner SVG (drawn in a 48×48 viewBox). */
const ROGERS: Record<string, string> = {
  // The Straw Hats: skull and crossed bones under Luffy's straw hat.
  "straw-hat-pirates": `
    ${bones}
    ${skull}
    <path d="M10 17.5 Q24 11 38 17.5 Q24 21.5 10 17.5 Z" fill="${STRAW}"/>
    <path d="M16.5 17.5 Q24 6.5 31.5 17.5 Z" fill="${STRAW}"/>
    <rect x="16.5" y="15" width="15" height="2.8" rx="1" fill="${BAND}"/>`,
};

/**
 * Return a complete <svg> string for a crew's Jolly Roger.
 * Unknown crews get the generic skull and bones — honest, and still on-brand.
 */
export function jollyRogerSvg(
  crewSlug: string,
  opts: { size?: number } = {},
): string {
  const size = opts.size ?? 28;
  const inner = ROGERS[crewSlug] ?? `${bones}${skull}`;
  return `<svg width="${size}" height="${size}" viewBox="0 0 48 48" aria-hidden="true" role="img">${inner}</svg>`;
}

/** The crews with a bespoke flag today (everything else falls back to the skull). */
export const CREWS_WITH_ROGER = Object.keys(ROGERS);
