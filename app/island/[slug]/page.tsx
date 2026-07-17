/**
 * app/island/[slug]/page.tsx — every dot is a door.
 *
 * NOTE (Next.js 16): `params` AND `searchParams` are both Promises.
 *
 * No `export const dynamic`. Awaiting searchParams already makes this dynamic,
 * and a redundant export is one more thing to explain. Dynamic is the price of
 * server-gating, and server-gating is the point: `/island/water-7?ch=100` is a
 * link somebody SENDS somebody, so the name must not be in the response.
 *
 * generateMetadata has the same gate as the body, for the same reason. A page
 * whose <h1> says "Uncharted" and whose <title> says "Water 7" has leaked in the
 * browser tab, the bookmark and the crawler's index.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { loadArt } from "@/lib/art";
import { buildWorld, eventsAtChapter, presenceWindowAt } from "@/lib/canon";
import { islandEntry, readChapter } from "@/lib/entry";
import { BRAND } from "@/config/brand";
import IslandEntry, { type IslandExtras } from "@/components/entry/IslandEntry";
import Uncharted from "@/components/entry/Uncharted";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
};

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const world = buildWorld(loadCanon());
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = islandEntry(world, slug, ctx);

  if (entry.state === "uncharted") {
    // Identical for fogged and nonexistent — including the noindex, so the
    // robots directive itself cannot be read as an oracle.
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
      openGraph: { images: [`/api/og/island/${slug}?ch=${ctx.chapter}`] },
    };
  }
  return {
    title: `${entry.data.island.name} — ${BRAND.shortName}`,
    description: `${entry.data.island.name}, charted as of chapter ${ctx.chapter}. ${BRAND.tagline}`,
    openGraph: { images: [`/api/og/island/${slug}?ch=${ctx.chapter}`] },
  };
}

export default async function Page({ params, searchParams }: Props) {
  const world = buildWorld(loadCanon());
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = islandEntry(world, slug, ctx);

  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }

  // The extras. Every one rides a gate that already exists — this page invents
  // no chapter logic of its own.
  const poneglyphs: IslandExtras["poneglyphs"] = [];
  for (const p of world.poneglyphs) {
    if (p.revealedChapter > ctx.chapter) continue;
    const w = presenceWindowAt(p.custody, ctx.chapter);
    if (!w || w.islandSlug !== slug) continue;
    poneglyphs.push({ slug: p.slug, name: p.name, kind: p.kind, label: w.label });
  }

  const presentCrews: IslandExtras["presentCrews"] = [];
  for (const c of world.presence.crews) {
    const w = presenceWindowAt(c.windows, ctx.chapter);
    if (w && w.islandSlug === slug) presentCrews.push({ slug: c.slug, name: c.name, label: w.label });
  }
  for (const c of world.presence.characters) {
    const w = presenceWindowAt(c.windows, ctx.chapter);
    if (w && w.islandSlug === slug) presentCrews.push({ slug: c.slug, name: c.name, label: w.label });
  }

  const wp = world.voyage.waypoints.find((w) => w.slug === slug && w.chapter <= ctx.chapter);

  const events: IslandExtras["events"] = eventsAtChapter(world, ctx.chapter)
    .filter((e) => e.islandSlug === slug)
    .map((e) => ({ slug: e.slug, name: e.name, kind: e.kind, chapter: e.occurredChapter }));

  return (
    <IslandEntry
      data={entry.data}
      extras={{
        poneglyphs,
        presentCrews,
        voyageCall: wp ? { chapter: wp.chapter, label: wp.label } : null,
        events,
      }}
      art={loadArt()}
      chapter={ctx.chapter}
    />
  );
}
