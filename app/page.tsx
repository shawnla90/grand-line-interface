/**
 * app/page.tsx — the server half. It exists to do exactly two things:
 * read the committed build artifact, and hand a compact payload to the client.
 *
 * ZERO REQUEST-TIME FETCHES. loadCanon() reads data/canon.json off disk with
 * node:fs and validates it against the zod schema, which throws if the artifact
 * is malformed — a bad canon.json must fail the build, not render a wrong map.
 * There is no database, no ORM and no external API anywhere in the request path.
 *
 * NOTE (Next.js 16): `searchParams` is a Promise. Synchronous access was removed
 * in this major, so it is awaited here.
 */

import { loadCanon } from "@/lib/schema";
import { loadBuildLog } from "@/lib/buildlog";
import { loadArt } from "@/lib/art";
import {
  buildWorld, chapterForEpisode, clampChapter, clampEpisode, isIslandFogged, type Axis,
} from "@/lib/canon";
import { isPresenceLens, parseFocus, type Focus, type PresenceLens } from "@/lib/lenses";
// one()/int() live in lib/entry.ts now: the entry routes parse the same URL, and
// two copies of "what does ?ch mean" is how they drift.
import { int, one } from "@/lib/entry";
import Atlas from "@/components/Atlas";

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const world = buildWorld(loadCanon());
  const sp = await searchParams;

  const ch = int(one(sp.ch));
  const ep = int(one(sp.ep));
  const lensParam = one(sp.lens);
  const initialLens: PresenceLens = isPresenceLens(lensParam) ? lensParam : "crew";
  // ?focus=status:yonko — the share mechanic carries the isolation, not just the
  // chapter. Garbage parses to null rather than throwing: a URL is user input.
  const initialFocus: Focus | null = parseFocus(one(sp.focus));

  // ?ep= is accepted as a convenience and folded straight back onto the chapter
  // axis — the chapter is the only state the app actually keeps.
  let initialChapter: number | null = null;
  let initialAxis: Axis = one(sp.axis) === "episode" ? "episode" : "chapter";

  if (ep !== null) {
    initialChapter = chapterForEpisode(world, clampEpisode(world, ep));
    initialAxis = "episode";
  } else if (ch !== null) {
    initialChapter = clampChapter(world, ch);
  }

  // ?island=<slug> — the round trip back from /island/[slug]. Validated through
  // isIslandFogged against the SAME chapter the map will open at, so a crafted
  // /?ch=1&island=laugh-tale cannot select what the map would otherwise fog.
  // An unknown or fogged slug is simply dropped: the map opens, nothing is
  // selected, and the URL told the reader nothing it did not already know.
  const islandParam = one(sp.island);
  const target = islandParam ? world.islands.find((i) => i.slug === islandParam) : undefined;
  const initialIsland =
    target && !isIslandFogged(target, initialChapter ?? world.chapterMin) ? target.slug : null;

  return (
    <Atlas
      world={world}
      initialIsland={initialIsland}
      art={loadArt()}
      initialChapter={initialChapter}
      initialAxis={initialAxis}
      initialLens={initialLens}
      initialFocus={initialFocus}
      buildLog={loadBuildLog()}
    />
  );
}
