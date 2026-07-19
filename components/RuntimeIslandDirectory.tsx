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
  arcSlug,
  onDive,
}: {
  chapter: number;
  arcSlug: string | null;
  onDive: (anchor: [number, number]) => void;
}) {
  const [open, setOpen] = useState(false);

  const { wired, held } = useMemo(() => {
    // The original waterfall card is still retained as provenance/fallback, but
    // the complete Wano + Onigashima system supersedes it in the live browser.
    // Listing both made the shipped Wano look unfinished even while the full
    // system was wired directly above it.
    const superseded = new Set(["wano-waterfall-ascent"]);
    const d = runtimeDirectory(
      ((runtimeAssets as { assets: unknown[] }).assets as unknown as RuntimeAsset[]).filter(
        (asset) => !superseded.has(asset.id),
      ),
      ((runtimeAssets as { refused?: { id: string }[] }).refused ?? [])
        .map((r) => r.id)
        .filter((id) => !superseded.has(id)),
    );
    return {
      wired: d.filter((e) => e.status === "wired"),
      held: d.filter((e) => e.status !== "wired"),
    };
  }, []);

  const reachable = wired.filter((e) => e.reveal !== null && chapter >= e.reveal).length;
  const currentId = arcSlug ? CURRENT_ARC_MODEL[arcSlug] : undefined;
  const current = currentId ? wired.find((entry) => entry.id === currentId) : undefined;
  const currentReady = !!current?.anchor && current.reveal !== null && chapter >= current.reveal;

  return (
    <div className="pointer-events-auto">
      {currentReady && current && (
        <button
          type="button"
          data-testid="current-arc-3d-dive"
          onClick={() => onDive(current.anchor!)}
          className="mb-1.5 flex w-full items-center justify-between gap-2 rounded-md border border-gold/70 bg-ink/92 px-3 py-2 text-left text-gold shadow-xl backdrop-blur transition-colors hover:border-gold hover:bg-gold/10"
        >
          <span className="font-mono text-[9px] uppercase tracking-[0.16em]">◈ enter</span>
          <span className="min-w-0 flex-1 truncate text-[11px] text-parchment">
            {CURRENT_ARC_LABEL[arcSlug!] ?? current.label}
          </span>
          <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.12em]">3D ↘</span>
        </button>
      )}

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

/**
 * The chapter readout already knows the current arc. This table joins that
 * story truth to the runtime model representing the same place, so a reader at
 * Wano or Egghead gets an immediate, named entrance instead of needing to know
 * that a collapsed asset inventory is secretly the way into the island.
 */
const CURRENT_ARC_MODEL: Record<string, string> = {
  "arlong-park": "conomi-arlong-park",
  loguetown: "loguetown-roger-execution",
  "reverse-mountain": "reverse-mountain-twin-cape-voyage",
  "whisky-peak": "cactus-island-whisky-peak",
  arabasta: "arabasta-kingdom",
  skypiea: "skypiea-sky-system",
  "water-7": "water-7-sea-train-network",
  "enies-lobby": "water-7-sea-train-network",
  "sabaody-archipelago": "sabaody-grove-network",
  "return-to-sabaody": "fish-man-red-line-descent",
  "fish-man-island": "fish-man-island",
  "punk-hazard": "punk-hazard-geographic-system",
  "amazon-lily": "amazon-lily",
  "impel-down": "world-government-tarai-system",
  marineford: "world-government-tarai-system",
  levely: "mary-geoise-red-line",
  dressrosa: "dressrosa-green-bit",
  zou: "zou-zunesha",
  "whole-cake-island": "totto-land-food-geography",
  "wano-country": "wano-onigashima-country-system",
  egghead: "egghead-future-island-system",
  elbaph: "elbaph-adam-world-system",
};

const CURRENT_ARC_LABEL: Record<string, string> = {
  "arlong-park": "Arlong Park",
  loguetown: "Loguetown",
  "reverse-mountain": "Reverse Mountain",
  "whisky-peak": "Whisky Peak",
  arabasta: "Arabasta",
  skypiea: "Skypiea",
  "water-7": "Water 7",
  "enies-lobby": "Water 7 & Enies Lobby",
  "sabaody-archipelago": "Sabaody",
  "return-to-sabaody": "the Fish-Man descent",
  "fish-man-island": "Fish-Man Island",
  "punk-hazard": "Punk Hazard",
  "amazon-lily": "Amazon Lily",
  "impel-down": "the Tarai Current",
  marineford: "the World Government triangle",
  levely: "Mary Geoise",
  dressrosa: "Dressrosa",
  zou: "Zou",
  "whole-cake-island": "Totto Land",
  "wano-country": "Wano & Onigashima",
  egghead: "Egghead",
  elbaph: "Elbaph",
};

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
