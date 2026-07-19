/**
 * app/fruits/page.tsx — the devil fruit codex, as far as you've read it.
 *
 * Every fruit the reader has met by ?ch= — reveal-gated by the fruitEntry
 * rule (authored reveals, never the raw fruit_id join), holders listed only
 * once THEIR reveal has passed, and each fruit's lineage (inheritances,
 * thefts, prizes) as a chapter-gated chain. Fruits not yet met ship as a
 * count. A missing ?ch fails closed to chapterMin, like every other route.
 *
 * NOTE (Next.js 16): `searchParams` is a Promise.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { fruitCodexAtChapter, type LineageKind } from "@/lib/fruits";
import { loadFruitLineages } from "@/lib/fruits-load";
import { BRAND } from "@/config/brand";
import { Kicker, Panel, Receipts } from "@/components/ui/Panel";

export const metadata: Metadata = {
  title: `The Codex — ${BRAND.shortName}`,
  description: "Every devil fruit the reader has met, its holders, and where it has been.",
};

type Props = { searchParams: Promise<{ [k: string]: string | string[] | undefined }> };

const KIND_LABEL: Record<LineageKind, string> = {
  revealed: "Revealed",
  inherited: "Inherited",
  taken: "Taken",
  staked: "Staked",
  lore: "Lore",
};

export default async function Page({ searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const sp = await searchParams;
  const ctx = readChapter(world, sp);
  const codex = fruitCodexAtChapter(world, loadFruitLineages(), ctx.chapter);

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${ctx.chapter}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>The sea&apos;s curses</Kicker>
        <h1 className="font-pirate mt-2 text-[44px] leading-none text-parchment">The Codex</h1>
        <p className="font-document mt-3 max-w-[54ch] text-[14px] leading-relaxed text-muted">
          {ctx.chapterSet ? (
            <>
              Every devil fruit you have met by chapter{" "}
              <span className="tnum text-parchment">{ctx.chapter}</span> — who carries it, and
              where it has been. A fruit outlives its eater; the heavy ones have lineages.
            </>
          ) : (
            <>
              This codex is written against a chapter, and you have not said where you are.
              Add ?ch= to the link, or set your chapter on the map and come back.
            </>
          )}
        </p>
      </header>

      {codex.revealed.length === 0 ? (
        <Panel className="mt-8 px-6 py-6">
          <p className="font-document text-[14px] leading-relaxed text-muted">
            No fruit is charted at your chapter yet. The first ones surface early — sail on.
          </p>
        </Panel>
      ) : (
        <ul className="mt-8 space-y-4">
          {codex.revealed.map((f) => (
            <li key={f.slug}>
              <Panel className="px-6 py-5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <Link
                    href={`/fruit/${f.slug}?ch=${ctx.chapter}`}
                    className="font-pirate text-[24px] leading-tight text-parchment transition-colors hover:text-gold"
                  >
                    {f.name}
                  </Link>
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-gold/80">
                    {f.type}
                  </span>
                </div>
                <div className="tnum mt-1 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
                  known to you since ch. {f.firstKnown}
                </div>

                {f.users.length > 0 && (
                  <div className="mt-3">
                    <Kicker>Held by</Kicker>
                    <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                      {f.users.map((u) => (
                        <li key={u.slug}>
                          <Link
                            href={`/character/${u.slug}?ch=${ctx.chapter}`}
                            className="font-document text-[13px] text-parchment underline underline-offset-2 transition-colors hover:text-gold"
                          >
                            {u.name}
                          </Link>
                          <span className="tnum ml-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                            ch. {u.fromChapter}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {f.lineage.length > 0 && (
                  <div className="mt-3 border-t border-rope/60 pt-3">
                    <Kicker>Where it has been</Kicker>
                    <ol className="mt-2 space-y-2.5">
                      {f.lineage.map((e) => (
                        <li key={e.chapter} className="flex gap-3">
                          <span className="tnum shrink-0 font-mono text-[10px] text-gold/80">
                            ch. {e.chapter}
                          </span>
                          <div className="min-w-0">
                            <span className="mr-2 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                              {KIND_LABEL[e.kind]}
                            </span>
                            <span className="font-document text-[13px] leading-relaxed text-muted">
                              {e.note}
                            </span>
                            <Receipts sourceRef={e.source_ref} className="mt-1" />
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </Panel>
            </li>
          ))}
        </ul>
      )}

      {codex.hidden > 0 && (
        <p className="mt-6 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
          {codex.hidden} charted {codex.hidden === 1 ? "fruit" : "fruits"} you have not met
          yet. Sail further.
        </p>
      )}

      <footer className="mt-10">
        <p className="font-document text-[11px] leading-relaxed text-muted-2 italic">
          {BRAND.tagline} Thirty-five of the corpus&apos;s 213 fruits are chartable — the ones
          with an authored, chapter-stamped reveal. Coverage grows by authoring reveals, not
          by trusting the encyclopedia: the encyclopedia lied about at least one fruit for
          eight hundred years.
        </p>
      </footer>
    </main>
  );
}
