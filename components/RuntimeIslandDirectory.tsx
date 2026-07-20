"use client";

import { useState } from "react";
import runtimeAssets from "@/data/generated/runtime_assets.json";
import { runtimeDirectory, type DirectoryEntry, type RuntimeAsset } from "./runtime-models";

// The original waterfall card remains as provenance/fallback, but the complete
// Wano + Onigashima system supersedes it in the live browser.
const SUPERSEDED = new Set(["wano-waterfall-ascent"]);
const WIRED_ISLANDS = runtimeDirectory(
  ((runtimeAssets as { assets: unknown[] }).assets as unknown as RuntimeAsset[]).filter(
    (asset) => !SUPERSEDED.has(asset.id),
  ),
  ((runtimeAssets as { refused?: { id: string }[] }).refused ?? [])
    .map((item) => item.id)
    .filter((id) => !SUPERSEDED.has(id)),
).filter((entry) => entry.status === "wired");

/**
 * RuntimeIslandDirectory — "here is everything we built in 3D, and how to reach it."
 *
 * Answers a real gap: the models sit at their own anchors around the world, and
 * without this the only way to find one is to already know where and when it is.
 * This lists the islands available at the reader's chapter and flies them into
 * the selected one.
 *
 * It NEVER breaks the reader's place in the story: islands ahead of the reader's
 * chapter stay out of the choices. Viewing an island does not advance the story.
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

  const available = WIRED_ISLANDS.filter((entry) => entry.reveal !== null && chapter >= entry.reveal);
  const currentId = arcSlug ? CURRENT_ARC_MODEL[arcSlug] : undefined;
  const current = currentId ? WIRED_ISLANDS.find((entry) => entry.id === currentId) : undefined;
  const currentReady = !!current?.anchor && current.reveal !== null && chapter >= current.reveal;
  const choices = currentReady && current
    ? [current, ...available.filter((entry) => entry.id !== current.id)]
    : available;

  const viewIsland = (anchor: [number, number]) => {
    setOpen(false);
    onDive(anchor);
  };

  return (
    <div className="pointer-events-auto">
      <button
        type="button"
        data-testid="explore-3d-islands"
        aria-expanded={open}
        aria-controls="runtime-island-choices"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 rounded-md border border-gold/60 bg-ink/90 px-3 py-2 text-left text-parchment shadow-lg backdrop-blur transition-colors hover:border-gold hover:bg-gold/10"
      >
        <span className="text-[11px] font-medium">Explore 3D islands</span>
        <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.12em] text-gold/80">
          {choices.length} available {open ? "▴" : "▾"}
        </span>
      </button>

      {open && (
        <div
          id="runtime-island-choices"
          className="mt-2 max-h-[min(60vh,520px)] w-[260px] overflow-y-auto rounded-md border border-rope/70 bg-ink/95 p-2 shadow-2xl backdrop-blur"
        >
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="text-[11px] font-medium text-parchment">Choose an island</span>
            <button
              type="button"
              aria-label="Close 3D island list"
              onClick={() => setOpen(false)}
              className="rounded px-1.5 py-0.5 text-sm text-muted-2 transition-colors hover:bg-parchment/10 hover:text-parchment"
            >
              ×
            </button>
          </div>
          {choices.map((entry) => (
            <Row
              key={entry.id}
              entry={entry}
              current={currentReady && entry.id === current?.id}
              currentLabel={currentReady && entry.id === current?.id && arcSlug
                ? CURRENT_ARC_LABEL[arcSlug]
                : undefined}
              onView={viewIsland}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * The chapter readout already knows the current arc. This table joins that
 * story truth to the runtime model representing the same place, so a reader at
 * Wano or Egghead appears first in the choices instead of getting lost in the
 * full island list.
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
  current,
  currentLabel,
  onView,
}: {
  entry: DirectoryEntry;
  current: boolean;
  currentLabel?: string;
  onView: (anchor: [number, number]) => void;
}) {
  return (
    <button
      type="button"
      data-testid={current ? "current-arc-3d-dive" : undefined}
      onClick={() => entry.anchor && onView(entry.anchor)}
      className="flex w-full items-center justify-between gap-3 rounded px-2 py-2 text-left text-[11px] text-parchment transition-colors hover:bg-gold/10"
    >
      <span className="min-w-0 truncate">
        {currentLabel ?? entry.label}
        {current && (
          <span className="ml-2 font-mono text-[8px] uppercase tracking-[0.12em] text-gold/70">
            current
          </span>
        )}
      </span>
      <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.12em] text-gold/80">
        View
      </span>
    </button>
  );
}
