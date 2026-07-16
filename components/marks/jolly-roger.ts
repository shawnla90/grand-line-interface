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

// Accent inks for the Phase 5 crews — same register as the house palette above.
const SCAR = "#c05248"; // Red-Hair red
const CANDY = "#d78bb1"; // Big Mom pink
const HORN = "#efe6d4"; // Beasts bone (horns share the bone ink)
const RUST = "#b0413e"; // Kid red
const AMBER = "#e3c96b"; // Heart yellow
const SERPENT = "#9b6fae"; // Kuja violet
const FLAMINGO = "#d7a1c2"; // Donquixote pink
const NOSE = "#d1543f"; // Buggy red

/** crewSlug -> inner SVG (drawn in a 48×48 viewBox). */
const ROGERS: Record<string, string> = {
  // The Straw Hats: skull and crossed bones under Luffy's straw hat.
  "straw-hat-pirates": `
    ${bones}
    ${skull}
    <path d="M10 17.5 Q24 11 38 17.5 Q24 21.5 10 17.5 Z" fill="${STRAW}"/>
    <path d="M16.5 17.5 Q24 6.5 31.5 17.5 Z" fill="${STRAW}"/>
    <rect x="16.5" y="15" width="15" height="2.8" rx="1" fill="${BAND}"/>`,

  // Red-Hair: three claw scars raked across the left eye.
  "red-hair-pirates": `
    ${bones}
    ${skull}
    <g stroke="${SCAR}" stroke-width="1.5" stroke-linecap="round">
      <line x1="17.2" y1="19.2" x2="20.4" y2="28.8"/>
      <line x1="19.4" y1="18.6" x2="22.6" y2="28.2"/>
      <line x1="21.6" y1="18" x2="24.4" y2="27.4"/>
    </g>`,

  // Whitebeard: the great crescent mustache, sweeping wider than the skull itself.
  "whitebeard-pirates": `
    ${bones}
    ${skull}
    <g stroke="${BONE}" stroke-width="3.4" fill="none" stroke-linecap="round">
      <path d="M24 29.5 Q15 32 10 23.5"/>
      <path d="M24 29.5 Q33 32 38 23.5"/>
    </g>`,

  // Big Mom: a mob-cap bonnet over the cranium and full candy lips on the jaw.
  "big-mom-pirates": `
    ${bones}
    ${skull}
    <path d="M12.5 19.5 Q24 7.5 35.5 19.5 Q30 15.5 24 15.8 Q18 15.5 12.5 19.5 Z" fill="${CANDY}"/>
    <path d="M20 33.6 Q24 37 28 33.6 Q24 31.8 20 33.6 Z" fill="${CANDY}"/>`,

  // Beasts: two horns curving off the cranium.
  "beasts-pirates": `
    ${bones}
    <path d="M16 17 Q12.5 11 15.5 5.5 Q16.5 12 20 15.5 Z" fill="${HORN}"/>
    <path d="M32 17 Q35.5 11 32.5 5.5 Q31.5 12 28 15.5 Z" fill="${HORN}"/>
    ${skull}`,

  // Blackbeard: three skulls abreast — the center one flanked by two smaller.
  "blackbeard-pirates": `
    ${bones}
    <g>
      <circle cx="9.5" cy="21.5" r="5.4" fill="${BONE}"/>
      <circle cx="7.8" cy="21.3" r="1.3" fill="${INK}"/>
      <circle cx="11.2" cy="21.3" r="1.3" fill="${INK}"/>
    </g>
    <g>
      <circle cx="38.5" cy="21.5" r="5.4" fill="${BONE}"/>
      <circle cx="36.8" cy="21.3" r="1.3" fill="${INK}"/>
      <circle cx="40.2" cy="21.3" r="1.3" fill="${INK}"/>
    </g>
    ${skull}`,

  // Kid: a jagged sawtooth grin stitched shut, with rivet studs on the cranium.
  "kid-pirates": `
    ${bones}
    ${skull}
    <path d="M18 31.4 l2 2.6 2-2.6 2 2.6 2-2.6 2 2.6 2-2.6" stroke="${INK}"
          stroke-width="1.5" fill="none" stroke-linejoin="round"/>
    <g fill="${RUST}">
      <circle cx="18.5" cy="16.8" r="1.2"/>
      <circle cx="24" cy="15.4" r="1.2"/>
      <circle cx="29.5" cy="16.8" r="1.2"/>
    </g>`,

  // Heart: no skull at all — the spoked ring and the wide grin, in amber.
  "heart-pirates": `
    <g stroke="${AMBER}" stroke-width="2.6" stroke-linecap="round">
      <line x1="24" y1="4.5" x2="24" y2="9.5"/>
      <line x1="24" y1="38.5" x2="24" y2="43.5"/>
      <line x1="4.5" y1="24" x2="9.5" y2="24"/>
      <line x1="38.5" y1="24" x2="43.5" y2="24"/>
      <line x1="10.2" y1="10.2" x2="13.7" y2="13.7"/>
      <line x1="34.3" y1="34.3" x2="37.8" y2="37.8"/>
      <line x1="10.2" y1="37.8" x2="13.7" y2="34.3"/>
      <line x1="34.3" y1="13.7" x2="37.8" y2="10.2"/>
    </g>
    <circle cx="24" cy="24" r="13" fill="none" stroke="${AMBER}" stroke-width="2.8"/>
    <circle cx="19.5" cy="21" r="1.9" fill="${AMBER}"/>
    <circle cx="28.5" cy="21" r="1.9" fill="${AMBER}"/>
    <path d="M16.5 27 Q24 33.5 31.5 27" stroke="${AMBER}" stroke-width="2.6" fill="none"
          stroke-linecap="round"/>`,

  // Kuja: a serpent winding beneath the crossed bones, head raised.
  "kuja-pirates": `
    ${bones}
    ${skull}
    <path d="M8.5 40.5 Q14 36.5 19 39.5 Q24 42.5 29 39.5 Q33 37 37 39.5"
          stroke="${SERPENT}" stroke-width="2.4" fill="none" stroke-linecap="round"/>
    <path d="M37 39.5 l3.5-2 -1 3.6 Z" fill="${SERPENT}"/>`,

  // Donquixote: the grinning ring, cancelled by a single slash. No skull.
  "donquixote-pirates": `
    <circle cx="24" cy="24" r="13.5" fill="none" stroke="${BONE}" stroke-width="3"/>
    <circle cx="19.5" cy="20.5" r="1.9" fill="${BONE}"/>
    <circle cx="28.5" cy="20.5" r="1.9" fill="${BONE}"/>
    <path d="M16.5 27 Q24 34 31.5 27" stroke="${BONE}" stroke-width="2.8" fill="none"
          stroke-linecap="round"/>
    <line x1="11.5" y1="11.5" x2="36.5" y2="36.5" stroke="${FLAMINGO}" stroke-width="3.4"
          stroke-linecap="round"/>`,

  // Buggy: the big round nose, and side tufts where hair escapes the bandana.
  "buggy-pirates": `
    ${bones}
    ${skull}
    <path d="M13 21 Q10.5 18 11.5 14.5 Q13.5 17.5 15.5 18.5 Z" fill="${SERPENT}"/>
    <path d="M35 21 Q37.5 18 36.5 14.5 Q34.5 17.5 32.5 18.5 Z" fill="${SERPENT}"/>
    <circle cx="24" cy="26.6" r="3.4" fill="${NOSE}"/>
    <circle cx="23" cy="25.6" r="0.9" fill="${BONE}" opacity="0.55"/>`,
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
