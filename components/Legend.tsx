"use client";

/**
 * components/Legend.tsx — the confidence key, with live counts.
 *
 * ARCHITECTURE RULE 4, MADE VISIBLE: "Every authored row carries source_ref and
 * canon_confidence. This is rendered in the UI, not just stored."
 *
 * A pin a machine derived from voyage order must not look like a pin a human
 * confirmed against the manga. So confidence is carried by the pin's GEOMETRY,
 * not by a colour a colour-blind reader would miss:
 *
 *   solid disc   canon    — a human checked this
 *   hollow ring  derived  — placed from region + voyage order
 *   ghost dot    guess    — no chapter, no region: an honest placement
 *
 * The counts are live, and right now they read `canon 0`. Every one of the 256
 * mappable islands was positioned by a script. Saying so is the whole difference
 * between a reference work and a repackaging — and it is an open invitation to
 * the fandom to correct it.
 */

import type { World, WorldAt } from "@/lib/canon";

function Swatch({ kind }: { kind: "canon" | "derived" | "guess" | "fog" }) {
  const base = "block rounded-full";
  if (kind === "canon")
    return <span className={`${base} h-2.5 w-2.5 bg-gold ring-1 ring-parchment/70`} />;
  if (kind === "derived")
    return <span className={`${base} h-2.5 w-2.5 border-[1.5px] border-gold-2 bg-gold/15`} />;
  if (kind === "guess") return <span className={`${base} h-2 w-2 bg-muted-2/60`} />;
  return <span className={`${base} h-1.5 w-1.5 bg-muted-2/40`} />;
}

function Row({
  kind,
  label,
  note,
  count,
}: {
  kind: "canon" | "derived" | "guess" | "fog";
  label: string;
  note: string;
  count: number | null;
}) {
  return (
    <li className="flex items-start gap-2.5">
      <span className="mt-[3px] flex w-3 justify-center">
        <Swatch kind={kind} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className="text-[11px] text-parchment">{label}</span>
          {count !== null && (
            <span
              className={`tnum font-mono text-[10px] ${
                kind === "canon" && count === 0 ? "text-straw" : "text-muted-2"
              }`}
            >
              {count}
            </span>
          )}
        </span>
        <span className="mt-px block text-[10px] leading-snug text-muted-2">{note}</span>
      </span>
    </li>
  );
}

export default function Legend({ world, at, showOffCanon }: { world: World; at: WorldAt; showOffCanon: boolean }) {
  const pc = world.counts.positionConfidence;

  // Count what is ACTUALLY PLOTTED, not what exists. The off-canon layer is where
  // the `guess` tier lives (no chapter, no region — nothing to derive a position
  // from), so with that layer off the guess count is genuinely zero and the legend
  // says so rather than advertising a pin style that is nowhere on screen.
  let canon = 0;
  let derived = 0;
  let guess = 0;
  const tally = (c: "canon" | "derived" | "guess") => {
    if (c === "canon") canon++;
    else if (c === "derived") derived++;
    else guess++;
  };
  for (const i of at.visibleIslands) tally(i.confidence);
  if (showOffCanon) {
    for (const i of world.islands) {
      if (i.status !== "manga" || i.debutChapter === null) tally(i.confidence);
    }
  }

  return (
    <div className="w-[254px] rounded-md border border-rope/70 bg-ink/90 p-3.5 shadow-2xl backdrop-blur">
      <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
        How much to trust this pin
      </div>

      <ul className="mt-2.5 space-y-2">
        <Row kind="canon" label="Confirmed" note="A human checked the position." count={canon} />
        <Row
          kind="derived"
          label="Derived"
          note="Placed from region + voyage order."
          count={derived}
        />
        <Row kind="guess" label="Guessed" note="No chapter, no region." count={guess} />
        <Row
          kind="fog"
          label="Beyond you"
          note="Charted later in the story."
          count={at.foggedIslands.length}
        />
      </ul>

      {showOffCanon && (
        <p className="mt-2.5 border-t border-rope/60 pt-2.5 text-[10px] leading-snug text-muted-2">
          Gold is in the manga. <span className="text-muted">Grey is not</span> — film, anime-only and
          game locations, shown at the same confidence geometry but off the story&apos;s timeline.
        </p>
      )}

      {pc.canon === 0 && (
        <p className="mt-3 border-t border-rope/60 pt-2.5 text-[10px] leading-snug text-muted-2">
          <span className="text-straw">Not one pin here is human-confirmed.</span> All{" "}
          <span className="tnum">{world.counts.islandsManga}</span>{" "}
          positions were derived by a
          script from each island&apos;s sea and its place in the voyage. Corrections welcome — that
          is the point of showing you.
        </p>
      )}
    </div>
  );
}
