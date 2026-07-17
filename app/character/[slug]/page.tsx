/**
 * app/character/[slug]/page.tsx — the wanted poster.
 *
 * Reads RAW canon (loadCanon), not the World — buildWorld drops 776 of the 786
 * characters, because the map only ever needed the ten aboard. That makes this
 * the one route in the app holding a canon row with an ungated bounty, an
 * ungated fruit and an ungated crew in its hand. It does not pass them on:
 * characterEntry returns a PosterVM, which cannot carry them. The type is the
 * guard; this file just resolves and renders.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { loadArt } from "@/lib/art";
import { buildWorld } from "@/lib/canon";
import { characterEntry, readChapter } from "@/lib/entry";
import { BRAND } from "@/config/brand";
import CharacterEntry from "@/components/entry/CharacterEntry";
import Uncharted from "@/components/entry/Uncharted";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
};

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = characterEntry(canon, world, slug, ctx);

  if (entry.state === "uncharted") {
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
      openGraph: { images: [`/api/og/character/${slug}?ch=${ctx.chapter}`] },
    };
  }
  // The epithet is already bounty-gated by the VM, so the title cannot call him
  // "Straw Hat Luffy" before the world does.
  const { poster } = entry.data;
  return {
    title: `${poster.name} — ${BRAND.shortName}`,
    description: poster.epithet ? `"${poster.epithet}". ${BRAND.tagline}` : BRAND.tagline,
    openGraph: { images: [`/api/og/character/${slug}?ch=${ctx.chapter}`] },
  };
}

export default async function Page({ params, searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = characterEntry(canon, world, slug, ctx);

  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }
  return (
    <CharacterEntry
      data={entry.data}
      portrait={loadArt().characters[slug]}
      chapter={ctx.chapter}
    />
  );
}
