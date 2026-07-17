/**
 * components/entry/Uncharted.tsx — the one page a fogged entry renders.
 *
 * It takes NO props about what was asked for, because it is rendered for two
 * different situations that must be indistinguishable: an entity beyond the
 * reader's chapter, and an entity that does not exist. If this component could
 * tell them apart, so could a stranger with a list of guesses and a browser —
 * and the difference is the map. See lib/entry.ts:UNCHARTED.
 *
 * `chapterSet` is the ONE thing it varies on, and it is a fact about the URL the
 * reader sent, not about the thing they asked for. Without ?ch we do not know
 * where they are, so we ask; with it, we say what we can honestly say.
 */

import Link from "next/link";
import { BRAND } from "@/config/brand";
import { Kicker, Panel } from "@/components/ui/Panel";

export default function Uncharted({
  chapter,
  chapterSet,
}: {
  chapter: number;
  chapterSet: boolean;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-[680px] flex-col justify-center px-6 py-16">
      <Panel className="px-7 py-8">
        <Kicker>Uncharted</Kicker>

        <h1 className="font-pirate mt-3 text-[38px] leading-none text-parchment">
          {chapterSet ? "Beyond your chapter" : BRAND.prompt}
        </h1>

        <p className="font-document mt-4 text-[15px] leading-relaxed text-muted">
          {chapterSet ? (
            <>
              Nothing here is charted at chapter{" "}
              <span className="tnum text-parchment">{chapter}</span>. Either you have not
              reached it yet, or there is nothing to reach — this atlas will not tell you
              which, because telling you would be the spoiler.
            </>
          ) : (
            <>
              This entry is charted against a chapter, and you have not said where you are.
              Add one to the link — or open the chart and set it there.
            </>
          )}
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            href={chapterSet ? `/?ch=${chapter}` : "/"}
            className="rounded-sm border border-gold/60 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-gold transition-colors hover:bg-gold/10"
          >
            Open the chart ↗
          </Link>
          <span className="font-mono text-[10px] text-muted-2">
            {chapterSet
              ? "Sail further and come back."
              : "The chart asks once, then remembers."}
          </span>
        </div>
      </Panel>

      <p className="font-document mt-5 px-1 text-[11px] leading-relaxed text-muted-2 italic">
        {BRAND.tagline}
      </p>
    </main>
  );
}
