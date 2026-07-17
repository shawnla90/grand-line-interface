/**
 * lib/entry.ts — the server-side gate for the entry pages.
 *
 * ============================================================================
 * WHY THIS EXISTS SEPARATELY FROM THE MAP'S GATE
 * ============================================================================
 * The map ships the whole World to the browser and lets worldAtChapter() decide
 * what is KNOWN per frame. That is correct there: you need every island's
 * geometry to draw the fog over it, and the fog is a rendering decision the UI
 * says out loud is not encryption.
 *
 * A page cannot work that way. `/island/water-7?ch=100` is a link somebody SENDS
 * somebody. If the server hands the client the name and lets the client hide it,
 * the name is in the payload, in the flight data, in the share preview, and in
 * the crawler's index. So the routes invert the boundary: the gate runs on the
 * SERVER and a fogged entity's name never enters the response at all.
 *
 * ============================================================================
 * THE 404 IS AN ORACLE. THIS IS THE WHOLE FILE.
 * ============================================================================
 * The obvious design — 200 for a real island, 404 for a nonexistent slug — leaks
 * the entire map. Ask for /island/laugh-tale?ch=100: a 404 means no such island,
 * a 200 means it exists and you just cannot see it yet. Two hundred requests
 * later you have the full list of what is coming. The fog would be intact and
 * the secret would be gone.
 *
 * So a fogged entity and a nonexistent slug return the SAME SINGLETON — not
 * similar objects, the same one. There is no field on it to differ on, no
 * "reason" the page could accidentally print, and no branch a future edit could
 * add without deleting this comment first. Both render 200 "Uncharted". Neither
 * calls notFound().
 *
 * THE HONEST LIMIT: the slug is in the URL, so a recipient of
 * /island/water-7?ch=100 can read the string "water-7" no matter what we do. No
 * server gate fixes that. What this buys is that the server never CONFIRMS it —
 * the response is byte-identical to /island/qwertyuiop?ch=100, so the name in
 * the link is a guess, not a fact. Closing that too would need opaque share
 * tokens, which would break the thing this phase is for: every dot is a door.
 */

import type { Canon, Character } from "./schema";
import type { World, WorldBountyRow, WorldCrewMember, WorldIsland } from "./canon";
import type { WorldFruitReveal } from "./canon";
import {
  clampChapter, clampEpisode, chapterForEpisode, episodeForChapter, isIslandFogged,
  presenceWindowAt, statusHoldersAt,
} from "./canon";

/* -------------------------------------------------------------------------- */
/* searchParams                                                               */
/* -------------------------------------------------------------------------- */

/** Next hands `?a=1&a=2` as an array. Lifted from app/page.tsx — four routes need it now. */
export function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

export function int(v: string | undefined): number | null {
  if (!v) return null;
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
}

export type ChapterCtx = {
  /** Always a real chapter. Never NaN, never out of range. */
  chapter: number;
  /** false when ?ch was absent or garbage — changes the COPY, never the gate. */
  chapterSet: boolean;
  episode: number | null;
};

/**
 * Read the reader's position out of a URL.
 *
 * A missing ?ch fails CLOSED, to chapterMin. Not to chapterMax: a bare
 * /island/laugh-tale would then hand every crawler and every link preview the
 * maximum spoiler, which is the exact opposite of the product. And not to a
 * separate "no chapter, show nothing" gate either — a new gate is a new thing to
 * get wrong. clampChapter(world, NaN) already returns chapterMin, so the app
 * already has an opinion about a missing chapter and this just uses it.
 *
 * chapterSet only changes what the page SAYS: "Where are you?" (an invitation)
 * rather than "beyond your chapter" (a claim about a reader we know nothing
 * about). That mirrors app/page.tsx, which renders HeroPrompt instead of
 * guessing.
 */
export function readChapter(
  world: World,
  sp: { [k: string]: string | string[] | undefined },
): ChapterCtx {
  const ch = int(one(sp.ch));
  const ep = int(one(sp.ep));
  if (ep !== null) {
    const chapter = chapterForEpisode(world, clampEpisode(world, ep));
    return { chapter, chapterSet: true, episode: clampEpisode(world, ep) };
  }
  const chapter = clampChapter(world, ch ?? Number.NaN);
  return { chapter, chapterSet: ch !== null, episode: episodeForChapter(world, chapter) };
}

/* -------------------------------------------------------------------------- */
/* the entry envelope                                                         */
/* -------------------------------------------------------------------------- */

/**
 * CARRIES NOTHING, ON PURPOSE. Any field added here is an oracle: it would let
 * a fogged entity render differently from a nonexistent one, and the difference
 * is the map. It is a frozen singleton so that `uncharted === UNCHARTED` and
 * there is physically nothing to leak.
 */
export const UNCHARTED = Object.freeze({ state: "uncharted" as const });
export type Uncharted = typeof UNCHARTED;

export type Entry<T> = { state: "charted"; data: T } | Uncharted;

export function charted<T>(data: T): Entry<T> {
  return { state: "charted", data };
}

export type EntryFamily = "island" | "character" | "crew" | "fruit";
export const ENTRY_FAMILIES: EntryFamily[] = ["island", "character", "crew", "fruit"];

export function isEntryFamily(v: string | undefined): v is EntryFamily {
  return v === "island" || v === "character" || v === "crew" || v === "fruit";
}

/* -------------------------------------------------------------------------- */
/* the wanted poster's view-model                                             */
/* -------------------------------------------------------------------------- */

/**
 * What a wanted poster is allowed to know.
 *
 * WantedCard's prop used to be WorldCrewMember — a type that only exists because
 * crew_joins is hand-authored, and which carries joinChapter/joinArc/joinSaga/
 * order. Widening it to all 786 characters would hang crew-join facts on 776
 * people who never joined a crew. So the card takes a view-model instead, and
 * the two constructors below are the only doors into it.
 *
 * THIS TYPE IS THE DROP-LIST, ENFORCED BY THE COMPILER. It structurally cannot
 * carry the nine fields a raw canon character row would happily hand you:
 *
 *   bounty      one present-day scalar. Luffy's is 3,000,000,000 at chapter 1.
 *   status      alive|dead. Ace is "dead" from chapter 1.
 *   fruit_name  THE WORST ONE. Luffy's raw row says "Hito Hito no Mi, Nika
 *   fruit_id    model" — a chapter-1044 reveal sitting on a chapter-1
 *               character, which also joins art.fruits[196] and renders the
 *               Nika artwork. It is machine-translated French besides.
 *   crew_name   Jinbe's row says "Straw Hat Pirates" and job "Helmsman". He
 *   crew_id     debuts at 528 and joins at 976 — this is the Jinbe rule
 *   job         arriving through a door check_canon's jinbe_test does not watch.
 *   age         Robin's 30 is post-timeskip.
 *   height_cm   the schema's own comment says it is "the last (adult)" value.
 *
 * None of them can be fogged, because each is a single present-day value with no
 * chapter attached. bounty_history CAN be — that is the whole point of Phase 7B
 * — so the poster carries the history and resolves it through bountyAt().
 */
export type PosterVM = {
  slug: string;
  name: string;
  /**
   * Gated on the bounty, not on the debut: an epithet is poster text. Nobody
   * calls him "Straw Hat Luffy" at chapter 50 — they call him some kid in a
   * straw hat. No bounty, no alias.
   */
  epithet: string | null;
  bountyHistory: WorldBountyRow[];
  verified: boolean;
  /** "joined ch. N" for a Straw Hat; "first seen ch. N" for everyone else. */
  footnote: { label: string; chapter: number } | null;
};

/**
 * THE TWO CONSTRUCTORS GATE DIFFERENTLY, AND THAT IS DELIBERATE.
 *
 * posterFromCrewMember feeds CrewRoster — a CLIENT component that re-gates every
 * frame while the reader drags the chapter dial. It gets the FULL history,
 * because that is Phase 5's established boundary: the World ships and the DOM
 * gates, which is what makes the slider instant instead of a round-trip per
 * tick. The map already works this way and says so out loud.
 *
 * posterFromCharacter feeds a PAGE, and a page is a link somebody sends
 * somebody. Server-gating was the whole point of choosing routes: if the server
 * serialises 3,000,000,000 into the flight data of /character/monkey-d-luffy?ch=1
 * and lets the client hide it, the number is still in the payload, in the share
 * preview and in the crawler's index. So it PRE-GATES: rows the reader has not
 * reached are not in the response at all.
 *
 * (Caught by the unit's own verification script, which found "3000000000" and
 * "Straw Hat Luffy" in a chapter-1 payload. The component was hiding both
 * correctly; the bytes were still there.)
 */
export function posterFromCrewMember(m: WorldCrewMember): PosterVM {
  return {
    slug: m.slug,
    name: m.name,
    epithet: m.epithet,
    bountyHistory: m.bountyHistory,
    verified: m.verified,
    footnote: { label: "joined", chapter: m.joinChapter },
  };
}

export function posterFromCharacter(c: Character, ctx: ChapterCtx): PosterVM {
  // Only the rows the reader has been shown. bountyAt() still resolves over
  // this (lowest order among revealed), so gating twice is harmless — but now
  // there is nothing to gate a second time.
  const revealed = c.bounty_history
    .filter((b) => b.as_of_chapter <= ctx.chapter)
    .map((b) => ({
      order: b.order,
      amount: b.amount,
      asOfChapter: b.as_of_chapter,
      verified: b.verified,
      confidence: b.canon_confidence,
      sourceRef: b.source_ref,
    }));
  return {
    slug: c.slug,
    name: c.name,
    // The epithet rides the bounty — poster text, not a name. Pre-gated here for
    // the same reason as the history: at chapter 50 the string "Straw Hat Luffy"
    // should not exist in the response, not merely go unrendered.
    epithet: revealed.length > 0 ? c.epithet : null,
    bountyHistory: revealed,
    verified: false, // no character row is human-verified yet
    footnote:
      c.debut_chapter !== null ? { label: "first seen", chapter: c.debut_chapter } : null,
  };
}

/* -------------------------------------------------------------------------- */
/* the four resolvers                                                          */
/* -------------------------------------------------------------------------- */

export type IslandEntryData = {
  island: WorldIsland;
  arcName: string | null;
};

export function islandEntry(world: World, slug: string, ctx: ChapterCtx): Entry<IslandEntryData> {
  const island = world.islands.find((i) => i.slug === slug);
  if (!island) return UNCHARTED;
  if (isIslandFogged(island, ctx.chapter)) return UNCHARTED;
  return charted({
    island,
    arcName: world.arcs.find((a) => a.slug === island.debutArc)?.name ?? null,
  });
}

export type CharacterEntryData = {
  poster: PosterVM;
  /** Their crew's slug IF a presence roster places them — never characters[].crew_id,
   *  which says "Straw Hat Pirates" for a Jinbe 448 chapters early. */
  crewSlug: string | null;
  origin: string | null;
  birthday: string | null;
  bloodType: string | null;
  debutChapter: number;
  sourceRef: string;
  wikiSourceRef: string | null;
};

/**
 * The 154 characters with a null debut_chapter are PERMANENTLY uncharted: we
 * cannot prove the reader has met them, so we do not claim they exist.
 *
 * Duplicate slugs (sanjuan-wolf, silvers-rayleigh, scarlett — three pairs) are
 * resolved to the lowest id, deterministically. check_canon asserts the pairs
 * agree on debut_chapter, so the gate is identical either way; only the bounty
 * history and epithet could differ, and picking is better than throwing.
 */
export function characterEntry(
  canon: Canon,
  world: World,
  slug: string,
  ctx: ChapterCtx,
): Entry<CharacterEntryData> {
  const matches = canon.characters.filter((c) => c.slug === slug);
  if (matches.length === 0) return UNCHARTED;
  const c = matches.reduce((a, b) => (a.id <= b.id ? a : b));
  if (c.debut_chapter === null || c.debut_chapter > ctx.chapter) return UNCHARTED;
  // The map link's focus. Derived from the AUTHORED presence rosters, so it can
  // only ever say what the chart itself would show at this chapter.
  let crewSlug: string | null = null;
  for (const crew of world.presence.crews) {
    if (crew.members.some((m) => m.slug === slug && m.fromChapter <= ctx.chapter)) {
      crewSlug = crew.slug;
      break;
    }
  }
  if (!crewSlug && world.crew.some((m) => m.slug === slug && m.joinChapter <= ctx.chapter)) {
    crewSlug = world.voyage.crewSlug;
  }

  return charted({
    poster: posterFromCharacter(c, ctx),
    crewSlug,
    origin: c.origin,
    birthday: c.birthday,
    bloodType: c.blood_type,
    debutChapter: c.debut_chapter,
    sourceRef: c.source_ref,
    wikiSourceRef: c.wiki_source_ref,
  });
}

export type CrewEntryData = {
  slug: string;
  name: string;
  /** Where they are AT this chapter, or null if they are off the board. */
  here: { islandSlug: string | null; label: string; sourceRef: string } | null;
  vessel: { name: string; slug: string } | null;
  members: { poster: PosterVM; fruit: WorldFruitReveal | null; haki: string[] }[];
  statuses: string[];
  isVoyageCrew: boolean;
};

/**
 * A crew is chartable only if somebody AUTHORED a chapter for it.
 *
 * canon/crews.json has 149 rows and not one of them has a chapter or a slug —
 * which is exactly why buildWorld drops them: an entity with no chapter cannot
 * be fogged. The only crews with a gate are the ~32 in canon/crew_presence.json.
 *
 * A DERIVED gate would be worse than none. min(member debut) for the Blackbeard
 * Pirates is ~223, because Teach debuts as a Whitebeard crewman — the crew does
 * not exist until ~440. That gate would tell a chapter-230 reader that the
 * Blackbeard Pirates are out there. No gate, no page.
 */
export function crewEntry(world: World, slug: string, ctx: ChapterCtx): Entry<CrewEntryData> {
  const c = world.presence.crews.find((x) => x.slug === slug);
  if (!c) return UNCHARTED;
  // The authored gate: the first window anyone typed for this crew.
  const first = Math.min(...c.windows.map((w) => w.fromChapter));
  if (!Number.isFinite(first) || first > ctx.chapter) return UNCHARTED;

  const w = presenceWindowAt(c.windows, ctx.chapter);
  const members = c.members
    .filter((m) => m.fromChapter <= ctx.chapter)
    .map((m) => ({
      poster: {
        slug: m.slug,
        name: m.name,
        epithet: null,
        bountyHistory: [],
        verified: m.verified,
        footnote: { label: "first seen", chapter: m.fromChapter },
      } satisfies PosterVM,
      fruit: m.fruit && m.fruit.fromChapter <= ctx.chapter ? m.fruit : null,
      haki: m.haki.filter((h) => h.fromChapter <= ctx.chapter).map((h) => h.type),
    }));

  const statuses: string[] = [];
  for (const kind of ["yonko", "warlord", "supernova"] as const) {
    if (statusHoldersAt(world, kind, ctx.chapter).has(slug)) statuses.push(kind);
  }

  return charted({
    slug: c.slug,
    name: c.name,
    here: w ? { islandSlug: w.islandSlug, label: w.label, sourceRef: w.sourceRef } : null,
    vessel: c.vessel,
    members,
    statuses,
    isVoyageCrew: slug === world.voyage.crewSlug,
  });
}

export type FruitEntryData = {
  slug: string;
  name: string;
  type: string;
  description: string | null;
  fruitId: number | null;
  users: { slug: string; name: string; fromChapter: number; sourceRef: string }[];
};

/**
 * THE USER LIST COMES FROM THE AUTHORED REVEALS. NEVER FROM characters[].fruit_id.
 *
 * That join is right there, it is one line, and it is a chapter-1044 spoiler on
 * a chapter-1 page: Luffy's canon row says fruit_name "Hito Hito no Mi, Nika
 * model", so `characters.filter(c => c.fruit_id === id)` would list him under
 * the Nika fruit for a reader who has just met him in a barrel. A fruit is a
 * STORY REVEAL with its own chapter, and only canon/fruit_reveals.json knows it.
 *
 * That is also why only 35 of 213 fruits are chartable. The other 178 have no
 * reveal authored, so they have no gate, so they get no page. Coverage grows by
 * authoring reveals, not by writing code.
 */
export function fruitEntry(canon: Canon, world: World, slug: string, ctx: ChapterCtx): Entry<FruitEntryData> {
  const users: FruitEntryData["users"] = [];
  let name: string | null = null;
  let type: string | null = null;
  let fruitId: number | null = null;

  const carriers: { slug: string; name: string; fruit: WorldFruitReveal | null }[] = [
    ...world.presence.crews.flatMap((c) =>
      c.members.map((m) => ({ slug: m.slug, name: m.name, fruit: m.fruit })),
    ),
    ...world.presence.characters.map((c) => ({ slug: c.slug, name: c.name, fruit: c.fruit })),
  ];
  for (const e of carriers) {
    if (!e.fruit || e.fruit.slug !== slug) continue;
    // The fruit EXISTS as a chartable thing once anyone's reveal is authored…
    name ??= e.fruit.name;
    type ??= e.fruit.type;
    // …but a USER only appears once THEIR reveal has been reached.
    if (e.fruit.fromChapter <= ctx.chapter) {
      users.push({
        slug: e.slug,
        name: e.name,
        fromChapter: e.fruit.fromChapter,
        sourceRef: "",
      });
    }
  }
  if (name === null) return UNCHARTED; // no authored reveal: not chartable at all
  if (users.length === 0) return UNCHARTED; // authored, but not yet reached

  const row = canon.fruits.find((f) => f.name === name);
  fruitId = row?.id ?? null;

  return charted({
    slug,
    name,
    type: type!,
    // The prose describes the fruit, not who has it — safe once revealed.
    description: row?.description ?? null,
    fruitId,
    users: users.sort((a, b) => a.fromChapter - b.fromChapter),
  });
}
