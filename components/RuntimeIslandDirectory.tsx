"use client";

import { useMemo, useState } from "react";
import runtimeAssets from "@/data/generated/runtime_assets.json";
import { runtimeDirectory, type DirectoryEntry, type RuntimeAsset } from "./runtime-models";

/**
 * RuntimeIslandDirectory — "here is everything we built in 3D, and how to reach it."
 *
 * Answers a real gap: the models sit at their own anchors around the world, and
 * without this the only way to find one is to already know where and when it is.
 * This lists them, greys the ones you have not read far enough to see, and flies
 * you into the rest.
 *
 * It NEVER breaks the reader's place in the story: an island whose reveal chapter
 * is ahead of you shows the chapter and is not clickable — the same fog the map
 * keeps, stated as a list. Diving does not advance your chapter; you can only
 * reach what you have already read to.
 */
export function RuntimeIslandDirectory({
  chapter,
  onDive,
}: {
  chapter: number;
  onDive: (anchor: [number, number]) => void;
}) {
  const [open, setOpen] = useState(false);

  const { wired, held } = useMemo(() => {
    const d = runtimeDirectory(
      (runtimeAssets as { assets: unknown[] }).assets as unknown as RuntimeAsset[],
      ((runtimeAssets as { refused?: { id: string }[] }).refused ?? []).map((r) => r.id),
    );
    return {
      wired: d.filter((e) => e.status === "wired"),
      held: d.filter((e) => e.status !== "wired"),
    };
  }, []);

  const reachable = wired.filter((e) => e.reveal !== null && chapter >= e.reveal).length;

  return (
    <div className="pointer-events-auto">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-md border border-rope/70 bg-ink/85 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-2 shadow-lg backdrop-blur transition-colors hover:border-gold/50 hover:text-parchment"
      >
        <span aria-hidden>◈</span> 3D islands
        <span className="text-gold/80">{reachable}</span>
        <span className="text-muted-2/60">/ {wired.length}</span>
        <span className="text-muted-2/50">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="mt-2 max-h-[min(60vh,520px)] w-[236px] overflow-y-auto rounded-md border border-rope/70 bg-ink/92 p-1.5 shadow-2xl backdrop-blur">
          {wired.map((e) => (
            <Row key={e.id} entry={e} chapter={chapter} onDive={onDive} />
          ))}

          {held.length > 0 && (
            <div className="mt-2 border-t border-rope/40 px-2 pt-2 pb-1">
              <div className="font-mono text-[8px] uppercase tracking-[0.2em] text-muted-2/70">
                Not yet charted in 3D
              </div>
              <div className="mt-1 text-[10px] leading-snug text-muted-2/80">
                {held.map((e) => e.label).join(" · ")}
              </div>
              <div className="mt-1 text-[9px] leading-snug text-muted-2/55">
                Awaiting verification or asset fixes — not a missing feature.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({
  entry,
  chapter,
  onDive,
}: {
  entry: DirectoryEntry;
  chapter: number;
  onDive: (anchor: [number, number]) => void;
}) {
  const ready = entry.reveal !== null && chapter >= entry.reveal;
  if (!ready) {
    return (
      <div className="flex items-center justify-between rounded px-2 py-1.5 text-[11px] text-muted-2/45">
        <span className="truncate">{entry.label}</span>
        <span className="ml-2 shrink-0 font-mono text-[9px] tabular-nums">ch {entry.reveal}</span>
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={() => entry.anchor && onDive(entry.anchor)}
      className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-[11px] text-parchment transition-colors hover:bg-gold/10"
    >
      <span className="truncate">{entry.label}</span>
      <span className="ml-2 shrink-0 font-mono text-[9px] uppercase tracking-[0.12em] text-gold/70">
        dive ↘
      </span>
    </button>
  );
}
