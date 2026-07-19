/**
 * app/poneglyphs/page.tsx — the stones, and the road they spell.
 *
 * Entirely derived from data the atlas already ships: world.poneglyphs
 * (canon/poneglyphs.json custody windows, resolved through presenceWindowAt —
 * stones move). This page adds NO new canon; it is the reading surface those
 * seven rows never had.
 *
 * The road tally renders only after the reader has met their first road
 * poneglyph (ch. 818, where the four-stone rule is explained on the page) —
 * before that, even the NUMBER four is a spoiler. The fourth road poneglyph is
 * deliberately absent from the data (its location is the plot; see
 * canon/poneglyphs.json _deliberately_excluded) and the copy owns that
 * honestly rather than pinning a guess.
 *
 * NOTE (Next.js 16): `searchParams` is a Promise.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { loadCanon } from "@/lib/schema";
import { buildWorld, presenceWindowAt, type PoneglyphKind } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { BRAND } from "@/config/brand";
import { Confidence, Kicker, Panel, Receipts } from "@/components/ui/Panel";

export const metadata: Metadata = {
  title: `The Stones — ${BRAND.shortName}`,
  description: "Every poneglyph the reader has met, where it sits, and the road they spell.",
};

type Props = { searchParams: Promise<{ [k: string]: string | string[] | undefined }> };

const KIND_COPY: Record<PoneglyphKind, { label: string; tone: string }> = {
  road: { label: "Road", tone: "text-straw" },
  instructional: { label: "Instructional", tone: "text-gold" },
  historical: { label: "Historical", tone: "text-gold-2" },
  // In the enum for completeness; canon/poneglyphs.json deliberately excludes
  // it (the Rio Poneglyph is the whole history assembled, not a stele).
  rio: { label: "Rio", tone: "text-parchment" },
};

export default async function Page({ searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const sp = await searchParams;
  const ctx = readChapter(world, sp);

  const revealed = world.poneglyphs
    .filter((p) => p.revealedChapter <= ctx.chapter)
    .sort((a, b) => a.revealedChapter - b.revealedChapter);
  const hidden = world.poneglyphs.length - revealed.length;
  const roadCharted = revealed.filter((p) => p.kind === "road").length;

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${ctx.chapter}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>The forbidden library</Kicker>
        <h1 className="font-pirate mt-2 text-[44px] leading-none text-parchment">The Stones</h1>
        <p className="font-document mt-3 max-w-[54ch] text-[14px] leading-relaxed text-muted">
          {ctx.chapterSet ? (
            <>
              Every poneglyph you have met by chapter{" "}
              <span className="tnum text-parchment">{ctx.chapter}</span>, and where it sits —
              stones move, so each one is charted as custody over time, not a pin.
            </>
          ) : (
            <>
              This chart is drawn against a chapter, and you have not said where you are. Add
              ?ch= to the link, or set your chapter on the map and come back.
            </>
          )}
        </p>
      </header>

      {roadCharted > 0 && (
        <Panel className="mt-6 px-6 py-5">
          <Kicker>The road to the last island</Kicker>
          <div className="mt-2 flex items-baseline gap-4">
            <span className="font-pirate text-[36px] leading-none text-straw">
              {roadCharted}<span className="text-muted-2"> / 4</span>
            </span>
            <p className="font-document text-[13px] leading-relaxed text-muted">
              road poneglyphs charted. Four rubbings triangulate Laugh Tale. The fourth is not
              on this chart because its location is the plot — this atlas does not invent
              answers, it waits for them.
            </p>
          </div>
        </Panel>
      )}

      <ul className="mt-6 space-y-4">
        {revealed.map((p) => {
          const custody = presenceWindowAt(p.custody, ctx.chapter);
          const kind = KIND_COPY[p.kind];
          const island = custody?.islandSlug
            ? world.islands.find((i) => i.slug === custody.islandSlug)
            : null;
          return (
            <li key={p.slug}>
              <Panel className="px-6 py-5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <h2 className="font-pirate text-[24px] leading-tight text-parchment">
                    {p.name}
                  </h2>
                  <span
                    className={`font-mono text-[10px] uppercase tracking-[0.16em] ${kind.tone}`}
                  >
                    {kind.label}
                    {p.note ? ` · ${p.note}` : ""}
                  </span>
                </div>
                <div className="tnum mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
                  known to you since ch. {p.revealedChapter}
                </div>

                <div className="mt-3">
                  <Kicker>Custody at your chapter</Kicker>
                  {custody ? (
                    <>
                      <p className="font-document mt-1 text-[14px] leading-relaxed text-parchment">
                        {island ? (
                          <Link
                            href={`/island/${island.slug}?ch=${ctx.chapter}`}
                            className="underline underline-offset-2 transition-colors hover:text-gold"
                          >
                            {custody.label}
                          </Link>
                        ) : (
                          custody.label
                        )}
                      </p>
                      <Receipts sourceRef={custody.sourceRef} className="mt-1.5" />
                      <Confidence level={custody.confidence} className="mt-2" />
                    </>
                  ) : (
                    <p className="font-document mt-1 text-[13px] text-muted-2 italic">
                      Custody uncharted at this chapter — the stone has moved, and where it
                      went is not yours to know yet.
                    </p>
                  )}
                </div>
              </Panel>
            </li>
          );
        })}
      </ul>

      {hidden > 0 && (
        <p className="mt-6 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
          {hidden} {hidden === 1 ? "stone" : "stones"} still buried at your chapter. Sail
          further.
        </p>
      )}

      <footer className="mt-10">
        <p className="font-document text-[11px] leading-relaxed text-muted-2 italic">
          {BRAND.tagline} The wiki lists some thirty &quot;known&quot; stones; this chart
          holds only the ones both revealed to the reader and placeable on a real island —
          the rule canon/poneglyphs.json keeps.
        </p>
      </footer>
    </main>
  );
}
