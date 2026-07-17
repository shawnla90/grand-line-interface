/**
 * app/crew/[slug]/page.tsx — a crew, as of your chapter.
 *
 * Charts the ~32 crews somebody authored a presence window for. The other 117
 * in canon/crews.json have no chapter, so they cannot be fogged, so they get no
 * page — the same rule that makes buildWorld drop them. See lib/entry.ts.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { crewEntry, readChapter } from "@/lib/entry";
import { BRAND } from "@/config/brand";
import CrewEntry from "@/components/entry/CrewEntry";
import Uncharted from "@/components/entry/Uncharted";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
};

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const world = buildWorld(loadCanon());
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = crewEntry(world, slug, ctx);
  if (entry.state === "uncharted") {
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
      openGraph: { images: [`/api/og/crew/${slug}?ch=${ctx.chapter}`] },
    };
  }
  return {
    title: `${entry.data.name} — ${BRAND.shortName}`,
    description: BRAND.tagline,
    openGraph: { images: [`/api/og/crew/${slug}?ch=${ctx.chapter}`] },
  };
}

export default async function Page({ params, searchParams }: Props) {
  const world = buildWorld(loadCanon());
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = crewEntry(world, slug, ctx);
  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }
  return <CrewEntry data={entry.data} chapter={ctx.chapter} />;
}
