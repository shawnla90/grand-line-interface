/**
 * app/event/[slug]/page.tsx — an event the reader has seen.
 *
 * Charts the events with an authored occurrence in canon/events.json. An event
 * past the reader's bookmark — or a slug that never existed — renders the same
 * Uncharted page, byte-identical, for the reasons lib/entry.ts spells out: a
 * 200 that confirms "the duel exists, you just can't see it" IS the spoiler.
 * Coverage grows by authoring events, not by writing code here.
 *
 * NOTE (Next.js 16): `params` and `searchParams` are both Promises.
 */

import type { Metadata } from "next";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { eventEntry, readChapter } from "@/lib/entry";
import { overlaysForEvent } from "@/lib/overlays";
import { loadOverlays } from "@/lib/overlays-load";
import { BRAND } from "@/config/brand";
import EventEntry from "@/components/entry/EventEntry";
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
  const entry = eventEntry(world, slug, ctx);
  if (entry.state === "uncharted") {
    return {
      title: `Uncharted — ${BRAND.shortName}`,
      description: "Beyond your chapter.",
      robots: { index: false, follow: false },
    };
  }
  return {
    title: `${entry.data.event.name} — ${BRAND.shortName}`,
    description: BRAND.tagline,
  };
}

export default async function Page({ params, searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const ctx = readChapter(world, sp);
  const entry = eventEntry(world, slug, ctx);
  if (entry.state === "uncharted") {
    return <Uncharted chapter={ctx.chapter} chapterSet={ctx.chapterSet} />;
  }
  // Overlays gate through the event (already visible here) plus their own
  // chapter; the registry is empty until docs/OVERLAY_INTAKE.md drops land.
  const overlays = overlaysForEvent(loadOverlays(), slug, ctx.chapter);
  return <EventEntry data={entry.data} chapter={ctx.chapter} overlays={overlays} />;
}
