"use client";

/**
 * components/ArcTimeline.tsx — the voyage, as a scrubber.
 *
 * THE TIMELINE OBEYS THE FOG TOO. This is the part it would be easy to get
 * wrong: a strip listing all 33 arcs by name is itself a spoiler. "Wano Country
 * Arc" sitting on screen at chapter 100 tells a first-time reader something they
 * have not earned yet.
 *
 * So an arc you have not reached renders as an unnamed block. Its name is not in
 * the DOM, not in a title attribute, not in a tooltip. You can scrub into it —
 * it is your book — but the atlas will not read ahead for you.
 */

import type { World, WorldAt, WorldArc } from "@/lib/canon";

type Props = {
  world: World;
  at: WorldAt;
  onScrub: (chapter: number) => void;
};

function arcSpan(a: WorldArc, chapterMax: number) {
  const end = a.chapterEnd ?? chapterMax;
  return Math.max(1, end - a.chapterStart + 1);
}

export default function ArcTimeline({ world, at, onScrub }: Props) {
  const total = world.chapterMax - world.chapterMin + 1;

  return (
    <div className="select-none">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">Voyage</span>
        <span className="font-mono text-[9px] text-muted-2">
          {at.arc ? at.arc.name : "—"}
        </span>
      </div>

      <div className="flex h-7 w-full items-stretch gap-px overflow-hidden rounded-sm">
        {world.arcs.map((a) => {
          const span = arcSpan(a, world.chapterMax);
          const reached = at.chapter >= a.chapterStart;
          const current = at.arc?.slug === a.slug;

          // A future arc is a shape, not a name.
          const label = reached ? a.name : undefined;

          return (
            <button
              key={a.slug}
              type="button"
              aria-label={reached ? `${a.name}, chapter ${a.chapterStart}` : "Unread arc"}
              title={label}
              onClick={() => onScrub(a.chapterStart)}
              style={{ flexGrow: span / total }}
              className={[
                "group relative min-w-[3px] cursor-pointer transition-colors duration-300",
                current
                  ? "bg-gold"
                  : reached
                    ? "bg-gold/35 hover:bg-gold/60"
                    : "bg-rope/50 hover:bg-rope-2/70",
              ].join(" ")}
            >
              {current && (
                <span className="absolute inset-x-0 -bottom-px h-px bg-gold-2 shadow-[0_0_10px_2px_rgba(227,176,75,.7)]" />
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-1 flex justify-between font-mono text-[9px] tabular-nums text-muted-2">
        <span>ch. {world.chapterMin}</span>
        <span className="text-muted">
          {at.chapter >= world.chapterMax ? "the whole world" : `${at.stats.arcIndex} of ${at.stats.arcTotal} arcs`}
        </span>
        <span>ch. {world.chapterMax}</span>
      </div>
    </div>
  );
}
