/**
 * components/entry/CrewEntry.tsx — a crew, as of your chapter.
 *
 * Everything here is authored and gated: where they are (a presence window),
 * their ship (the authored vessel, not the ungated boats table), who is aboard
 * (members past their own from_chapter), and whether they hold a seat
 * (statusHoldersAt). Nothing is derived from the 149-row crews table, which has
 * no chapter and therefore no business on a page that fogs.
 */

import Link from "next/link";
import type { CrewEntryData } from "@/lib/entry";
import { Kicker, Panel, Receipts } from "@/components/ui/Panel";
import { crewColor } from "@/lib/crews";
import { FRUIT_TYPE_STYLE, HAKI_STYLE, STATUS_STYLE } from "@/lib/lenses";
import type { HakiType, StatusKind } from "@/lib/canon";
import { BRAND } from "@/config/brand";
import JollyRoger from "@/components/marks/JollyRoger";

export default function CrewEntry({
  data,
  chapter,
}: {
  data: CrewEntryData;
  chapter: number;
}) {
  const ink = crewColor(data.slug);

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${chapter}&focus=crew:${data.slug}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6 flex items-center gap-4">
        <JollyRoger crewSlug={data.slug} size={44} title={data.name} />
        <div>
          <Kicker>Crew</Kicker>
          <h1 className="font-pirate mt-1 text-[40px] leading-none" style={{ color: ink }}>
            {data.name}
          </h1>
        </div>
      </header>

      {data.statuses.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {data.statuses.map((s) => (
            <span
              key={s}
              className="rounded-sm border px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em]"
              style={{
                borderColor: STATUS_STYLE[s as StatusKind].color,
                color: STATUS_STYLE[s as StatusKind].color,
              }}
            >
              {STATUS_STYLE[s as StatusKind].label}
            </span>
          ))}
        </div>
      )}

      <Panel className="mt-6 px-6 py-5">
        <Kicker>Where they are, at chapter {chapter}</Kicker>
        {data.here ? (
          <>
            <p className="mt-2 text-[15px] text-parchment">{data.here.label}</p>
            {data.here.islandSlug && (
              <Link
                href={`/island/${data.here.islandSlug}?ch=${chapter}`}
                className="mt-1 inline-block font-mono text-[10px] text-gold/80 underline underline-offset-2 hover:text-gold"
              >
                Open the island →
              </Link>
            )}
            <Receipts sourceRef={data.here.sourceRef} className="mt-3" />
          </>
        ) : (
          <p className="mt-2 text-[13px] italic text-muted-2">
            Not currently charted. They exist — you have met them — but nothing in the story
            places them anywhere at this chapter.
          </p>
        )}
        {data.vessel && (
          <p className="mt-3 font-mono text-[11px] text-muted">⛵ {data.vessel.name}</p>
        )}
      </Panel>

      {data.members.length > 0 && (
        <Panel className="mt-4 px-6 py-5">
          <Kicker>Aboard, as you have met them</Kicker>
          <ul className="mt-3 space-y-2.5">
            {data.members.map((m) => (
              <li key={m.poster.slug} className="flex items-baseline justify-between gap-3">
                <Link
                  href={`/character/${m.poster.slug}?ch=${chapter}`}
                  className="text-[13px] text-parchment transition-colors hover:text-gold"
                >
                  {m.poster.name}
                </Link>
                <span className="flex shrink-0 items-center gap-2">
                  {m.fruit && (
                    <span
                      className="font-mono text-[9px]"
                      style={{ color: FRUIT_TYPE_STYLE[m.fruit.type].color }}
                    >
                      {m.fruit.name}
                    </span>
                  )}
                  {m.haki.map((h) => (
                    <span
                      key={h}
                      className="font-mono text-[9px]"
                      style={{ color: HAKI_STYLE[h as HakiType].color }}
                    >
                      {HAKI_STYLE[h as HakiType].label}
                    </span>
                  ))}
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
