/**
 * components/entry/TheoryEntry.tsx — one theory, at page scale.
 *
 * A server component: it only ever receives a VM the server already gated
 * (theoryEntry in lib/theories.ts), so there is no fog branch in here. The
 * evidence trail is the product — chapter-stamped rows the reader has actually
 * reached, each one a receipt — and the status line at the top is ALLOWED to
 * move: scrub past the flip chapter and the same URL renders a different
 * verdict. Related entities arrive pre-resolved (resolveRelated), so a name
 * only appears if that family's own gate passed.
 */

import Link from "next/link";
import type { RelatedResolved, TheoryStatus, TheoryVM } from "@/lib/theories";
import { TIER_LABEL } from "@/lib/theories";
import { Confidence, Kicker, Panel, Receipts } from "@/components/ui/Panel";
import { BRAND } from "@/config/brand";

/** Display copy per status — the enum stays in data, the words live here. */
const STATUS_COPY: Record<TheoryStatus, { label: string; tone: string }> = {
  open: { label: "Open", tone: "text-muted" },
  partly_confirmed: { label: "Partly confirmed", tone: "text-gold-2" },
  confirmed: { label: "Confirmed", tone: "text-gold" },
  debunked: { label: "Debunked", tone: "text-straw" },
};

export function StatusChip({ status }: { status: TheoryStatus }) {
  const c = STATUS_COPY[status];
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-[0.16em] ${c.tone}`}
    >
      {c.label}
    </span>
  );
}

export default function TheoryEntry({
  vm,
  related,
  chapter,
}: {
  vm: TheoryVM;
  related: RelatedResolved;
  chapter: number;
}) {
  const hasRelated =
    related.characters.length + related.islands.length + related.poneglyphs.length > 0;

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <div className="flex items-baseline justify-between gap-3">
        <Link
          href={`/theories?ch=${chapter}`}
          className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
        >
          ← The iceberg
        </Link>
        <Link
          href={`/?ch=${chapter}`}
          className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
        >
          {BRAND.name} ↗
        </Link>
      </div>

      <header className="mt-6">
        <Kicker>
          Tier {vm.tier} · {TIER_LABEL[vm.tier]}
        </Kicker>
        <h1 className="font-pirate mt-2 text-[40px] leading-none text-parchment">{vm.title}</h1>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <StatusChip status={vm.status} />
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2">
            surfaced ch. {vm.surfacedAt}
          </span>
        </div>
      </header>

      <Panel className="mt-6 px-6 py-5">
        <Kicker>The question</Kicker>
        <p className="font-document mt-2 text-[15px] leading-relaxed text-muted">{vm.question}</p>
        <p className="font-document mt-3 border-l border-rope pl-3 text-[13px] leading-relaxed text-muted-2 italic">
          {vm.statusNote}
        </p>
      </Panel>

      <Panel className="mt-4 px-6 py-5">
        <Kicker>The trail — as far as you&apos;ve sailed</Kicker>
        <ol className="mt-3 space-y-4">
          {vm.evidence.map((e) => (
            <li key={e.chapter} className="flex gap-4">
              <Link
                href={`/?ch=${e.chapter}`}
                className="tnum shrink-0 font-mono text-[11px] text-gold/80 underline-offset-2 transition-colors hover:text-gold hover:underline"
              >
                ch. {e.chapter}
              </Link>
              <div className="min-w-0">
                <p className="font-document text-[14px] leading-relaxed text-parchment">
                  {e.claim}
                </p>
                <Receipts sourceRef={e.source_ref} className="mt-1.5" />
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-4 font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
          The trail grows as you read. This is everything charted at chapter {chapter}.
        </p>
      </Panel>

      {hasRelated && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>Charted alongside</Kicker>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
            {related.characters.map((r) => (
              <li key={`c-${r.slug}`}>
                <Link
                  href={`/character/${r.slug}?ch=${chapter}`}
                  className="font-document text-[13px] text-parchment underline underline-offset-2 transition-colors hover:text-gold"
                >
                  {r.name}
                </Link>
              </li>
            ))}
            {related.islands.map((r) => (
              <li key={`i-${r.slug}`}>
                <Link
                  href={`/island/${r.slug}?ch=${chapter}`}
                  className="font-document text-[13px] text-parchment underline underline-offset-2 transition-colors hover:text-gold"
                >
                  {r.name}
                </Link>
              </li>
            ))}
            {related.poneglyphs.map((r) => (
              <li key={`p-${r.slug}`}>
                <span className="font-document text-[13px] text-parchment">{r.name}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <div className="mt-4">
        <Confidence
          level={vm.confidence}
          label={
            vm.verified
              ? "Chapters confirmed by a human"
              : "Unverified — chapters not yet confirmed against the manga"
          }
        />
      </div>
    </main>
  );
}
