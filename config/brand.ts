/**
 * config/brand.ts — the ONLY place a user-visible name lives.
 *
 * The project name is not locked. Renaming it must be a one-line change here,
 * not a grep across the app. Nothing in app/ or components/ may hard-code the
 * product name, the tagline, or the legal line.
 */

export const BRAND = {
  name: "Grand Line Interface",
  /** Used where the full name is too long (browser tab, tight headers). */
  shortName: "Grand Line Interface",
  tagline: "A One Piece atlas that only shows you the world you've already read.",
  /** The one-sentence pitch, shown under the hero prompt. */
  promise: "Tell it where you are. It renders the world you know — and fogs everything after.",
  /** The hero question. This is the entire first screen. */
  prompt: "Where are you?",

  /**
   * Attribution. Non-negotiable, and rendered small + honest in the footer.
   * data/canon.json carries meta.attribution_required_in_ui: true — the wiki is
   * CC-BY-SA 3.0 and facts are free, but attribution is the obligation.
   */
  legal: {
    unofficial:
      "An unofficial, non-commercial fan reference work. Not affiliated with, endorsed by, or licensed by the rights holders.",
    copyright: "“One Piece” is © Eiichiro Oda / Shueisha / Toei Animation.",
    /**
     * Phase 6 added official artwork (portraits, Jolly Rogers, ships, Devil Fruits,
     * island images). It is NOT original and NOT MIT — this line says so out loud,
     * the same way a derived pin refuses to look human-confirmed.
     */
    artwork:
      "Character portraits, Jolly Rogers, ships, Devil Fruits and location images are official artwork © the rights holders, used as attributed fan reference and excluded from this project’s open-source code license.",
    sources: [
      {
        label: "One Piece Fandom",
        href: "https://onepiece.fandom.com",
        note: "structured facts (chapter/episode ranges, island debuts) under CC-BY-SA 3.0, and official artwork as attributed fan reference. No article prose is reproduced.",
      },
      {
        label: "api-onepiece.com",
        href: "https://api-onepiece.com",
        note: "arcs, episodes, characters, crews. Machine-translated from French; normalized locally.",
      },
      {
        label: "The Library of Ohara",
        href: "https://onepieceworldmap.com",
        note: "inspiration only — no data used. It mapped where the world is; this maps when you know it.",
      },
    ],
  },
} as const;
