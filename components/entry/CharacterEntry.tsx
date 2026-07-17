/**
 * components/entry/CharacterEntry.tsx — a wanted poster, at page scale.
 *
 * One Piece's own UI primitive for "here is a person and what the world thinks
 * they are worth", so the poster IS the page rather than an illustration on it.
 *
 * What is NOT here is the point. The raw canon row for this character carries a
 * present-day bounty, a status, a devil fruit, a crew, a job, an age and a
 * height — nine fields, none of which can be fogged, several of which are
 * outright spoilers at chapter 1 (Luffy's fruit row says "Nika model"; Jinbe's
 * crew row says "Straw Hat Pirates" 448 chapters early). The page cannot print
 * them because it never receives them: it takes a PosterVM, and that type
 * structurally cannot carry them. See lib/entry.ts.
 */

import Link from "next/link";
import type { CharacterEntryData } from "@/lib/entry";
import { Field, FieldGrid, Kicker, Panel, Receipts } from "@/components/ui/Panel";
import { BRAND } from "@/config/brand";
import WantedCard from "@/components/WantedCard";

export default function CharacterEntry({
  data,
  portrait,
  chapter,
}: {
  data: CharacterEntryData;
  portrait?: string;
  chapter: number;
}) {
  const { poster } = data;

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${chapter}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <div className="mt-7 flex flex-col items-center">
        <WantedCard poster={poster} chapter={chapter} portrait={portrait} size="hero" />
      </div>

      <Panel className="mt-7 px-6 py-5">
        <Kicker>What the chart knows</Kicker>
        <FieldGrid className="mt-3">
          <Field label="First seen">ch. {data.debutChapter}</Field>
          <Field label="Origin">{data.origin ?? "—"}</Field>
          <Field label="Birthday">{data.birthday ?? "—"}</Field>
          <Field label="Blood type">{data.bloodType ?? "—"}</Field>
        </FieldGrid>
        <Receipts
          sourceRef={data.wikiSourceRef ? `${data.sourceRef} | ${data.wikiSourceRef}` : data.sourceRef}
          className="mt-4"
        />
      </Panel>

      {poster.bountyHistory.length > 1 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>The bounty, as you read it</Kicker>
          {/* Only rows the reader has reached are in the payload at all — the
              page cannot print a future number because it does not have one. */}
          <ul className="mt-3 space-y-1.5">
            {[...poster.bountyHistory]
              .sort((a, b) => a.asOfChapter - b.asOfChapter)
              .map((b) => (
                <li key={b.order} className="flex items-baseline justify-between gap-3">
                  <span className="tnum font-mono text-[13px] text-gold-2">
                    ฿{b.amount.toLocaleString("en-US")}
                  </span>
                  <span className="tnum font-mono text-[10px] text-muted-2">
                    ch. {b.asOfChapter}
                  </span>
                </li>
              ))}
          </ul>
        </Panel>
      )}

      <p className="font-document mt-8 text-[11px] leading-relaxed text-muted-2 italic">
        Charted against chapter {chapter}. {BRAND.tagline}
      </p>
    </main>
  );
}
