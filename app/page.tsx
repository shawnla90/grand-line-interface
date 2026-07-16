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
import { buildWorld, chapterForEpisode, clampChapter, clampEpisode, type Axis } from "@/lib/canon";
import { isPresenceLens, type PresenceLens } from "@/lib/lenses";
import Atlas from "@/components/Atlas";

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function int(v: string | undefined): number | null {
  if (!v) return null;
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
}

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

  return (
    <Atlas
      world={world}
      initialChapter={initialChapter}
      initialAxis={initialAxis}
      initialLens={initialLens}
      buildLog={loadBuildLog()}
    />
  );
}
