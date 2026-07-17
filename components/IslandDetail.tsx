"use client";

/**
 * components/IslandDetail.tsx — the receipts.
 *
 * This panel exists to render `source_ref` verbatim. Every row in the artifact
 * carries one, and rule 4 says it gets rendered, not just stored. So when the map
 * claims Water 7 sits at lng -73.79, the reader can read the exact sentence that
 * put it there:
 *
 *   "position: derived: region='Paradise'; lng by voyage order 14 (water-7, arc
 *    named after island) | belt model: Grand Line=equator, Red Line=0/180
 *    meridian; deterministic sha256(slug) jitter"
 *
 * That is the difference between an atlas and a picture of one. It is also the
 * fastest way for a reader who knows better to tell us we are wrong.
 */

import type { World, WorldIsland } from "@/lib/canon";
import type { Art } from "@/lib/art";
import { Confidence, Field, FieldGrid, Kicker, Receipts } from "./ui/Panel";

export default function IslandDetail({
  island,
  world,
  art,
  onClose,
}: {
  island: WorldIsland;
  world: World;
  art: Art;
  onClose: () => void;
}) {
  const arc = world.arcs.find((a) => a.slug === island.debutArc);
  // Only the ~24 voyage-waypoint islands carry a real image; everything else has none.
  const image = art.islands[island.slug];

  return (
    <div className="dr-enter border-b border-rope/60 px-5 py-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <Kicker>Island</Kicker>
          <h3 className="font-pirate mt-1.5 truncate text-[21px] leading-tight text-parchment">
            {island.name}
          </h3>
          {island.japanese && (
            <div className="mt-0.5 truncate text-[11px] text-muted-2">
              {island.japanese}
              {island.romaji && <span className="ml-1.5 italic">{island.romaji}</span>}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close island"
          className="shrink-0 rounded-sm border border-rope px-1.5 py-0.5 font-mono text-[10px] text-muted-2 transition-colors hover:border-rope-2 hover:text-parchment"
        >
          ✕
        </button>
      </div>

      {image && (
        <div className="mt-3 overflow-hidden rounded-sm border border-rope/60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={image}
            alt={island.name}
            className="block max-h-[120px] w-full object-cover"
          />
        </div>
      )}

      <FieldGrid className="mt-3">
        <Field label="Debut">
          {island.debutChapter !== null ? `ch. ${island.debutChapter}` : "—"}
        </Field>
        <Field label="Sea">{island.sea}</Field>
        <Field label="First seen">{arc?.name ?? "—"}</Field>
        <Field label="Position" mono>
          {island.lat.toFixed(2)}, {island.lng.toFixed(2)}
        </Field>
      </FieldGrid>

      <Confidence level={island.confidence} className="mt-3" />
      <Receipts sourceRef={island.sourceRef} wikiUrl={island.wikiUrl} className="mt-2" />
    </div>
  );
}
