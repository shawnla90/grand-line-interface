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

const CONFIDENCE_COPY: Record<WorldIsland["confidence"], { label: string; tone: string }> = {
  canon: { label: "Confirmed by a human", tone: "text-gold" },
  derived: { label: "Position derived", tone: "text-gold-2" },
  guess: { label: "Position guessed", tone: "text-muted" },
};

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
  const conf = CONFIDENCE_COPY[island.confidence];
  const arc = world.arcs.find((a) => a.slug === island.debutArc);
  // Only the ~24 voyage-waypoint islands carry a real image; everything else has none.
  const image = art.islands[island.slug];

  return (
    <div className="dr-enter border-b border-rope/60 px-5 py-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">Island</div>
          <h3 className="mt-1.5 truncate text-[17px] leading-tight font-medium text-parchment">
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

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
        <div>
          <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">Debut</dt>
          <dd className="tnum mt-0.5 text-[13px] text-parchment">
            {island.debutChapter !== null ? `ch. ${island.debutChapter}` : "—"}
          </dd>
        </div>
        <div>
          <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">Sea</dt>
          <dd className="mt-0.5 truncate text-[13px] text-parchment">{island.sea}</dd>
        </div>
        <div>
          <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">First seen</dt>
          <dd className="mt-0.5 truncate text-[13px] text-parchment">{arc?.name ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">Position</dt>
          <dd className="tnum mt-0.5 font-mono text-[11px] text-muted">
            {island.lat.toFixed(2)}, {island.lng.toFixed(2)}
          </dd>
        </div>
      </dl>

      <div className={`mt-3 font-mono text-[10px] uppercase tracking-[0.16em] ${conf.tone}`}>
        {conf.label}
      </div>

      {/* The receipt, verbatim. Not a summary of it. */}
      <details className="group mt-2">
        <summary className="cursor-pointer list-none font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2 transition-colors hover:text-muted">
          <span className="group-open:hidden">Show source ▸</span>
          <span className="hidden group-open:inline">Hide source ▾</span>
        </summary>
        <p className="mt-2 border-l border-rope pl-2.5 font-mono text-[10px] leading-relaxed break-words text-muted-2">
          {island.sourceRef}
        </p>
        {island.wikiUrl && (
          <a
            href={island.wikiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-block font-mono text-[10px] text-gold/80 underline underline-offset-2 transition-colors hover:text-gold"
          >
            Fandom entry ↗
          </a>
        )}
      </details>
    </div>
  );
}
