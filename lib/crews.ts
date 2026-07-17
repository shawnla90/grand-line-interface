/**
 * lib/crews.ts — per-crew presentation style. Facts live in canon/; style lives
 * in code (the same split jolly-roger.ts already makes). Pure module: no React,
 * no DOM, no fs — safe for the map, the legend, and any future renderer.
 *
 * Colors are accent hues chosen to read on the deep-ocean ground (#071324) and
 * on parchment, staying inside the atlas's muted brass-and-vellum register —
 * these are chart inks, not team jerseys.
 */

export type CrewStyle = { color: string; label: string };

export const CREW_STYLE: Record<string, CrewStyle> = {
  // the Emperors and the crews the story keeps returning to
  "straw-hat-pirates": { color: "#f0c877", label: "Straw Hat Pirates" },
  "red-hair-pirates": { color: "#c05248", label: "Red-Hair Pirates" },
  "whitebeard-pirates": { color: "#e8e0cf", label: "Whitebeard Pirates" },
  "big-mom-pirates": { color: "#d78bb1", label: "Big Mom Pirates" },
  "beasts-pirates": { color: "#7fa06b", label: "Beasts Pirates" },
  "blackbeard-pirates": { color: "#6b7890", label: "Blackbeard Pirates" },
  "kid-pirates": { color: "#b0413e", label: "Kid Pirates" },
  "heart-pirates": { color: "#e3c96b", label: "Heart Pirates" },
  "kuja-pirates": { color: "#9b6fae", label: "Kuja Pirates" },
  "donquixote-pirates": { color: "#d7a1c2", label: "Donquixote Pirates" },
  "buggy-pirates": { color: "#d17a4a", label: "Buggy Pirates" },
  // East Blue — the four crews of the first act
  "alvida-pirates": { color: "#a86f8e", label: "Alvida Pirates" },
  "black-cat-pirates": { color: "#7d7f96", label: "Black Cat Pirates" },
  "krieg-pirates": { color: "#8a7a52", label: "Krieg Pirates" },
  "arlong-pirates": { color: "#5f9ba8", label: "Arlong Pirates" },
  // Paradise
  "baroque-works": { color: "#b58a5e", label: "Baroque Works" },
  "foxy-pirates": { color: "#c78f4e", label: "Foxy Pirates" },
  "cipher-pol-9": { color: "#9c9fae", label: "CP9" },
  "thriller-bark-pirates": { color: "#8f7bb0", label: "Thriller Bark Pirates" },
  // the gate to the New World
  "sun-pirates": { color: "#d9a05b", label: "Sun Pirates" },
  "new-fish-man-pirates": { color: "#5c8f7d", label: "New Fish-Man Pirates" },
  "caribou-pirates": { color: "#6f8a5c", label: "Caribou Pirates" },
  // the Worst Generation
  "on-air-pirates": { color: "#c96f8a", label: "On Air Pirates" },
  "hawkins-pirates": { color: "#a3b06a", label: "Hawkins Pirates" },
  "fallen-monk-pirates": { color: "#b08a6a", label: "Fallen Monk Pirates" },
  "bonney-pirates": { color: "#e0a3b8", label: "Bonney Pirates" },
  "fire-tank-pirates": { color: "#9a6b5c", label: "Fire Tank Pirates" },
  "drake-pirates": { color: "#6b8fb0", label: "Drake Pirates" },
  // post-timeskip
  "barto-club": { color: "#7fb08a", label: "Barto Club" },
  "beautiful-pirates": { color: "#c9a8d6", label: "Beautiful Pirates" },
  "germa-66": { color: "#6f7fc0", label: "Germa 66" },
  "revolutionary-army": { color: "#5f8fa8", label: "Revolutionary Army" },
};

/** Standalone Warlords (no rostered crew flag) render in a neutral chart ink. */
export const WARLORD_COLOR = "#8c9ab5";

/**
 * Presence characters who answer to no crew flag still answer to something. The
 * affiliation ink is what separates an admiral from a Warlord on the crew lens —
 * without it every unrostered figure on the chart reads as the same grey, and
 * Marineford at ch. 550 becomes a pile of identical dots.
 */
export const AFFILIATION_STYLE: Record<string, CrewStyle> = {
  Marine: { color: "#4f7fa8", label: "Marines" },
  Revolutionary: { color: "#5f8fa8", label: "Revolutionary Army" },
  Warlord: { color: WARLORD_COLOR, label: "Warlords" },
};

export const DEFAULT_CREW_COLOR = "#8c9ab5";

export function crewColor(slug: string | null | undefined): string {
  return (slug && CREW_STYLE[slug]?.color) || DEFAULT_CREW_COLOR;
}

/** The ink for an unrostered presence character, by their affiliation. */
export function affiliationColor(affiliation: string | null | undefined): string {
  return (affiliation && AFFILIATION_STYLE[affiliation]?.color) || WARLORD_COLOR;
}
