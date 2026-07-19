/**
 * components/entry/EventEntry.tsx — what happened here, at page scale.
 *
 * A server component: it only ever receives an entry the server already gated
 * (see eventEntry in lib/entry.ts), so there is no fog branch in here at all.
 * Participants link to their character pages AT THE READER'S CHAPTER — the
 * links carry ?ch= so a visible event never becomes a door past the bookmark.
 */

import Link from "next/link";
import type { EventEntryData } from "@/lib/entry";
import type { EventKind } from "@/lib/canon";
import type { Overlay } from "@/lib/overlays";
import { Confidence, Field, FieldGrid, Kicker, Panel, Receipts } from "@/components/ui/Panel";
import { BRAND } from "@/config/brand";

/** Display copy per kind — the enum stays in data, the words live here. */
const KIND_LABEL: Record<EventKind, string> = {
  duel: "Duel",
  battle: "Battle",
  war: "War",
  declaration: "Declaration",
  death: "Death",
  execution: "Execution",
  oath: "Oath",
  escape: "Escape",
  departure: "Departure",
};

const SIGNIFICANCE_LABEL: Record<1 | 2 | 3, string> = {
  1: "An arc beat",
  2: "Saga-defining",
  3: "Era-defining",
};

export default function EventEntry({
  data,
  chapter,
  overlays = [],
}: {
  data: EventEntryData;
  chapter: number;
  /** Pre-gated by overlaysForEvent — this component never re-gates. Empty
   *  until drops land through docs/OVERLAY_INTAKE.md, and that's fine. */
  overlays?: Overlay[];
}) {
  const { event, islandName, arcName } = data;
  const span =
    event.throughChapter !== null && event.throughChapter !== event.occurredChapter
      ? `ch. ${event.occurredChapter}–${event.throughChapter}`
      : `ch. ${event.occurredChapter}`;

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${chapter}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>{KIND_LABEL[event.kind]}</Kicker>
        <h1 className="font-pirate mt-2 text-[40px] leading-none text-parchment">{event.name}</h1>
        <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.16em] text-gold/80">
          {span}
          {arcName ? ` · ${arcName}` : ""}
        </div>
      </header>

      <Panel className="mt-6 px-6 py-5">
        <Kicker>What changed</Kicker>
        <p className="font-document mt-2 text-[14px] leading-relaxed text-muted">
          {event.outcome}
        </p>
      </Panel>

      <Panel className="mt-4 px-6 py-5">
        <FieldGrid>
          <Field label="Where">
            {event.islandSlug ? (
              <Link
                href={`/island/${event.islandSlug}?ch=${chapter}`}
                className="underline underline-offset-2 transition-colors hover:text-gold"
              >
                {islandName ?? event.islandSlug}
              </Link>
            ) : (
              "Open sea"
            )}
          </Field>
          <Field label="Weight">{SIGNIFICANCE_LABEL[event.significance]}</Field>
        </FieldGrid>
      </Panel>

      {overlays.length > 0 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>The page itself</Kicker>
          <ul className="mt-3 space-y-4">
            {overlays.map((o) => (
              <li key={o.slug}>
                {o.kind === "panel" ? (
                  /* eslint-disable-next-line @next/next/no-img-element -- art
                     assets ship at their authored size; the optimizer would
                     re-encode rights-holders' work for no layout gain. */
                  <img
                    src={o.media_path}
                    alt={o.title}
                    className="w-full rounded-sm border border-rope/70"
                  />
                ) : (
                  <video
                    src={o.media_path}
                    className="w-full rounded-sm border border-rope/70"
                    muted
                    loop
                    autoPlay
                    playsInline
                  />
                )}
                <div className="mt-1.5 flex items-baseline justify-between gap-3">
                  <span className="font-document text-[12px] text-muted">{o.title}</span>
                  <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                    {o.credit.license_note}
                  </span>
                </div>
                <Receipts sourceRef={o.credit.source_ref} className="mt-1" />
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel className="mt-4 px-6 py-5">
        <Kicker>Who was there</Kicker>
        <ul className="mt-2 space-y-1.5">
          {event.participants.map((p) => (
            <li key={p.slug} className="flex items-baseline justify-between gap-3">
              <Link
                href={`/character/${p.slug}?ch=${chapter}`}
                className="font-document text-[14px] text-parchment underline underline-offset-2 transition-colors hover:text-gold"
              >
                {p.name}
              </Link>
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2">
                {p.role}
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="mt-4">
        <Confidence
          level={event.confidence}
          label={
            event.verified
              ? "Chapter confirmed by a human"
              : "Unverified — chapter not yet confirmed against the manga"
          }
        />
        <Receipts sourceRef={event.sourceRef} className="mt-2" />
      </div>
    </main>
  );
}
