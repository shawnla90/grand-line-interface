"use client";

/**
 * components/HeroPrompt.tsx — the entire first screen is ONE input.
 *
 *        Where are you?
 *   [  Chapter   1044  ]
 *
 * ...and the world resolves to that exact moment. No nav, no sign-up, no tour.
 * The map is already alive behind this, fully fogged; committing a number
 * dissolves the prompt and sweeps the world open.
 *
 * The presets are deliberately just numbers. A preset labelled "Wano" would spoil
 * the very thing the product exists to protect — the reader already knows where
 * they are, and that is the only fact this screen needs.
 */

import { useState } from "react";
import type { Axis, World } from "@/lib/canon";
import { BRAND } from "@/config/brand";
import NumberField from "./NumberField";
import AxisToggle from "./AxisToggle";

type Props = {
  world: World;
  axis: Axis;
  onAxis: (a: Axis) => void;
  onCommit: (n: number) => void;
};

export default function HeroPrompt({ world, axis, onAxis, onCommit }: Props) {
  const byChapter = axis === "chapter";
  const max = byChapter ? world.chapterMax : world.episodeMax;
  const [draft, setDraft] = useState(byChapter ? 1044 : 1085);

  const presets = byChapter ? [1, 100, 500, 1044, world.chapterMax] : [1, 100, 500, 1085, world.episodeMax];

  return (
    <div className="pointer-events-auto absolute inset-0 z-30 flex items-center justify-center bg-abyss/72 backdrop-blur-[3px]">
      <div className="dr-enter w-full max-w-[560px] px-8">
        <div className="font-pirate text-[19px] tracking-[0.06em] text-gold/85">
          {BRAND.name}
        </div>

        <h1 className="font-pirate mt-5 text-[52px] leading-none tracking-[0.01em] text-parchment sm:text-[64px]">
          {BRAND.prompt}
        </h1>

        <p className="font-document mt-3 max-w-[420px] text-[15px] leading-relaxed text-muted italic">
          {BRAND.promise}
        </p>

        <form
          className="mt-9"
          onSubmit={(e) => {
            e.preventDefault();
            onCommit(draft);
          }}
        >
          <div className="flex items-end justify-between gap-4">
            <div className="min-w-0 flex-1">
              <NumberField
                label={byChapter ? "Chapter" : "Episode"}
                value={draft}
                min={1}
                max={max}
                onCommit={setDraft}
                size="hero"
                autoFocus
              />
            </div>
            <div className="pb-2">
              <AxisToggle axis={axis} onAxis={onAxis} size="hero" />
            </div>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-2">
            {presets.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onCommit(p)}
                className="tnum rounded-sm border border-rope px-2.5 py-1 font-mono text-[11px] text-muted transition-colors hover:border-gold/60 hover:text-gold"
              >
                {p}
              </button>
            ))}

            <button
              type="submit"
              className="ml-auto rounded-sm bg-gold px-5 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-abyss transition-colors hover:bg-gold-2"
            >
              Chart it
            </button>
          </div>
        </form>

        <p className="mt-8 text-[11px] leading-relaxed text-muted-2">
          Everything after your {axis} is fogged — {world.counts.islandsManga} islands, {world.counts.arcs}{" "}
          arcs and a crew of {world.counts.crew}, revealed only as far as you have actually read.
        </p>
      </div>
    </div>
  );
}
