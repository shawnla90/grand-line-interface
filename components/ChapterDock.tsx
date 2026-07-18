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
import { EPIC_AUDIO_SHIPPABLE } from "@/config/epic-audio-cues";
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
  journey: boolean;
  onJourney: () => void;
  epicJourney: boolean;
  epicElapsedMs: number;
  epicDurationMs: number;
  epicCueLabel: string;
  epicMuted: boolean;
  epicAudioError: string | null;
  onEpicJourney: () => void;
  onEpicMuted: () => void;
  /** ?record=1 only: the one-click record-the-journey button. */
  recordArmed?: boolean;
  recording?: boolean;
  onRecord?: () => void;
  /** Sail-mode story stops (undefined = the story layers are off entirely). */
  storyStops?: boolean;
  onStoryStops?: (on: boolean) => void;
  /** Scene sound opt-in (undefined = no simulations, no chip). The click is
   * the audio-unlock gesture; cold load is always silent. */
  sceneSound?: boolean;
  onSceneSound?: () => void;
};

export default function ChapterDock({
  world, at, axis, onAxis, onChapter, episode, onEpisode,
  playing, speed, onPlayPause, onSpeed, journey, onJourney,
  epicJourney, epicElapsedMs, epicDurationMs, epicCueLabel, epicMuted,
  epicAudioError, onEpicJourney, onEpicMuted,
  recordArmed = false, recording = false, onRecord,
  storyStops, onStoryStops,
  sceneSound, onSceneSound,
}: Props) {
  const byChapter = axis === "chapter";

  const value = byChapter ? at.chapter : episode;
  const min = byChapter ? world.chapterMin : world.episodeMin;
  const max = byChapter ? world.chapterMax : world.episodeMax;
  const commit = byChapter ? onChapter : onEpisode;

  const pct = ((value - min) / Math.max(1, max - min)) * 100;
  const formatClock = (milliseconds: number) => {
    const seconds = Math.max(0, Math.floor(milliseconds / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  };

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
          {/* the short visual cut remains exactly separate from the audio cut. */}
          <button
            type="button"
            onClick={onJourney}
            disabled={epicJourney}
            title={journey ? "Stop the journey" : "Sail the short cinematic Grand Line journey"}
            aria-label={journey ? "Stop journey" : "Play cinematic journey"}
            className={[
              "grid h-9 shrink-0 place-items-center rounded-sm border px-2.5 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
              journey
                ? "border-gold/60 bg-ink/90 text-gold"
                : epicJourney
                  ? "cursor-not-allowed border-rope/40 bg-ink/70 text-muted-2/40"
                  : "border-rope bg-ink/90 text-muted-2 hover:border-gold/60 hover:text-gold",
            ].join(" ")}
          >
            {journey ? "◼ journey" : "⛵ journey"}
          </button>
          {EPIC_AUDIO_SHIPPABLE && (
            <button
              type="button"
              onClick={onEpicJourney}
              title={epicJourney ? "Stop the Epic Journey" : "Play the full audio-led Epic Journey"}
              aria-label={epicJourney ? "Stop Epic Journey" : "Play Epic Journey with audio"}
              className={[
                "grid h-9 shrink-0 place-items-center rounded-sm border px-2.5 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
                epicJourney
                  ? "border-gold/70 bg-gold/10 text-gold shadow-[0_0_18px_rgba(212,175,55,0.16)]"
                  : "border-rope bg-ink/90 text-muted-2 hover:border-gold/60 hover:text-gold",
              ].join(" ")}
            >
              {epicJourney ? "◼ epic" : "♫ epic"}
            </button>
          )}
          {epicJourney && (
            <button
              type="button"
              onClick={onEpicMuted}
              title={epicMuted ? "Unmute Epic Journey" : "Mute Epic Journey"}
              aria-label={epicMuted ? "Unmute Epic Journey" : "Mute Epic Journey"}
              aria-pressed={epicMuted}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-sm border border-rope bg-ink/90 text-[13px] text-muted-2 transition-colors hover:border-gold/60 hover:text-gold"
            >
              {epicMuted ? "🔇" : "🔊"}
            </button>
          )}
          {/* record-the-journey: plays the cinematic AND saves a map-only
              .webm when it ends. Armed by ?record=1 (preserveDrawingBuffer
              is a map-construction decision); the ship/markers are DOM and
              stay out of the export — full fidelity is the OS recorder. */}
          {recordArmed && (
            <button
              type="button"
              onClick={onRecord}
              disabled={recording}
              title={recording ? "Recording — the take saves when the journey ends" : "Record the journey to a .webm (map-only export)"}
              aria-label={recording ? "Recording" : "Record the journey"}
              className={[
                "grid h-9 shrink-0 place-items-center rounded-sm border px-2.5 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
                recording
                  ? "animate-pulse border-red-500/70 bg-ink/90 text-red-400"
                  : "border-rope bg-ink/90 text-muted-2 hover:border-red-400/60 hover:text-red-300",
              ].join(" ")}
            >
              {recording ? "● rec" : "⏺ record"}
            </button>
          )}
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
            {/* story stops: sailing pauses and dives at each story beat.
                Rendered only when the story layers exist at all. */}
            {storyStops !== undefined && onStoryStops && (
              <button
                type="button"
                onClick={() => onStoryStops(!storyStops)}
                title={storyStops ? "Sailing stops for story beats — click to sail straight through" : "Sail straight through — click to stop for story beats"}
                className={[
                  "rounded-sm border px-1 py-0.5 font-mono text-[8px] uppercase tracking-[0.14em] transition-colors",
                  storyStops
                    ? "border-gold/60 text-gold"
                    : "border-transparent text-muted-2 hover:text-muted",
                ].join(" ")}
              >
                ⚑ stops
              </button>
            )}
            {/* scene sound: the opt-in gesture that unlocks the audio
                director. Rendered only when simulations exist at all. */}
            {sceneSound !== undefined && onSceneSound && (
              <button
                type="button"
                onClick={onSceneSound}
                aria-pressed={sceneSound}
                title={sceneSound ? "Scene sound is on — click to silence the stages" : "Turn on scene sound — fights and story beats play their sound design"}
                className={[
                  "rounded-sm border px-1 py-0.5 font-mono text-[8px] uppercase tracking-[0.14em] transition-colors",
                  sceneSound
                    ? "border-gold/60 text-gold"
                    : "border-transparent text-muted-2 hover:text-muted",
                ].join(" ")}
              >
                {sceneSound ? "🔊 sound" : "🔈 sound"}
              </button>
            )}
          </div>
          {epicJourney && (
            <div className="hidden min-w-0 max-w-[160px] flex-col gap-0.5 xl:flex" aria-live="polite">
              <div className="font-mono text-[9px] tabular-nums text-gold/80">
                {formatClock(epicElapsedMs)} / {formatClock(epicDurationMs)}
              </div>
              <div className="truncate font-document text-[10px] italic text-parchment/70">
                {epicAudioError ? "Audio blocked — restart Epic" : epicCueLabel}
              </div>
            </div>
          )}
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
