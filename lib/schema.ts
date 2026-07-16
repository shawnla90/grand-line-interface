/**
 * lib/schema.ts — the zod schema for data/canon.json, and the only sanctioned way
 * to read it.
 *
 * ARCHITECTURE: the app makes ZERO request-time fetches. There is no database and
 * no ORM. data/canon.json is a committed build artifact produced by
 * scripts/normalize.py, and this module validates it at build time and THROWS on
 * any schema violation. A canon.json that does not parse must not become a page.
 *
 * loadCanon() uses node:fs, so it is server-only: call it in a Server Component,
 * generateStaticParams, or a route handler — never in a "use client" file.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

/* -------------------------------------------------------------------------- */
/* enums                                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Every row in the artifact carries this. It is rendered in the UI, not just
 * stored — a pin the machine guessed must not look like a pin a human confirmed.
 */
export const CanonConfidence = z.enum(["canon", "derived", "guess"]);
export type CanonConfidence = z.infer<typeof CanonConfidence>;

/** The raw feed ships SIX status values across two languages. This is the only one. */
export const CharacterStatus = z.enum(["alive", "dead", "unknown"]);
export type CharacterStatus = z.infer<typeof CharacterStatus>;

export const CrewStatus = z.enum(["active", "inactive", "disbanded", "unknown"]);
export type CrewStatus = z.infer<typeof CrewStatus>;

/**
 * FILTER THE MAP ON THIS. 123 of the 413 "islands" debut only in non-canon media
 * (films, games, ONAs) and 33 are anime-only. They have no chapter because they are
 * not in the manga. That is correct data, not missing data — plotting all 413 would
 * put One Piece Film: Z locations on a canon map.
 */
export const IslandCanonStatus = z.enum(["manga", "anime", "non_canon", "unknown"]);
export type IslandCanonStatus = z.infer<typeof IslandCanonStatus>;

/* -------------------------------------------------------------------------- */
/* collections                                                                 */
/* -------------------------------------------------------------------------- */

const Range = z.object({ start: z.number().int(), end: z.number().int().nullable() });

/** [start, end] — end is null only for the ongoing arc. */
const Segment = z.tuple([z.number().int(), z.number().int().nullable()]);

export const Saga = z.object({
  id: z.number().int(),
  title: z.string(),
  number: z.number().int(),
  /** Parsed from the French string "1 à 100". null on the Final Saga, which upstream leaves as "-". */
  chapters: Range.nullable(),
  volumes: Range.nullable(),
  episodes: Range.nullable(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Saga = z.infer<typeof Saga>;

export const Arc = z.object({
  slug: z.string(),
  name: z.string(),
  saga: z.string(),
  /** Dense 0..N. This is the voyage order, and check_canon asserts the chain is unbroken. */
  order: z.number().int().nonnegative(),
  chapter_start: z.number().int(),
  chapter_end: z.number().int().nullable(),
  chapter_segments: z.array(Segment),
  episode_start: z.number().int(),
  episode_end: z.number().int().nullable(),
  /**
   * AUTHORITATIVE for episode membership. Never test with [episode_start, episode_end]:
   * the gaps between segments are FILLER belonging to no canon arc. Impel Down runs
   * 422-425 AND 430-452 — episodes 426-429 are filler. 7 arcs are split this way.
   */
  episode_segments: z.array(Segment),
  ongoing: z.boolean(),
  prev_arc: z.string().nullable(),
  next_arc: z.string().nullable(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Arc = z.infer<typeof Arc>;

export const Island = z.object({
  slug: z.string(),
  name: z.string(),
  japanese: z.string().nullable(),
  romaji: z.string().nullable(),
  region: z.string().nullable(),
  sea: z.string(),
  /** NOT NULL, by rule, from commit #1. A map of 15 pins on an empty ocean is a dead map. */
  lng: z.number().min(-180).max(180),
  lat: z.number().min(-90).max(90),
  /** THE FOG KEY. Non-null for all 256 manga-canon islands. */
  debut_chapter: z.number().int().nullable(),
  debut_episode: z.number().int().nullable(),
  debut_arc: z.string().nullable(),
  debut_saga: z.string().nullable(),
  canon_status: IslandCanonStatus,
  debut_source: z.string().nullable(),
  affiliation: z.string().nullable(),
  wiki_url: z.string().nullable(),
  /** The confidence of the POSITION — that is the claim the map is making. */
  canon_confidence: CanonConfidence,
  source_ref: z.string().min(1),
});
export type Island = z.infer<typeof Island>;

export const Character = z.object({
  id: z.number().int(),
  name: z.string(),
  slug: z.string(),
  status: CharacterStatus,
  /** Parsed from the French string "3.000.000.000" to 3000000000. Never a string here. */
  bounty: z.number().int().nonnegative().nullable(),
  /** Parsed from "19 ans". */
  age: z.number().int().nullable(),
  size_cm: z.number().int().nullable(),
  job: z.string().nullable(),
  crew_id: z.number().int().nullable(),
  crew_name: z.string().nullable(),
  fruit_id: z.number().int().nullable(),
  fruit_name: z.string().nullable(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Character = z.infer<typeof Character>;

export const Crew = z.object({
  id: z.number().int(),
  name: z.string(),
  /** The untranslated upstream name, kept for traceability: "The Chapeau de Paille crew". */
  raw_name: z.string(),
  romanized: z.string().nullable(),
  status: CrewStatus,
  total_bounty: z.number().int().nonnegative().nullable(),
  member_count: z.number().int().nullable(),
  is_yonko: z.boolean(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Crew = z.infer<typeof Crew>;

export const Fruit = z.object({
  id: z.number().int(),
  name: z.string(),
  romanized: z.string().nullable(),
  type: z.string(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Fruit = z.infer<typeof Fruit>;

export const Episode = z.object({
  id: z.number().int(),
  number: z.number().int(),
  title: z.string(),
  /** The manga chapters this episode adapts. Empty = filler. This is the anime->manga bridge. */
  chapters: z.array(z.number().int()),
  arc: z.string().nullable(),
  saga: z.string().nullable(),
  filler: z.boolean(),
  release_date: z.string().nullable(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
});
export type Episode = z.infer<typeof Episode>;

/**
 * THE JINBE FIELD. Debut is not Join. Every upstream source has a Debut field and it
 * is wrong for 10/10 Straw Hats — Jinbe debuts at episode 430 and joins at 977.
 * These rows are hand-typed in canon/crew_joins.json and every one of them is
 * verified:false until a human confirms it against the manga. Render that.
 */
export const CrewJoin = z.object({
  name: z.string(),
  slug: z.string(),
  crew: z.string(),
  crew_slug: z.string(),
  join_chapter: z.number().int(),
  join_episode: z.number().int(),
  join_arc: z.string(),
  join_saga: z.string(),
  /** Join sequence, ascending by join_chapter — NOT the roster order fans recite. */
  order: z.number().int(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
  /** false = a human has not confirmed this against the manga yet. Show it in the UI. */
  verified: z.boolean(),
});
export type CrewJoin = z.infer<typeof CrewJoin>;

/**
 * A waypoint on the crew's authored voyage. Hand-typed in canon/voyage_legs.json.
 * The normalizer resolves each waypoint's position (from an island slug, or an
 * explicit lng/lat) and writes lng/lat here, so the app never re-resolves. The
 * drawn route connects these points in `order`, revealing up to the reader's
 * chapter. verified:false until a human confirms the chapter against the manga.
 */
export const VoyageWaypoint = z.object({
  order: z.number().int(),
  /** The island this waypoint sits on, when it is one. null for open-sea points (e.g. Baratie). */
  slug: z.string().nullable(),
  label: z.string(),
  chapter: z.number().int(),
  lng: z.number(),
  lat: z.number(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
  verified: z.boolean(),
});
export type VoyageWaypoint = z.infer<typeof VoyageWaypoint>;

export const Voyage = z.object({
  crew: z.string(),
  crew_slug: z.string(),
  waypoints: z.array(VoyageWaypoint),
});
export type Voyage = z.infer<typeof Voyage>;

/**
 * The crew's ship as of a chapter. Hand-typed in canon/vessels.json. `from_chapter`
 * is the chapter FROM which this vessel is the ship; the reader sees the last one
 * whose from_chapter <= their chapter. Chapter-gated so a reader at ch. 20 sees the
 * small boat, never the Thousand Sunny. verified:false until confirmed.
 */
export const Vessel = z.object({
  order: z.number().int(),
  name: z.string(),
  slug: z.string(),
  from_chapter: z.number().int(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
  verified: z.boolean(),
});
export type Vessel = z.infer<typeof Vessel>;

/**
 * A window of presence: WHERE an entity (a crew, a Warlord) is, FROM a chapter,
 * optionally UNTIL one. Hand-typed in canon/crew_presence.json — no upstream
 * source has a location-by-chapter axis at all. The active window at chapter N
 * is the last whose from_chapter <= N, unless its to_chapter has passed (a
 * death, an arrest, a departure) — then the entity is off the map. The
 * normalizer resolves each window's position (island slug or explicit lng/lat)
 * and writes lng/lat here, so the app never re-resolves. canon_confidence rates
 * the POSITION claim, exactly like an island pin.
 */
export const PresenceWindow = z.object({
  order: z.number().int(),
  /** The island this window anchors to, when it is one. null for open-sea points. */
  island_slug: z.string().nullable(),
  label: z.string(),
  from_chapter: z.number().int().positive(),
  to_chapter: z.number().int().positive().nullable(),
  lng: z.number(),
  lat: z.number(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
  verified: z.boolean(),
});
export type PresenceWindow = z.infer<typeof PresenceWindow>;

/** A named member rendered as an orb once from_chapter is reached (while the crew is on the map). */
export const PresenceMember = z.object({
  slug: z.string(),
  name: z.string(),
  from_chapter: z.number().int().positive(),
  source_ref: z.string().min(1),
  canon_confidence: CanonConfidence,
  verified: z.boolean(),
});
export type PresenceMember = z.infer<typeof PresenceMember>;

export const CrewPresence = z.object({
  slug: z.string(),
  name: z.string(),
  /** Link back to crews[] for traceability. null when upstream has no row (Buggy, Donquixote). */
  crew_id: z.number().int().nullable(),
  vessel: z.object({ name: z.string(), slug: z.string() }).nullable(),
  members: z.array(PresenceMember),
  windows: z.array(PresenceWindow),
});
export type CrewPresence = z.infer<typeof CrewPresence>;

/** A standalone chapter-gated character (the Warlords). */
export const CharacterPresence = z.object({
  slug: z.string(),
  name: z.string(),
  affiliation: z.string(),
  crew_slug: z.string().nullable(),
  windows: z.array(PresenceWindow),
});
export type CharacterPresence = z.infer<typeof CharacterPresence>;

export const Presence = z.object({
  crews: z.array(CrewPresence),
  characters: z.array(CharacterPresence),
});
export type Presence = z.infer<typeof Presence>;

export const CanonMeta = z.object({
  generated_at: z.string(),
  generator: z.string(),
  /** sha256 of data/raw/_manifest.json — the upstream-drift fingerprint. */
  source_manifest_sha: z.string(),
  sources: z.object({ api: z.string(), wiki: z.string(), canon: z.string() }),
  /** The Fandom wiki is CC-BY-SA 3.0. The footer must attribute it. */
  attribution_required_in_ui: z.literal(true),
  canon_confidence_values: z.array(CanonConfidence),
  warnings: z.array(z.string()),
  counts: z.record(z.string(), z.number().int()),
});
export type CanonMeta = z.infer<typeof CanonMeta>;

export const Canon = z.object({
  meta: CanonMeta,
  sagas: z.array(Saga),
  arcs: z.array(Arc),
  islands: z.array(Island),
  characters: z.array(Character),
  crews: z.array(Crew),
  fruits: z.array(Fruit),
  episodes: z.array(Episode),
  crew_joins: z.array(CrewJoin),
  voyage: Voyage,
  vessels: z.array(Vessel),
  presence: Presence,
});
export type Canon = z.infer<typeof Canon>;

/* -------------------------------------------------------------------------- */
/* loader                                                                      */
/* -------------------------------------------------------------------------- */

export const CANON_PATH = join(process.cwd(), "data", "canon.json");

let cached: Canon | null = null;

/**
 * Read + validate data/canon.json. Server-only. Throws on any schema violation:
 * a bad artifact must fail the build, not render a wrong map.
 */
export function loadCanon(): Canon {
  if (cached) return cached;

  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(CANON_PATH, "utf8"));
  } catch (cause) {
    throw new Error(
      `Could not read ${CANON_PATH}. It is a build artifact — generate it with ` +
        `\`python3 scripts/normalize.py\` and commit it.`,
      { cause },
    );
  }

  const parsed = Canon.safeParse(raw);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .slice(0, 15)
      .map((i) => `  ${i.path.join(".") || "<root>"}: ${i.message}`)
      .join("\n");
    throw new Error(
      `data/canon.json failed schema validation (${parsed.error.issues.length} issues):\n${issues}\n\n` +
        `Do not "fix" this in the app. Fix scripts/normalize.py or canon/, re-run the ` +
        `normalizer, and re-run scripts/check_canon.py.`,
    );
  }

  cached = parsed.data;
  return cached;
}

/* -------------------------------------------------------------------------- */
/* the fog                                                                     */
/* -------------------------------------------------------------------------- */

/** The arc a reader is in at `chapter`. */
export function arcForChapter(canon: Canon, chapter: number): Arc | null {
  return (
    canon.arcs.find((a) =>
      a.chapter_segments.some(([lo, hi]) => chapter >= lo && (hi === null || chapter <= hi)),
    ) ?? null
  );
}

/**
 * THE PRODUCT. The islands a reader at `chapter` has met — everything after is fog.
 * Non-manga islands are excluded: they have no chapter because they are not in the manga.
 */
export function islandsVisibleAt(canon: Canon, chapter: number): Island[] {
  return canon.islands.filter(
    (i) => i.canon_status === "manga" && i.debut_chapter !== null && i.debut_chapter <= chapter,
  );
}

/** The crew standing on the deck at `chapter`. Reads the hand-typed joins, never a Debut field. */
export function crewAt(canon: Canon, chapter: number): CrewJoin[] {
  return canon.crew_joins
    .filter((j) => j.join_chapter <= chapter)
    .sort((a, b) => a.order - b.order);
}
