/**
 * components/entry/IslandEntry.tsx — an island, at page scale.
 *
 * Everything the rail's IslandDetail shows, plus the four things a rail has no
 * room for and that cost nothing because they are already gated: the arc, the
 * poneglyphs standing here, who is anchored here now, and whether the crew ever
 * called. Each rides a gate that already exists in lib/canon.ts — no new
 * chapter logic is invented for this page.
 *
 * A server component: it only ever receives an entry the server already gated,
 * so there is no fog branch in here at all. The route decides; this renders.
 */

import Link from "next/link";
import type { IslandEntryData } from "@/lib/entry";
import type { Art } from "@/lib/art";
import { Confidence, Field, FieldGrid, Kicker, Panel, Receipts } from "@/components/ui/Panel";
import { poneglyphInk } from "@/components/marks/poneglyph";
import type { PoneglyphKind } from "@/lib/canon";
import { BRAND } from "@/config/brand";

export type IslandExtras = {
  poneglyphs: { slug: string; name: string; kind: string; label: string }[];
  presentCrews: { slug: string; name: string; label: string }[];
  voyageCall: { chapter: number; label: string } | null;
  /** Events the reader has seen that happened here — already gated upstream. */
  events: { slug: string; name: string; kind: string; chapter: number }[];
};

export default function IslandEntry({
  data,
  extras,
  art,
  chapter,
}: {
  data: IslandEntryData;
  extras: IslandExtras;
  art: Art;
  chapter: number;
}) {
  const { island, arcName } = data;
  const image = art.islands[island.slug];

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${chapter}&island=${island.slug}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>Island</Kicker>
        <h1 className="font-pirate mt-2 text-[44px] leading-none text-parchment">{island.name}</h1>
        {island.japanese && (
          <div className="mt-2 text-[13px] text-muted-2">
            {island.japanese}
            {island.romaji && <span className="ml-2 italic">{island.romaji}</span>}
          </div>
        )}
      </header>

      {image && (
        <div className="mt-6 overflow-hidden rounded-md border border-rope/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image} alt={island.name} className="block max-h-[300px] w-full object-cover" />
        </div>
      )}

      <Panel className="mt-6 px-6 py-5">
        <FieldGrid>
          <Field label="Debut">
            {island.debutChapter !== null ? `ch. ${island.debutChapter}` : "—"}
          </Field>
          <Field label="Sea">{island.sea}</Field>
          <Field label="First seen">{arcName ?? "—"}</Field>
          <Field label="Position" mono>
            {island.lat.toFixed(2)}, {island.lng.toFixed(2)}
          </Field>
        </FieldGrid>
        <Confidence level={island.confidence} className="mt-4" />
        <Receipts sourceRef={island.sourceRef} wikiUrl={island.wikiUrl} className="mt-3" />
      </Panel>

      {extras.voyageCall && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>The crew called here</Kicker>
          <p className="mt-2 text-[14px] text-parchment">{extras.voyageCall.label}</p>
          <p className="tnum mt-1 font-mono text-[11px] text-muted-2">
            chapter {extras.voyageCall.chapter}
          </p>
        </Panel>
      )}

      {extras.presentCrews.length > 0 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>Who is here, at chapter {chapter}</Kicker>
          <ul className="mt-3 space-y-2">
            {extras.presentCrews.map((c) => (
              <li key={c.slug} className="flex items-baseline justify-between gap-3">
                <Link
                  href={`/crew/${c.slug}?ch=${chapter}`}
                  className="text-[13px] text-parchment transition-colors hover:text-gold"
                >
                  {c.name}
                </Link>
                <span className="truncate text-right text-[11px] text-muted-2">{c.label}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {extras.events.length > 0 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>It happened here</Kicker>
          <ul className="mt-3 space-y-2">
            {extras.events.map((e) => (
              <li key={e.slug} className="flex items-baseline justify-between gap-3">
                <Link
                  href={`/event/${e.slug}?ch=${chapter}`}
                  className="text-[13px] text-parchment transition-colors hover:text-gold"
                >
                  {e.name}
                </Link>
                <span className="tnum shrink-0 font-mono text-[11px] text-muted-2">
                  ch. {e.chapter}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {extras.poneglyphs.length > 0 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>Written here</Kicker>
          <ul className="mt-3 space-y-2">
            {extras.poneglyphs.map((p) => (
              <li key={p.slug} className="flex items-baseline gap-2">
                <span
                  className="mt-px block h-2.5 w-2 shrink-0 rounded-[1px]"
                  style={{ background: poneglyphInk(p.kind as PoneglyphKind) }}
                  aria-hidden
                />
                <div>
                  <div className="text-[13px] text-parchment">
                    {p.name}
                    {p.kind === "road" && (
                      <span
                        className="ml-2 font-mono text-[9px] uppercase tracking-[0.18em]"
                        style={{ color: poneglyphInk("road") }}
                      >
                        road
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-muted-2">{p.label}</div>
                </div>
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
