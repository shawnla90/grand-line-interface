"use client";

/**
 * components/ChapterDock.tsx — the console.
 *
 * One slider, one number field, one axis toggle, and the voyage strip. Dragging
 * the slider is 1:1 and instant; typing a number and hitting Enter makes the
 * world sweep to it (see the tween in Atlas.tsx).
 *
 * THE EPISODE SLIDER NEEDS ITS OWN POSITION, and this is subtle. Episode ->
 * chapter is many-to-one: 98 filler episodes adapt no chapter at all, so they
 * inherit the chapter the story was already at. If the episode slider's thumb
 * were derived from the chapter (ep -> ch -> ep), then dragging onto filler
 * episode 1084 would resolve to chapter 1057, which resolves back to episode
 * 1085, and the thumb would visibly snap out from under the cursor. So the
 * episode axis carries its own thumb position, while the world underneath stays
 * derived from exactly one number: the chapter.
 */

import type { World, WorldAt, Axis } from "@/lib/canon";
import { SPEEDS, type Speed } from "./Atlas";
import NumberField from "./NumberField";
import AxisToggle from "./AxisToggle";
import ArcTimeline from "./ArcTimeline";

type Props = {
  world: World;
  at: WorldAt;
  axis: Axis;
  onAxis: (a: Axis) => void;
  onChapter: (ch: number) => void;
  episode: number;
  onEpisode: (ep: number) => void;
  playing: boolean;
  speed: Speed;
  onPlayPause: () => void;
  onSpeed: (s: Speed) => void;
};

export default function ChapterDock({
  world, at, axis, onAxis, onChapter, episode, onEpisode,
  playing, speed, onPlayPause, onSpeed,
}: Props) {
  const byChapter = axis === "chapter";

  const value = byChapter ? at.chapter : episode;
  const min = byChapter ? world.chapterMin : world.episodeMin;
  const max = byChapter ? world.chapterMax : world.episodeMax;
  const commit = byChapter ? onChapter : onEpisode;

  const pct = ((value - min) / Math.max(1, max - min)) * 100;

  return (
    <div className="pointer-events-auto border-t border-rope/60 bg-ink/85 px-6 py-4 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1180px] flex-col gap-4 lg:flex-row lg:items-center lg:gap-8">
        {/* the helm: sail the story */}
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={onPlayPause}
            title={playing ? "Pause (Space)" : "Sail the story (Space)"}
            aria-label={playing ? "Pause" : "Play"}
            className={[
              "grid h-9 w-9 place-items-center rounded-sm border font-mono text-[13px] transition-colors",
              playing
                ? "border-gold/60 bg-ink/90 text-gold"
                : "border-rope bg-ink/90 text-muted-2 hover:border-gold/60 hover:text-gold",
            ].join(" ")}
          >
            {playing ? "❚❚" : "▶"}
          </button>
          <div className="flex flex-col gap-0.5">
            {/* speed chips: chapters flow at speed x 2/s */}
            <div className="flex items-center gap-0.5">
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSpeed(s)}
                  className={[
                    "rounded-sm border px-1 py-0.5 font-mono text-[9px] tabular-nums transition-colors",
                    speed === s
                      ? "border-gold/60 text-gold"
                      : "border-transparent text-muted-2 hover:text-muted",
                  ].join(" ")}
                >
                  {s}×
                </button>
              ))}
            </div>
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-muted-2">
              {playing ? "sailing" : "sail"}
            </div>
          </div>
        </div>

        {/* the number */}
        <div className="flex shrink-0 items-center gap-4">
          <div className="w-[122px]">
            <NumberField
              label={byChapter ? "Chapter" : "Episode"}
              value={value}
              min={min}
              max={max}
              onCommit={commit}
            />
          </div>
          <AxisToggle axis={axis} onAxis={onAxis} />
        </div>

        {/* the dial */}
        <div className="min-w-0 flex-1">
          <input
            type="range"
            className="dial"
            aria-label={byChapter ? "Chapter" : "Episode"}
            min={min}
            max={max}
            step={1}
            value={value}
            style={{ ["--pct" as string]: `${pct}%` }}
            onChange={(e) => commit(Number(e.target.value))}
          />

          {/* The cross-reference. In chapter mode this is the honest place to say
              the anime has not caught up yet, rather than clamping to episode
              1162 and pretending. */}
          <div className="mt-0.5 flex justify-between font-mono text-[9px] tabular-nums text-muted-2">
            <span>{min}</span>
            <span className="text-muted">
              {byChapter
                ? at.episode === null
                  ? `chapter ${at.chapter} · not yet animated`
                  : `chapter ${at.chapter} · episode ${at.episode}`
                : `episode ${episode} · chapter ${at.chapter}`}
            </span>
            <span>{max}</span>
          </div>
        </div>

        {/* the voyage */}
        <div className="w-full shrink-0 lg:w-[380px]">
          <ArcTimeline world={world} at={at} onScrub={onChapter} />
        </div>
      </div>
    </div>
  );
}
