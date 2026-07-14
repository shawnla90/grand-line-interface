"use client";

/**
 * components/Readout.tsx — "you are here".
 *
 * The instrument's primary display: chapter, episode, arc, saga, crew size,
 * islands revealed. Everything here is derived from one number.
 */

import type { World, WorldAt } from "@/lib/canon";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted-2">{label}</div>
      <div className="tnum mt-1 text-[15px] leading-none text-parchment">{value}</div>
      {sub && <div className="mt-1 text-[10px] leading-tight text-muted-2">{sub}</div>}
    </div>
  );
}

export default function Readout({ at, world }: { at: WorldAt; world: World }) {
  const { stats } = at;

  return (
    <div className="border-b border-rope/60 px-5 py-4">
      <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">You are here</div>

      {/* The arc + saga. Both come from the wiki, in English — canon.sagas is
          machine-translated French and the app never reads it. */}
      <div className="mt-2.5">
        <div className="text-[19px] leading-tight font-medium text-parchment">
          {at.arc ? at.arc.name : "—"}
        </div>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-muted">
          <span>{at.saga ?? "—"}</span>
          {at.arc?.ongoing && (
            <span className="rounded-sm border border-gold-dim/70 px-1 py-px font-mono text-[8px] uppercase tracking-[0.14em] text-gold">
              ongoing
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-4">
        <Stat label="Chapter" value={String(at.chapter)} sub={`of ${world.chapterMax}`} />
        <Stat
          label="Episode"
          value={at.episode === null ? "—" : String(at.episode)}
          // The anime lags the manga. Rather than clamp to the final episode and
          // lie, say so.
          sub={at.notYetAnimated ? "not yet animated" : `of ${world.episodeMax}`}
        />
        <Stat
          label="Islands"
          value={`${stats.islandsRevealed}`}
          sub={`of ${stats.islandsMappable} charted`}
        />
        <Stat label="Crew" value={`${stats.crewSize}`} sub={`of ${stats.crewTotal} aboard`} />
      </div>

      <div className="mt-4">
        <div className="h-px w-full bg-rope/70">
          <div
            className="h-px bg-gold transition-[width] duration-300 ease-out"
            style={{ width: `${Math.round(stats.chapterProgress * 100)}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[9px] tabular-nums text-muted-2">
          <span>
            arc {stats.arcIndex} / {stats.arcTotal}
          </span>
          <span>{Math.round(stats.chapterProgress * 100)}% read</span>
        </div>
      </div>
    </div>
  );
}
