/**
 * app/theories/page.tsx — the iceberg.
 *
 * Five tiers, surface to abyss, rendered as depth: the page literally darkens
 * as you scroll down, ocean-lit to abyss, using nothing but the atlas's own
 * palette. Everything on it is a pure function of ?ch=, like the map:
 *
 *   - a SURFACED theory renders as a card — title, question, live status;
 *   - a SUBMERGED theory renders as a redacted mass. Not its title blurred —
 *     there is no title in the payload at all (see lib/theories.ts). What ships
 *     is a COUNT per tier, and the count is the page's one documented leak:
 *     you can see how much iceberg is under you, and you cannot read any of it.
 *
 * A missing ?ch fails closed to chapterMin, exactly like the entry pages —
 * a bare /theories hands a crawler the emptiest possible iceberg, not the
 * fullest. The copy invites instead of claiming, mirroring Uncharted.
 *
 * NOTE (Next.js 16): `searchParams` is a Promise.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { loadCanon } from "@/lib/schema";
import { buildWorld } from "@/lib/canon";
import { readChapter } from "@/lib/entry";
import { icebergAtChapter, type IcebergTier, type Tier } from "@/lib/theories";
import { loadTheories } from "@/lib/theories-load";
import { BRAND } from "@/config/brand";
import { Kicker } from "@/components/ui/Panel";
import { StatusChip } from "@/components/entry/TheoryEntry";

export const metadata: Metadata = {
  title: `The Iceberg — ${BRAND.shortName}`,
  description: "Every theory surfaces at a chapter. Scrub the dial and watch the iceberg melt.",
};

type Props = { searchParams: Promise<{ [k: string]: string | string[] | undefined }> };

/** Depth styling per tier — darker and quieter the further down you scroll. */
const TIER_STYLE: Record<Tier, { band: string; depthLabel: string }> = {
  1: { band: "bg-ocean-lit/50", depthLabel: "above the waterline" },
  2: { band: "bg-ocean/60", depthLabel: "at the waterline" },
  3: { band: "bg-hull/70", depthLabel: "below the light" },
  4: { band: "bg-ink/80", depthLabel: "deep water" },
  5: { band: "bg-abyss", depthLabel: "the bottom" },
};

function TierBand({ tier, chapter }: { tier: IcebergTier; chapter: number }) {
  const style = TIER_STYLE[tier.tier];
  return (
    <section className={`${style.band} border-t border-rope/40 px-6 py-8`}>
      <div className="mx-auto max-w-[720px]">
        <div className="flex items-baseline justify-between">
          <Kicker>
            Tier {tier.tier} · {tier.label}
          </Kicker>
          <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
            {style.depthLabel}
          </span>
        </div>

        {tier.surfaced.length === 0 && tier.submerged === 0 && (
          <p className="font-document mt-4 text-[13px] text-muted-2 italic">
            Nothing charted at this depth yet.
          </p>
        )}

        <ul className="mt-4 space-y-3">
          {tier.surfaced.map((t) => (
            <li key={t.slug}>
              <Link
                href={`/theory/${t.slug}?ch=${chapter}`}
                className="block rounded-md border border-rope/70 bg-ink/60 px-5 py-4 backdrop-blur transition-colors hover:border-gold/50"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                  <span className="font-pirate text-[22px] leading-tight text-parchment">
                    {t.title}
                  </span>
                  <StatusChip status={t.status} />
                </div>
                <p className="font-document mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-muted">
                  {t.question}
                </p>
                <div className="mt-2 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
                  surfaced ch. {t.surfacedAt} · {t.evidence.length}{" "}
                  {t.evidence.length === 1 ? "clue" : "clues"} on your trail
                </div>
              </Link>
            </li>
          ))}

          {/* The submerged mass: pure texture, no data. aria-hidden because a
              screen reader should get the count below, not fifty block glyphs. */}
          {Array.from({ length: tier.submerged }, (_, i) => (
            <li key={`submerged-${i}`} aria-hidden="true">
              <div className="select-none rounded-md border border-rope/30 bg-abyss/60 px-5 py-4">
                <div className="font-mono text-[15px] tracking-[0.3em] text-rope">
                  ▓▓▓▓▓▓▓░░▓▓▓▓░░▓▓▓▓▓▓░▓▓
                </div>
                <div className="mt-2 font-mono text-[15px] tracking-[0.3em] text-rope/60">
                  ▓▓░▓▓▓▓▓▓▓░░▓▓▓
                </div>
              </div>
            </li>
          ))}
        </ul>

        {tier.submerged > 0 && (
          <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
            {tier.submerged} {tier.submerged === 1 ? "theory" : "theories"} still submerged at
            your chapter. Sail further.
          </p>
        )}
      </div>
    </section>
  );
}

export default async function Page({ searchParams }: Props) {
  const canon = loadCanon();
  const world = buildWorld(canon);
  const sp = await searchParams;
  const ctx = readChapter(world, sp);
  const iceberg = icebergAtChapter(loadTheories(), ctx.chapter);
  const surfacedTotal = iceberg.reduce((n, t) => n + t.surfaced.length, 0);
  const submergedTotal = iceberg.reduce((n, t) => n + t.submerged, 0);

  return (
    <main className="min-h-dvh">
      <header className="mx-auto max-w-[720px] px-6 pt-12 pb-8">
        <Link
          href={`/?ch=${ctx.chapter}`}
          className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
        >
          ← {BRAND.name}
        </Link>
        <Kicker className="mt-6">What the reader wonders</Kicker>
        <h1 className="font-pirate mt-2 text-[44px] leading-none text-parchment">The Iceberg</h1>
        <p className="font-document mt-3 max-w-[54ch] text-[14px] leading-relaxed text-muted">
          {ctx.chapterSet ? (
            <>
              Every theory surfaces at a chapter, gathers its clues chapter by chapter, and one
              day flips — confirmed or debunked — on the page where you watch it happen. At
              chapter <span className="tnum text-parchment">{ctx.chapter}</span>,{" "}
              <span className="tnum text-parchment">{surfacedTotal}</span> have surfaced and{" "}
              <span className="tnum text-parchment">{submergedTotal}</span> are still down
              there.
            </>
          ) : (
            <>
              This chart is drawn against a chapter, and you have not said where you are. It is
              showing you chapter one — the emptiest sea. Add ?ch= to the link, or set your
              chapter on the map and come back.
            </>
          )}
        </p>
      </header>

      {iceberg.map((tier) => (
        <TierBand key={tier.tier} tier={tier} chapter={ctx.chapter} />
      ))}

      <footer className="bg-abyss px-6 py-10">
        <p className="font-document mx-auto max-w-[720px] text-[11px] leading-relaxed text-muted-2 italic">
          {BRAND.tagline} Theories are hand-charted, unverified until a human confirms every
          chapter against the manga, and gated like everything else: the iceberg will not tell
          you what it is hiding — only that it goes deeper.
        </p>
      </footer>
    </main>
  );
}
