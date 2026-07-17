/**
 * config/east-blue-simulations.ts — the tunable knobs for the East Blue 2.5D
 * story layer. Numbers a human dials in by looking at the map, kept out of the
 * renderer so tuning is a one-file diff (the projection-overrides.ts posture).
 */

/** Build-time flag (inlined by Next). Default OFF is the asset track's hard
 * rule #1; nobody sees a simulation without opting in. */
export const EAST_BLUE_2D_ON = process.env.NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS === "1";

/**
 * The stage's width in metres: actor x = ±1 spans this. MAP-SCALE THEATRE, not
 * a canon measurement — same doctrine as the GLB models' visual_fit, and on
 * this chart the fit is planetary: the atlas paints a fantasy world onto a
 * full 360° globe (the East Blue alone spans ~70° of longitude), so islands
 * are already hundreds of km tall on screen. Measured at the ch51 proof:
 * 33km made Mihawk a 10px speck at zoom 5.2; 600km reads as a story beat
 * (cards ~200px, the sea chart still visible around them).
 */
export const STAGE_SPAN_M = 600_000;

/**
 * Scenes mount at the same zoom the GLB islands cross-fade in
 * (WorldMap's GLB_MIN_ZOOM) — one shared "close enough for the third
 * dimension" threshold instead of two competing ones.
 */
export const SIM_MIN_ZOOM = 4.6;

/** Fade-in ms when a scene mounts; fade-out is the layer removal (instant),
 * because backward scrub must re-fog NOW, not after a courtesy fade. */
export const SIM_FADE_IN_MS = 450;

/* ── the journey's East Blue moments ─────────────────────────────────────────
 * Five story beats the cinematic stops FOR. Each moment's chapter equals its
 * simulation's verified gate, so the scene becomes eligible exactly during the
 * dwell; label and fact are read from world.events AT RUNTIME (never copied
 * here), and every fact's event occurred at or before the moment's chapter —
 * a caption can therefore never say something the reader hasn't reached.
 * `focus` is the scene's anchor (the artifact's own coordinate), pulling the
 * dwell camera off the raw voyage line and onto the stage.
 */

import type { JourneyMoment } from "@/lib/journey";

type MomentDef = {
  chapter: number;
  simId: string;
  /** canon event slug — label + fact + (usually) focus come from this row. */
  event: string;
  /** Only where the scene anchor is NOT the event's coordinate (the vows play
   * on the Reverse Mountain approach, not at Loguetown where the fact lives). */
  focusOverride?: [number, number];
};

const EAST_BLUE_MOMENT_DEFS: MomentDef[] = [
  { chapter: 20, simId: "orange-town-luffy-vs-buggy", event: "buggy-blasted-away" },
  { chapter: 40, simId: "syrup-village-luffy-vs-kuro", event: "kuro-of-a-hundred-plans-falls" },
  { chapter: 51, simId: "baratie-zoro-vs-mihawk", event: "zoro-vs-mihawk-baratie" },
  { chapter: 93, simId: "arlong-park-final-clash", event: "arlong-park-falls" },
  { chapter: 100, simId: "east-blue-grand-line-vows", event: "the-loguetown-escape", focusOverride: [-177, -12] },
];

/** Build the journey's moment list from live canon. Duck-typed on the two
 * event fields we read, so this stays importable without lib/canon. */
export function buildEastBlueMoments(world: {
  events: { slug: string; name: string; outcome: string; lng: number; lat: number; occurredChapter: number }[];
}): JourneyMoment[] {
  const bySlug = new Map(world.events.map((e) => [e.slug, e]));
  const moments: JourneyMoment[] = [];
  for (const def of EAST_BLUE_MOMENT_DEFS) {
    const ev = bySlug.get(def.event);
    // A missing event row means the canon layer changed under us — skip the
    // moment rather than caption with nothing; the journey still runs.
    if (!ev || ev.occurredChapter > def.chapter) continue;
    moments.push({
      chapter: def.chapter,
      label: ev.name,
      fact: ev.outcome,
      focus: def.focusOverride ?? [ev.lng, ev.lat],
      simId: def.simId,
    });
  }
  return moments;
}
