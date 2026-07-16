/**
 * lib/canon.ts — the derivation layer. THE PRODUCT LIVES HERE.
 *
 * Everything the app renders is a pure function of ONE number: the chapter the
 * reader is on. This module owns that derivation and nothing else. No React, no
 * DOM, no fetch, no fs.
 *
 * ============================================================================
 * WHY THIS FILE IS TYPE-ONLY AGAINST lib/schema.ts
 * ============================================================================
 * lib/schema.ts imports `node:fs` (it reads data/canon.json off disk). If this
 * module did a VALUE import from it, every client component that calls
 * worldAtChapter() would drag node:fs into the browser bundle and the build
 * would fail to resolve it.
 *
 * So: `import type` only. Type imports are erased at compile time, so the
 * emitted JS has zero reference to schema.ts. buildWorld() takes the Canon as a
 * PARAMETER (the server injects it) instead of loading it. That keeps this file
 * pure, client-safe, trivially unit-testable, and reusable by the future video
 * renderer — which will call worldAtChapter() frame by frame with no Next.js,
 * no browser, and no filesystem in sight.
 *
 *   server (app/page.tsx):  buildWorld(loadCanon())  ->  World  (serializable)
 *   client (components/*):  worldAtChapter(world, ch) -> WorldAt
 *
 * ============================================================================
 * SPOILER SAFETY IS A RENDERING CONTRACT, NOT ENCRYPTION
 * ============================================================================
 * The full World payload ships to the browser — that is what makes the slider
 * feel instant instead of a server round-trip per tick. worldAtChapter() decides
 * what is KNOWN at a chapter; the components are responsible for never putting
 * an unknown island's name, or a future arc's name, into the DOM. The fog stops
 * accidental spoilers. It is not a security boundary, and the UI says so.
 */

import type {
  Canon,
  Island,
  Arc,
  CrewJoin,
  VoyageWaypoint,
  Vessel,
  PresenceWindow,
  PresenceMember,
  CrewPresence,
  CharacterPresence,
} from "./schema";

/* -------------------------------------------------------------------------- */
/* types — the serialization contract between server and client                */
/* -------------------------------------------------------------------------- */

export type Confidence = "canon" | "derived" | "guess";
export type IslandStatus = "manga" | "anime" | "non_canon" | "unknown";

/** Chapters are the spine. Episodes are a derived, lossy view of them. */
export type Axis = "chapter" | "episode";

export type WorldIsland = {
  slug: string;
  name: string;
  japanese: string | null;
  romaji: string | null;
  sea: string;
  region: string | null;
  lng: number;
  lat: number;
  /** THE FOG KEY. null for every island that is not in the manga. */
  debutChapter: number | null;
  debutEpisode: number | null;
  debutArc: string | null;
  debutSaga: string | null;
  status: IslandStatus;
  /** The confidence of the POSITION — the claim the map is actually making. */
  confidence: Confidence;
  debutSource: string | null;
  affiliation: string | null;
  wikiUrl: string | null;
  /** Rendered verbatim in the island panel. The receipts are the product. */
  sourceRef: string;
};

export type WorldArc = {
  slug: string;
  name: string;
  saga: string;
  order: number;
  chapterStart: number;
  chapterEnd: number | null;
  episodeStart: number;
  episodeEnd: number | null;
  ongoing: boolean;
  confidence: Confidence;
  sourceRef: string;
};

export type WorldSaga = {
  name: string;
  order: number;
  chapterStart: number;
  chapterEnd: number | null;
};

export type WorldCrewMember = {
  slug: string;
  name: string;
  joinChapter: number;
  joinEpisode: number;
  joinArc: string;
  joinSaga: string;
  order: number;
  /** false = no human has checked this against the manga. The UI MUST show it. */
  verified: boolean;
  confidence: Confidence;
  sourceRef: string;
};

/** A waypoint on the crew's authored route. Position already resolved (see schema). */
export type WorldVoyageWaypoint = {
  order: number;
  slug: string | null;
  label: string;
  chapter: number;
  lng: number;
  lat: number;
  verified: boolean;
  confidence: Confidence;
};

/** The crew's ship as of a chapter. `fromChapter` is when it becomes the ship. */
export type WorldVessel = {
  order: number;
  name: string;
  slug: string;
  fromChapter: number;
  verified: boolean;
  confidence: Confidence;
};

/**
 * A window of presence: where an entity is, from a chapter, optionally until
 * one. Position already resolved by the build. The active window at chapter N
 * is the last whose fromChapter <= N — unless its toChapter has passed, in
 * which case the entity is off the map (see presenceWindowAt).
 */
export type WorldPresenceWindow = {
  order: number;
  islandSlug: string | null;
  label: string;
  fromChapter: number;
  toChapter: number | null;
  lng: number;
  lat: number;
  verified: boolean;
  confidence: Confidence;
  sourceRef: string;
};

export type WorldPresenceMember = {
  slug: string;
  name: string;
  fromChapter: number;
  verified: boolean;
  confidence: Confidence;
};

export type WorldCrewPresence = {
  slug: string;
  name: string;
  crewId: number | null;
  vessel: { name: string; slug: string } | null;
  members: WorldPresenceMember[];
  windows: WorldPresenceWindow[];
};

export type WorldCharacterPresence = {
  slug: string;
  name: string;
  affiliation: string;
  crewSlug: string | null;
  windows: WorldPresenceWindow[];
};

export type World = {
  meta: {
    generatedAt: string;
    sourceManifestSha: string;
    warnings: string[];
  };
  chapterMin: number;
  chapterMax: number;
  episodeMin: number;
  episodeMax: number;
  /**
   * The last manga chapter the anime has actually adapted. Chapters after this
   * exist but have no episode — the anime lags the manga. Rendered as "not yet
   * animated" rather than silently clamped to the final episode.
   */
  lastAnimatedChapter: number;
  crewName: string;
  islands: WorldIsland[];
  arcs: WorldArc[];
  sagas: WorldSaga[];
  crew: WorldCrewMember[];
  /** The authored crew route: waypoints in voyage order, positions resolved. */
  voyage: { crewSlug: string; waypoints: WorldVoyageWaypoint[] };
  /** The crew's ship progression, chapter-gated, ascending by fromChapter. */
  vessels: WorldVessel[];
  /** Who else sails these seas: crews and Warlords with authored, chapter-gated windows. */
  presence: { crews: WorldCrewPresence[]; characters: WorldCharacterPresence[] };
  /** episodeToChapter[ep] -> manga chapter reached by the end of that episode. */
  episodeToChapter: number[];
  /** chapterToEpisode[ch] -> first episode that reaches that chapter, or null. */
  chapterToEpisode: (number | null)[];
  counts: {
    islandsTotal: number;
    islandsManga: number;
    islandsOffCanon: number;
    arcs: number;
    sagas: number;
    crew: number;
    crewVerified: number;
    presenceCrews: number;
    presenceCharacters: number;
    episodes: number;
    /** Position confidence across the MAPPABLE (manga-canon) set. */
    positionConfidence: Record<Confidence, number>;
  };
};

/** Everything true about the world at one chapter. The whole product. */
export type WorldAt = {
  chapter: number;
  /** null when the anime has not adapted this far. */
  episode: number | null;
  notYetAnimated: boolean;
  arc: WorldArc | null;
  saga: string | null;
  /** Islands the reader has met. Fogged ones are NOT in here. */
  visibleIslands: WorldIsland[];
  /** Islands that exist but are still beyond the reader. Names must not render. */
  foggedIslands: WorldIsland[];
  /** The crew standing on the deck. Never a Debut field — see the Jinbe note. */
  crew: WorldCrewMember[];
  /** The ship they are sailing right now. null before the first vessel's chapter. */
  vessel: WorldVessel | null;
  /**
   * The traveled route as of this chapter: every waypoint reached, plus the ship's
   * interpolated current position as the final point. Empty until the voyage starts.
   */
  voyagePath: [number, number][];
  /** Where the ship is right now — the one interpolated quantity in the model. */
  shipPosition: [number, number] | null;
  stats: {
    islandsRevealed: number;
    islandsMappable: number;
    crewSize: number;
    crewTotal: number;
    arcIndex: number;
    arcTotal: number;
    chapterProgress: number;
  };
};

/* -------------------------------------------------------------------------- */
/* build — server side, once, at render time                                   */
/* -------------------------------------------------------------------------- */

/**
 * Derive the chapter ceiling from the data rather than hard-coding 1185.
 *
 * Deliberately does NOT consult episodes[].chapters: that field is the dirty
 * free-text bridge from the upstream API and it contains chapter 5642 and
 * chapter 1955, neither of which exist. Islands, arcs and crew joins are the
 * trustworthy chapter-bearing collections.
 */
function deriveChapterMax(canon: Canon): number {
  let max = 1;
  for (const i of canon.islands) if (i.debut_chapter && i.debut_chapter > max) max = i.debut_chapter;
  for (const a of canon.arcs) {
    if (a.chapter_start > max) max = a.chapter_start;
    if (a.chapter_end && a.chapter_end > max) max = a.chapter_end;
  }
  for (const j of canon.crew_joins) if (j.join_chapter > max) max = j.join_chapter;
  return max;
}

/**
 * Build the episode <-> chapter bridge.
 *
 * THIS IS THE DIRTIEST JOIN IN THE PROJECT and it needs a real defence.
 * episodes[].chapters comes from an upstream free-text field ("Chap 2",
 * "Ch. 1118-1119", "Chap 30 + filler"). The normalizer parsed it, but it could
 * only parse what was there — and what was there includes:
 *
 *   ep  564 -> chapter 5642   (does not exist; the real value is 644)
 *   ep 1082 -> chapter 1955   (does not exist)
 *   ep  279 -> chapter 1      (a recap; it is not adapting chapter 1)
 *
 * Left alone, ep 279 claiming chapter 1 would make chapterToEpisode[1] = 279,
 * and the reader at chapter 1 would be told they are on episode 279.
 *
 * THE FILTER: an episode's chapter must fall inside its OWN arc's chapter range.
 * Arc ranges came from the wiki with a self-reconciling count cross-check, so
 * they are the one thing here worth trusting. Anything outside its arc is thrown
 * away, not clamped — a clamp would invent a number, and inventing numbers is
 * how the French garbage reaches the UI.
 *
 * The result is then forced monotonic (the anime adapts the manga forwards) and
 * inverted as a monotone step function, which is robust to the gaps, duplicates
 * and filler that a membership test is not.
 */
function buildBridge(canon: Canon, chapterMax: number) {
  const arcBySlug = new Map(canon.arcs.map((a) => [a.slug, a]));

  let episodeMax = 0;
  for (const e of canon.episodes) if (e.number > episodeMax) episodeMax = e.number;

  // 1. arc-anchored validity filter
  const claimed = new Map<number, number>();
  for (const e of canon.episodes) {
    const arc = e.arc ? arcBySlug.get(e.arc) : undefined;
    const lo = arc ? arc.chapter_start : 1;
    const hi = arc ? arc.chapter_end ?? chapterMax : chapterMax;

    let best = 0;
    for (const c of e.chapters) {
      if (c >= lo && c <= hi && c >= 1 && c <= chapterMax && c > best) best = c;
    }
    if (best > 0) claimed.set(e.number, best);
  }

  // 2. monotonic carry-forward. A filler episode does not advance the manga, so
  //    it inherits the chapter the story was already at.
  const episodeToChapter = new Array<number>(episodeMax + 1).fill(0);
  let cursor = 0;
  for (let n = 1; n <= episodeMax; n++) {
    const c = claimed.get(n);
    if (c !== undefined && c > cursor) cursor = c;
    episodeToChapter[n] = cursor;
  }

  // 3. invert the monotone step function: the first episode that reaches ch.
  const chapterToEpisode = new Array<number | null>(chapterMax + 1).fill(null);
  let j = 1;
  for (let ch = 1; ch <= chapterMax; ch++) {
    while (j <= episodeMax && episodeToChapter[j] < ch) j++;
    chapterToEpisode[ch] = j <= episodeMax ? j : null;
  }

  const lastAnimatedChapter = episodeMax > 0 ? episodeToChapter[episodeMax] : 0;
  return { episodeToChapter, chapterToEpisode, episodeMax, lastAnimatedChapter };
}

function toIsland(i: Island): WorldIsland {
  return {
    slug: i.slug,
    name: i.name,
    japanese: i.japanese,
    romaji: i.romaji,
    sea: i.sea,
    region: i.region,
    lng: i.lng,
    lat: i.lat,
    debutChapter: i.debut_chapter,
    debutEpisode: i.debut_episode,
    debutArc: i.debut_arc,
    debutSaga: i.debut_saga,
    status: i.canon_status,
    confidence: i.canon_confidence,
    debutSource: i.debut_source,
    affiliation: i.affiliation,
    wikiUrl: i.wiki_url,
    sourceRef: i.source_ref,
  };
}

function toArc(a: Arc): WorldArc {
  return {
    slug: a.slug,
    name: a.name,
    saga: a.saga,
    order: a.order,
    chapterStart: a.chapter_start,
    chapterEnd: a.chapter_end,
    episodeStart: a.episode_start,
    episodeEnd: a.episode_end,
    ongoing: a.ongoing,
    confidence: a.canon_confidence,
    sourceRef: a.source_ref,
  };
}

function toCrew(j: CrewJoin): WorldCrewMember {
  return {
    slug: j.slug,
    name: j.name,
    joinChapter: j.join_chapter,
    joinEpisode: j.join_episode,
    joinArc: j.join_arc,
    joinSaga: j.join_saga,
    order: j.order,
    verified: j.verified,
    confidence: j.canon_confidence,
    sourceRef: j.source_ref,
  };
}

function toWaypoint(w: VoyageWaypoint): WorldVoyageWaypoint {
  return {
    order: w.order,
    slug: w.slug,
    label: w.label,
    chapter: w.chapter,
    lng: w.lng,
    lat: w.lat,
    verified: w.verified,
    confidence: w.canon_confidence,
  };
}

function toVessel(v: Vessel): WorldVessel {
  return {
    order: v.order,
    name: v.name,
    slug: v.slug,
    fromChapter: v.from_chapter,
    verified: v.verified,
    confidence: v.canon_confidence,
  };
}

function toWindow(w: PresenceWindow): WorldPresenceWindow {
  return {
    order: w.order,
    islandSlug: w.island_slug,
    label: w.label,
    fromChapter: w.from_chapter,
    toChapter: w.to_chapter,
    lng: w.lng,
    lat: w.lat,
    verified: w.verified,
    confidence: w.canon_confidence,
    sourceRef: w.source_ref,
  };
}

function toMember(m: PresenceMember): WorldPresenceMember {
  return {
    slug: m.slug,
    name: m.name,
    fromChapter: m.from_chapter,
    verified: m.verified,
    confidence: m.canon_confidence,
  };
}

function toCrewPresence(c: CrewPresence): WorldCrewPresence {
  return {
    slug: c.slug,
    name: c.name,
    crewId: c.crew_id,
    vessel: c.vessel,
    members: c.members.map(toMember),
    windows: c.windows.map(toWindow).sort((a, b) => a.order - b.order),
  };
}

function toCharacterPresence(c: CharacterPresence): WorldCharacterPresence {
  return {
    slug: c.slug,
    name: c.name,
    affiliation: c.affiliation,
    crewSlug: c.crew_slug,
    windows: c.windows.map(toWindow).sort((a, b) => a.order - b.order),
  };
}

/**
 * Derive the saga axis FROM THE ARCS, not from canon.sagas.
 *
 * canon.sagas is the api-onepiece.com collection and it is still French:
 * "Île des Hommes-Poissons", "War at the top", "Celestial Island". Rendering it
 * would put machine-translated French in front of the user. arcs[].saga comes
 * from the Fandom wiki and is clean English ("Fish-Man Island Saga", "Summit War
 * Saga"), and every arc carries one, so the saga axis is exactly as trustworthy
 * as the arc axis. canon.sagas is intentionally never read by the app.
 */
function derivesSagas(arcs: WorldArc[]): WorldSaga[] {
  const byName = new Map<string, WorldSaga>();
  for (const a of [...arcs].sort((x, y) => x.order - y.order)) {
    const existing = byName.get(a.saga);
    if (!existing) {
      byName.set(a.saga, {
        name: a.saga,
        order: byName.size,
        chapterStart: a.chapterStart,
        chapterEnd: a.chapterEnd,
      });
      continue;
    }
    // extend. An ongoing arc (chapterEnd null) makes its saga open-ended too.
    if (existing.chapterEnd !== null) {
      existing.chapterEnd = a.chapterEnd === null ? null : Math.max(existing.chapterEnd, a.chapterEnd);
    }
  }
  return [...byName.values()];
}

/**
 * Project the 1.34 MB build artifact down to the payload the instrument needs.
 *
 * Dropped on purpose: 786 characters, 149 crews, 213 fruits, and every episode
 * title. The 10 crew members the roster renders come from crew_joins, not from
 * characters.
 *
 * characters[].bounty and characters[].status are dropped for a product reason,
 * not a size one: the dataset stores ONE current-day value per character. Luffy's
 * bounty is 3,000,000,000 — showing that next to his name at chapter 100 would
 * spoil ~950 chapters in the one app whose entire promise is that it will not.
 * A bounty is only safe to render if it is versioned by chapter, and it is not.
 */
export function buildWorld(canon: Canon): World {
  const chapterMax = deriveChapterMax(canon);
  const { episodeToChapter, chapterToEpisode, episodeMax, lastAnimatedChapter } = buildBridge(
    canon,
    chapterMax,
  );

  const islands = canon.islands.map(toIsland);
  const arcs = canon.arcs.map(toArc).sort((a, b) => a.order - b.order);
  const crew = canon.crew_joins.map(toCrew).sort((a, b) => a.order - b.order);
  const sagas = derivesSagas(arcs);

  const voyage = {
    crewSlug: canon.voyage.crew_slug,
    waypoints: canon.voyage.waypoints
      .map(toWaypoint)
      .sort((a, b) => a.order - b.order),
  };
  const vessels = canon.vessels.map(toVessel).sort((a, b) => a.order - b.order);
  const presence = {
    crews: canon.presence.crews.map(toCrewPresence),
    characters: canon.presence.characters.map(toCharacterPresence),
  };

  const mappable = islands.filter((i) => i.status === "manga" && i.debutChapter !== null);
  const positionConfidence: Record<Confidence, number> = { canon: 0, derived: 0, guess: 0 };
  for (const i of mappable) positionConfidence[i.confidence]++;

  return {
    meta: {
      generatedAt: canon.meta.generated_at,
      sourceManifestSha: canon.meta.source_manifest_sha,
      warnings: canon.meta.warnings,
    },
    chapterMin: 1,
    chapterMax,
    episodeMin: 1,
    episodeMax,
    lastAnimatedChapter,
    // The crew name comes from the data, not a string literal in the app.
    crewName: canon.crew_joins[0]?.crew ?? "Crew",
    islands,
    arcs,
    sagas,
    crew,
    voyage,
    vessels,
    presence,
    episodeToChapter,
    chapterToEpisode,
    counts: {
      islandsTotal: islands.length,
      islandsManga: mappable.length,
      islandsOffCanon: islands.length - mappable.length,
      arcs: arcs.length,
      sagas: sagas.length,
      crew: crew.length,
      crewVerified: crew.filter((c) => c.verified).length,
      presenceCrews: presence.crews.length,
      presenceCharacters: presence.characters.length,
      episodes: canon.episodes.length,
      positionConfidence,
    },
  };
}

/* -------------------------------------------------------------------------- */
/* derive — pure, client-safe, frame-by-frame cheap                            */
/* -------------------------------------------------------------------------- */

export function clampChapter(world: World, ch: number): number {
  if (!Number.isFinite(ch)) return world.chapterMin;
  return Math.min(world.chapterMax, Math.max(world.chapterMin, Math.round(ch)));
}

export function clampEpisode(world: World, ep: number): number {
  if (!Number.isFinite(ep)) return world.episodeMin;
  return Math.min(world.episodeMax, Math.max(world.episodeMin, Math.round(ep)));
}

/** The chapter a viewer at `episode` has effectively read. */
export function chapterForEpisode(world: World, episode: number): number {
  const ep = clampEpisode(world, episode);
  return Math.max(world.chapterMin, world.episodeToChapter[ep] ?? world.chapterMin);
}

/** The first episode that reaches `chapter`, or null if the anime is not there yet. */
export function episodeForChapter(world: World, chapter: number): number | null {
  const ch = clampChapter(world, chapter);
  return world.chapterToEpisode[ch] ?? null;
}

/** The arc a reader is in at `chapter`. Handles the ongoing arc's null end. */
export function arcForChapter(world: World, chapter: number): WorldArc | null {
  for (const a of world.arcs) {
    if (chapter >= a.chapterStart && (a.chapterEnd === null || chapter <= a.chapterEnd)) return a;
  }
  return null;
}

/**
 * THE PRODUCT. Everything true about the world at one chapter.
 *
 * Pure and cheap enough to call once per animation frame (413 islands, 33 arcs,
 * 10 crew). The map tweens the chapter value and calls this every frame, which
 * is what makes the world unfurl instead of snap.
 */
/**
 * The ship's position and the traveled route at a (possibly fractional) chapter.
 * Step-then-lerp: every waypoint whose chapter has been reached is a fixed point;
 * between the last reached waypoint and the next, the ship glides linearly by
 * chapter. This is the ONE interpolated quantity in the whole model.
 *
 * Called per-frame by the map (fractional chapter -> a smooth sail) and once by
 * worldAtChapter (integer chapter -> the discrete WorldAt). Waypoints are assumed
 * pre-sorted ascending by chapter — the build enforces non-decreasing chapters.
 */
export function voyageGeometryAt(
  waypoints: WorldVoyageWaypoint[],
  chapter: number,
): { path: [number, number][]; ship: [number, number] | null } {
  if (waypoints.length === 0) return { path: [], ship: null };
  const first = waypoints[0];
  if (chapter < first.chapter) return { path: [], ship: null };

  const path: [number, number][] = [];
  let ship: [number, number] = [first.lng, first.lat];
  for (let i = 0; i < waypoints.length; i++) {
    const w = waypoints[i];
    if (w.chapter > chapter) break;
    path.push([w.lng, w.lat]);
    ship = [w.lng, w.lat];
    const next = waypoints[i + 1];
    if (next && chapter < next.chapter) {
      // The reader is mid-leg: glide from w toward next in proportion to chapter.
      const span = next.chapter - w.chapter;
      const t = span > 0 ? (chapter - w.chapter) / span : 0;
      ship = [w.lng + (next.lng - w.lng) * t, w.lat + (next.lat - w.lat) * t];
      path.push(ship);
      break;
    }
  }
  return { path, ship };
}

/** The last vessel whose fromChapter <= chapter. null before the first ship sets sail. */
export function vesselAtChapter(vessels: WorldVessel[], chapter: number): WorldVessel | null {
  let cur: WorldVessel | null = null;
  for (const v of vessels) {
    if (v.fromChapter <= chapter) cur = v;
    else break;
  }
  return cur;
}

/**
 * The active presence window at `chapter`: the last window whose fromChapter <=
 * chapter — unless that window has ended (toChapter !== null and the reader is
 * past it), in which case the entity is OFF the map (a death, an arrest, a
 * departure). Same last-before-chapter gate as vesselAtChapter, plus an ending.
 * Windows are assumed pre-sorted ascending — the build enforces it.
 */
export function presenceWindowAt(
  windows: WorldPresenceWindow[],
  chapter: number,
): WorldPresenceWindow | null {
  let cur: WorldPresenceWindow | null = null;
  for (const w of windows) {
    if (w.fromChapter <= chapter) cur = w;
    else break;
  }
  if (cur && cur.toChapter !== null && chapter > cur.toChapter) return null;
  return cur;
}

export function worldAtChapter(world: World, chapter: number): WorldAt {
  const ch = clampChapter(world, chapter);
  const { path: voyagePath, ship: shipPosition } = voyageGeometryAt(world.voyage.waypoints, ch);
  const vessel = vesselAtChapter(world.vessels, ch);

  const visibleIslands: WorldIsland[] = [];
  const foggedIslands: WorldIsland[] = [];
  for (const i of world.islands) {
    // Off-canon islands (film/anime/game) have no chapter. They are not fogged
    // and not revealed — they are simply not on the manga timeline at all.
    if (i.status !== "manga" || i.debutChapter === null) continue;
    if (i.debutChapter <= ch) visibleIslands.push(i);
    else foggedIslands.push(i);
  }

  const crew = world.crew.filter((c) => c.joinChapter <= ch);
  const arc = arcForChapter(world, ch);
  const episode = episodeForChapter(world, ch);

  return {
    chapter: ch,
    episode,
    notYetAnimated: episode === null,
    arc,
    saga: arc?.saga ?? null,
    visibleIslands,
    foggedIslands,
    crew,
    vessel,
    voyagePath,
    shipPosition,
    stats: {
      islandsRevealed: visibleIslands.length,
      islandsMappable: world.counts.islandsManga,
      crewSize: crew.length,
      crewTotal: world.counts.crew,
      arcIndex: arc ? arc.order + 1 : 0,
      arcTotal: world.counts.arcs,
      chapterProgress: (ch - world.chapterMin) / Math.max(1, world.chapterMax - world.chapterMin),
    },
  };
}
