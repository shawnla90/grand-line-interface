/**
 * app/fruit/[slug]/page.tsx — a devil fruit, and who you have seen eat it.
 *
 * Charts the 35 fruits with an authored reveal. The other 178 have no chapter,
 * so they have no gate, so they get no page. Coverage grows by authoring
 * reveals in canon/fruit_reveals.json — not by writing code here.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { loadArt } from "@/lib/art";
import { buildWorld } from "@/lib/canon";
import { fruitEntry, readChapter } from "@/lib/entry";
import { BRAND } from "@/config/brand";
import FruitEntry from "@/components/entry/FruitEntry";
import Uncharted from "@/components/entry/Uncharted";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ [k: string]: string | string[] | undefined }>;
};

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const entry = fruitEntry(canon, world, slug, readChapter(world, sp));
  if (entry.state === "uncharted") {
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
    };
  }
  return { title: `${entry.data.name} — ${BRAND.shortName}`, description: BRAND.tagline };
}

export default async function Page({ params, searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = fruitEntry(canon, world, slug, ctx);
  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }
  const art = entry.data.fruitId !== null ? loadArt().fruits[entry.data.fruitId] : undefined;
  return <FruitEntry data={entry.data} art={art} chapter={ctx.chapter} />;
}
