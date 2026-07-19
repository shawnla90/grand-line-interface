/**
 * app/now/page.tsx — the war table: where everyone stands, as of YOUR chapter.
 *
 * At ?ch=1185 it answers the caught-up reader's question — where is everyone
 * RIGHT NOW — and at ?ch=500 the same page deals an honest 2008 board. One
 * page, one mechanic, both audiences; nothing here is "current" except
 * relative to the dial, which is the whole thesis of the atlas.
 *
 * Gating is boardAtChapter's (lib/board.ts): debut gate + window gate per
 * player, absentees as a count. A missing ?ch fails closed to chapterMin,
 * like every other route.
 *
 * NOTE (Next.js 16): `searchParams` is a Promise.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { boardAtChapter } from "@/lib/board";
import { loadKeyPlayers } from "@/lib/board-load";
import { BRAND } from "@/config/brand";
import { Kicker, Panel, Receipts } from "@/components/ui/Panel";

export const metadata: Metadata = {
  title: `The Board — ${BRAND.shortName}`,
  description: "Where the era's key players stand, as of your chapter.",
};

type Props = { searchParams: Promise<{ [k: string]: string | string[] | undefined }> };

export default async function Page({ searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const sp = await searchParams;
  const ctx = readChapter(world, sp);
  const board = boardAtChapter(loadKeyPlayers(), canon, world, ctx.chapter);

  return (
    <main className="mx-auto max-w-[880px] px-6 py-12">
      <Link
        href={`/?ch=${ctx.chapter}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>The state of the sea</Kicker>
        <h1 className="font-pirate mt-2 text-[44px] leading-none text-parchment">The Board</h1>
        <p className="font-document mt-3 max-w-[58ch] text-[14px] leading-relaxed text-muted">
          {ctx.chapterSet ? (
            <>
              The era&apos;s key players and where they stand at chapter{" "}
              <span className="tnum text-parchment">{ctx.chapter}</span> — in the strongest
              form you have seen them take. The board is endgame-weighted: coverage grows as
              the research does.
            </>
          ) : (
            <>
              This board is dealt against a chapter, and you have not said where you are. It
              is showing chapter one — an empty table. Add ?ch= to the link, or set your
              chapter on the map and come back.
            </>
          )}
        </p>
      </header>

      {board.cards.length === 0 ? (
        <Panel className="mt-8 px-6 py-6">
          <p className="font-document text-[14px] leading-relaxed text-muted">
            Nobody is on your board yet. The players charted here step onto it deep in the
            story — sail further.
          </p>
        </Panel>
      ) : (
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {board.cards.map((card) => (
            <li key={card.slug}>
              <Panel className="h-full px-5 py-4">
                <div className="flex items-baseline justify-between gap-3">
                  <Link
                    href={`/character/${card.slug}?ch=${ctx.chapter}`}
                    className="font-pirate text-[24px] leading-tight text-parchment transition-colors hover:text-gold"
                  >
                    {card.name}
                  </Link>
                </div>
                <div className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-gold/80">
                  {card.role}
                </div>

                <div className="mt-3">
                  <Kicker>Position</Kicker>
                  {card.position ? (
                    <>
                      <p className="font-document mt-1 text-[13px] leading-relaxed text-parchment">
                        {card.position.islandSlug && card.position.islandName ? (
                          <Link
                            href={`/island/${card.position.islandSlug}?ch=${ctx.chapter}`}
                            className="underline underline-offset-2 transition-colors hover:text-gold"
                          >
                            {card.position.label}
                          </Link>
                        ) : (
                          card.position.label
                        )}
                      </p>
                      <div className="tnum mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
                        since ch. {card.position.sinceChapter}
                      </div>
                      <Receipts sourceRef={card.position.sourceRef} className="mt-1.5" />
                    </>
                  ) : (
                    <p className="font-document mt-1 text-[13px] leading-relaxed text-muted-2 italic">
                      Off your chart — no charted position at this chapter.
                    </p>
                  )}
                </div>

                {card.form && (
                  <div className="mt-3">
                    <Kicker>Strongest form you&apos;ve seen</Kicker>
                    <p className="font-document mt-1 text-[13px] text-parchment">
                      {card.form.label}
                      <span className="tnum ml-2 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                        ch. {card.form.sinceChapter}
                      </span>
                    </p>
                  </div>
                )}
              </Panel>
            </li>
          ))}
        </ul>
      )}

      {board.offBoard > 0 && (
        <p className="mt-6 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
          {board.offBoard} {board.offBoard === 1 ? "player" : "players"} not yet on your board.
          Sail further.
        </p>
      )}

      <footer className="mt-10">
        <p className="font-document text-[11px] leading-relaxed text-muted-2 italic">
          {BRAND.tagline} Positions are hand-charted windows, unverified until a human
          confirms every chapter against the manga — and a player the story itself has
          hidden stays hidden here too.
        </p>
      </footer>
    </main>
  );
}
