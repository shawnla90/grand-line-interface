/**
 * components/entry/FruitEntry.tsx — a devil fruit, and who you have seen eat it.
 *
 * The user list is the whole page, and where it comes from is the whole point:
 * canon/fruit_reveals.json, never characters[].fruit_id. See lib/entry.ts.
 *
 * The art is keyed by fruit_id and only arrives with the reveal — an unrevealed
 * fruit has no picture here, because a picture is a reveal too.
 */

import Link from "next/link";
import type { FruitEntryData } from "@/lib/entry";
import { Kicker, Panel } from "@/components/ui/Panel";
import { FRUIT_TYPE_STYLE } from "@/lib/lenses";
import type { FruitType } from "@/lib/canon";
import { BRAND } from "@/config/brand";

export default function FruitEntry({
  data,
  art,
  chapter,
}: {
  data: FruitEntryData;
  art?: string;
  chapter: number;
}) {
  const ink = FRUIT_TYPE_STYLE[data.type as FruitType]?.color ?? "#e0b872";

  return (
    <main className="mx-auto max-w-[720px] px-6 py-12">
      <Link
        href={`/?ch=${chapter}&lens=fruit&focus=fruit:${encodeURIComponent(data.type)}`}
        className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 transition-colors hover:text-gold"
      >
        ← {BRAND.name}
      </Link>

      <header className="mt-6">
        <Kicker>Devil fruit</Kicker>
        <h1 className="font-pirate mt-2 text-[40px] leading-none text-parchment">{data.name}</h1>
        <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.16em]" style={{ color: ink }}>
          {data.type}
        </div>
      </header>

      {art && (
        <div className="mt-6 flex justify-center rounded-md border border-rope/60 bg-ink/60 p-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={art} alt={data.name} className="max-h-[220px] object-contain" />
        </div>
      )}

      {data.description && (
        <Panel className="mt-6 px-6 py-5">
          <Kicker>What it does</Kicker>
          <p className="font-document mt-2 text-[14px] leading-relaxed text-muted">
            {data.description}
          </p>
        </Panel>
      )}

      <Panel className="mt-4 px-6 py-5">
        <Kicker>Who you have seen eat it</Kicker>
        <ul className="mt-3 space-y-2">
          {data.users.map((u) => (
            <li key={u.slug} className="flex items-baseline justify-between gap-3">
              <Link
                href={`/character/${u.slug}?ch=${chapter}`}
                className="text-[14px] text-parchment transition-colors hover:text-gold"
              >
                {u.name}
              </Link>
              <span className="tnum shrink-0 font-mono text-[10px] text-muted-2">
                revealed ch. {u.fromChapter}
              </span>
            </li>
          ))}
        </ul>
        {data.users.length > 1 && (
          <p className="mt-3 text-[11px] leading-snug text-muted-2 italic">
            More than one name here is not a mistake. A devil fruit returns to the world when
            its user dies.
          </p>
        )}
      </Panel>

      <p className="font-document mt-8 text-[11px] leading-relaxed text-muted-2 italic">
        Charted against chapter {chapter}. {BRAND.tagline}
      </p>
    </main>
  );
}
