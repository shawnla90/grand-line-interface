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
};

/** Standalone Warlords (no rostered crew flag) render in a neutral chart ink. */
export const WARLORD_COLOR = "#8c9ab5";

export const DEFAULT_CREW_COLOR = "#8c9ab5";

export function crewColor(slug: string | null | undefined): string {
  return (slug && CREW_STYLE[slug]?.color) || DEFAULT_CREW_COLOR;
}
