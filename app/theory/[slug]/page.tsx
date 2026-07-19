/**
 * app/theory/[slug]/page.tsx — a theory the reader has earned.
 *
 * Charts the theories in canon/theories.json that have surfaced by the reader's
 * chapter. A theory past the bookmark — or a slug that never existed — renders
 * the same Uncharted page, byte-identical, for the reasons lib/entry.ts spells
 * out: a 200 that confirms "this theory exists, you just can't read it yet" IS
 * the spoiler, because a theory's TITLE is its payload. Coverage grows by
 * authoring theories, not by writing code here.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { resolveRelated, theoryEntry } from "@/lib/theories";
import { loadTheories } from "@/lib/theories-load";
import { BRAND } from "@/config/brand";
import TheoryEntry from "@/components/entry/TheoryEntry";
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
  const entry = theoryEntry(loadTheories(), slug, ctx);
  if (entry.state === "uncharted") {
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
    };
  }
  return {
    title: `${entry.data.title} — ${BRAND.shortName}`,
    description: BRAND.tagline,
  };
}

export default async function Page({ params, searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = theoryEntry(loadTheories(), slug, ctx);
  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }
  const related = resolveRelated(canon, world, entry.data.related, ctx.chapter);
  return <TheoryEntry vm={entry.data} related={related} chapter={ctx.chapter} />;
}
