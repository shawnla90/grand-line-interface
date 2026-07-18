/**
 * lib/journey.ts — the cinematic-journey timeline. PURE, no React, no map.
 *
 * Turns the 26 chapter-stamped voyage stops into a screen-recordable flight:
 * given progress t ∈ [0,1] it returns the fractional chapter to sweep to AND
 * the full camera program — zoom, pitch, orbit drift — for that instant. The
 * engine drives the chapter (fog + ship), the map damps toward the schedule's
 * camera; both read this one timeline so they never disagree.
 *
 * THE SHOT LIST, which is the whole point of this file. Measured live before
 * this existed: pitch was 0 for the entire run and the "dwells" were 3-second
 * zoom spikes — every 3D island the app can render was flown over flat,
 * top-down, unseen. So the timeline now owns four kinds of slice, each with a
 * camera program:
 *
 *   travel   — OUT over open sea (zoom ~3, flat): the curved gold route on the
 *              globe is the shot.
 *   dwell    — a 3D island on the route: the DIRECTORY-DIVE camera (zoom 6.4,
 *              pitch 48 — the numbers the ◈ panel already uses, because they
 *              are the ones that make a Blender model read as a place) plus a
 *              slow orbit drift, the walk-around-the-model shot.
 *   moment   — a story beat: 2.5D scene moments frame the stage at pitch 55
 *              with NO orbit (the actors are billboards; orbiting them reveals
 *              the cards), while model spotlights (Marineford, the Gates,
 *              Whisky Peak…) use the dive program at an off-route anchor.
 *   transit  — a VERTICAL experience: the chapter sweeps slowly (not held)
 *              while the camera pitches up and rides along — Skypiea's
 *              Knock-Up Stream climb, Fish-Man Island's dive. The altitude
 *              visuals are already pure functions of chapter; sweeping slowly
 *              through their beats at pitch IS the experience.
 */

export type JourneyStop = { chapter: number; slug: string | null; label: string; deep: boolean };

/**
 * A MOMENT: a beat the journey stops FOR, not just at. `kind: "scene"` is a
 * 2.5D simulation playing at its anchor (dwelling holds `chapterAt` AT the
 * moment's chapter, so the scene's spoiler gate opens exactly during the dwell
 * and never a frame before). `kind: "model"` is a 3D-model spotlight at an
 * anchor the voyage line never touches — Marineford exists on this chart and
 * deserves its shot even though no waypoint slug points at it. `fact` is read
 * from world.events at build time, never copied into this file.
 */
export type JourneyMoment = {
  chapter: number;
  label: string;
  kind?: "scene" | "model";
  fact?: string;
  focus?: [number, number];
  simId?: string;
  /** Authored dwell length in ms (scene moments; from the playback manifest).
   * The dwell's relative weight derives from it, so a 9s scene holds longer
   * than a 6.5s beat; absent = the classic momentWeight dwell. */
  holdMs?: number;
  /** Explicit relative-weight override; wins over holdMs derivation. */
  weight?: number;
  /** Per-moment camera overrides (scene moments; from the playback manifest). */
  zoom?: number;
  pitch?: number;
};

/** A slow chapter sweep with a pitched camera — the vertical rides. */
export type JourneyTransit = {
  fromCh: number;
  toCh: number;
  label: string;
  pitch: number;
  zoom: number;
  /** relative time weight (like dwellWeight, but for a sweep). */
  weight: number;
};

/** What the camera should be doing at an instant of the run. */
export type CamTarget = {
  zoom: number;
  pitch: number;
  /** deg/sec of bearing drift while fully inside a dwell window; 0 = none. */
  orbitDegPerSec: number;
};

type Slice =
  | { kind: "dwell"; t0: number; t1: number; chapter: number }
  | { kind: "travel"; t0: number; t1: number; fromCh: number; toCh: number };

export type Journey = {
  stops: JourneyStop[];
  /** Fractional chapter at progress t∈[0,1]. */
  chapterAt: (t: number) => number;
  /** Full camera program at t. The map DAMPS toward these, it never snaps. */
  camAt: (t: number) => CamTarget;
  /** Camera zoom at t — camAt(t).zoom, kept for existing callers. */
  zoomAt: (t: number) => number;
  /** The current leg's label, for the on-screen caption. */
  labelAt: (t: number) => string;
  /** The moment being dwelt on at t, or null over open sea / plain stops. */
  momentAt: (t: number) => JourneyMoment | null;
  /** Every moment dwell window as [t0, t1] fractions of the run — the caller
   * that owns wall-clock (Atlas) uses these to size the run so an authored
   * holdMs is guaranteed inside its window. */
  momentSpans: () => { t0: number; t1: number; moment: JourneyMoment }[];
};

export type JourneyOpts = {
  outZoom?: number; // sea travel
  deepZoom?: number; // scene moments — the 2.5D stage framing
  diveZoom?: number; // 3D dwells/spotlights — the directory-dive framing
  divePitch?: number; // 3D dwells/spotlights
  momentPitch?: number; // 2.5D scene moments
  orbitDegPerSec?: number; // bearing drift inside a 3D dwell
  travelCapCh?: number; // no single ocean crossing dominates the clock
  dwellWeight?: number; // relative time held at a 3D stop
  momentWeight?: number; // relative time held at a story moment
  rampFrac?: number; // fraction of a dwell window the camera eases over
};

const DEFAULTS: Required<JourneyOpts> = {
  outZoom: 3.0,
  deepZoom: 5.8,
  // The ◈ directory's dive numbers (Atlas.diveTo): the camera that makes a
  // model read as a place. The journey borrows them rather than inventing.
  diveZoom: 6.4,
  divePitch: 48,
  momentPitch: 55,
  orbitDegPerSec: 5,
  travelCapCh: 120,
  // Weights are relative; with the standard route (~1050 travel weight,
  // 8-10 dwells, 5 scene moments, 2 transits) and a 150s run these land at
  // roughly: dwell ≈ 6s, scene moment ≈ 8s, Skypiea ride ≈ 9s.
  dwellWeight: 135,
  momentWeight: 180,
  rampFrac: 0.42,
};

function smooth(x: number): number {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c); // smoothstep
}

/**
 * The on-route 3D stops the camera dives into. Curated, not derived — art
 * direction. Skypiea is NOT here anymore: its experience is the Knock-Up
 * Stream TRANSIT (a dwell at the top was a flat anticlimax); any deep stop
 * whose chapter falls inside a transit's sweep is skipped automatically.
 * Off-route models (Marineford, the Gates, Whisky Peak, Amazon Lily, Mary
 * Geoise) ride the MOMENT mechanism instead — see config/journey stops.
 */
export const DEEP_VOYAGE_SLUGS = new Set<string>([
  "conomi-islands", // Arlong Park
  "loguetown",
  "sabaody-archipelago",
  "fish-man-island",
  "dressrosa",
  "zou",
  "whole-cake-island", // Totto Land
]);

/** The vertical rides. Chapter ranges come from the transition modules'
 * own beat tables (skypiea.ts ASCENT 235-304, fishman.ts DESCENT 602-653);
 * the sweep starts just before so the eruption/dive is seen, and hands back
 * to a travel leg (or dwell) at the far side. */
export const VOYAGE_TRANSITS: JourneyTransit[] = [
  // Skypiea cannot be one linear 72-chapter sweep: the actual climb is only
  // 235→237, so the old schedule spent 2/72 of a nine-second shot on the
  // ascent — roughly a quarter-second. These authored phases give the boat a
  // readable approach, climb, time aloft, and descent while preserving the
  // canonical chapter functions in components/skypiea.ts.
  { fromCh: 233, toCh: 235, label: "Approaching the Knock-Up Stream", pitch: 48, zoom: 4.8, weight: 35 },
  { fromCh: 235, toCh: 237, label: "Riding the Knock-Up Stream", pitch: 60, zoom: 5.4, weight: 170 },
  { fromCh: 237, toCh: 300, label: "Skypiea — above the White Sea", pitch: 48, zoom: 5.6, weight: 90 },
  { fromCh: 300, toCh: 304, label: "Descending from the White Sea", pitch: 55, zoom: 5.2, weight: 75 },
  { fromCh: 304, toCh: 305, label: "Splash-down from Skypiea", pitch: 25, zoom: 4.4, weight: 25 },
  { fromCh: 601, toCh: 607, label: "Diving beneath the Red Line", pitch: 55, zoom: 5.4, weight: 110 },
];

/**
 * Build the timeline. `stops` are the voyage waypoints (ascending chapter);
 * a stop whose slug is in `deepSlugs` is a hero beat. `chapterMax` closes the
 * final leg (the fog keeps revealing past the last stop to the end of the story).
 */
export function buildJourney(
  stops: { chapter: number; slug: string | null; label: string }[],
  chapterMax: number,
  deepSlugs: Set<string> = DEEP_VOYAGE_SLUGS,
  opts: JourneyOpts = {},
  moments: JourneyMoment[] = [],
  transits: JourneyTransit[] = VOYAGE_TRANSITS,
): Journey {
  const o = { ...DEFAULTS, ...opts };

  const marked: JourneyStop[] = stops.map((s) => ({
    chapter: s.chapter,
    slug: s.slug,
    label: s.label,
    deep: s.slug != null && deepSlugs.has(s.slug),
  }));

  const inTransit = (ch: number) => transits.some((tr) => ch >= tr.fromCh && ch <= tr.toCh);

  // Stops, moments and transit-starts interleave into one chapter-ordered beat
  // list. A moment sorts AFTER a stop at the same chapter (arrive, then the
  // scene plays). A deep stop swallowed by a transit's sweep loses its dwell —
  // the ride IS that stop's experience.
  type Beat =
    | { kind: "stop"; ch: number; stop: JourneyStop }
    | { kind: "moment"; ch: number; moment: JourneyMoment }
    | { kind: "transit"; ch: number; transit: JourneyTransit };
  const beats: Beat[] = [
    ...marked.map((stop): Beat => ({ kind: "stop", ch: stop.chapter, stop })),
    ...moments.map((moment): Beat => ({ kind: "moment", ch: moment.chapter, moment })),
    ...transits.map((transit): Beat => ({ kind: "transit", ch: transit.fromCh, transit })),
  ].sort((a, b) => a.ch - b.ch || (a.kind === "stop" ? -1 : 1) - (b.kind === "stop" ? -1 : 1));

  type Raw =
    | { kind: "dwell"; w: number; chapter: number; label: string; moment?: JourneyMoment }
    | { kind: "travel"; w: number; fromCh: number; toCh: number; label: string; transit?: JourneyTransit };
  const raw: Raw[] = [];
  let cursorCh = marked.length ? marked[0].chapter : 1;

  for (let i = 0; i < beats.length; i++) {
    const b = beats[i];
    // A beat inside an already-consumed transit sweep contributes nothing.
    if (b.ch < cursorCh) continue;

    if (b.kind === "transit") {
      const tr = b.transit;
      raw.push({ kind: "travel", w: tr.weight, fromCh: tr.fromCh, toCh: tr.toCh, label: tr.label, transit: tr });
      cursorCh = tr.toCh;
    } else if (b.kind === "stop" && b.stop.deep && !inTransit(b.ch)) {
      raw.push({ kind: "dwell", w: o.dwellWeight, chapter: b.ch, label: b.stop.label });
      cursorCh = b.ch;
    } else if (b.kind === "moment") {
      // A moment with an authored holdMs scales its weight off the 8000ms
      // baseline momentWeight was tuned against (see DEFAULTS) — a 9s scene
      // holds proportionally longer than a 6.5s beat, and relative pacing
      // against travel legs is preserved. `weight` is the explicit override.
      const w =
        b.moment.weight ??
        (b.moment.holdMs != null
          ? o.momentWeight * (b.moment.holdMs / 8000)
          : b.moment.kind === "model"
            ? o.dwellWeight
            : o.momentWeight);
      raw.push({ kind: "dwell", w, chapter: b.ch, label: b.moment.label, moment: b.moment });
      cursorCh = b.ch;
    } else {
      cursorCh = Math.max(cursorCh, b.ch);
    }

    // Travel to the next un-consumed beat (or the end of the story).
    let nextCh = chapterMax;
    let nextLabel = raw.length ? raw[raw.length - 1].label : "";
    for (let j = i + 1; j < beats.length; j++) {
      if (beats[j].ch >= cursorCh) {
        nextCh = beats[j].ch;
        const nb = beats[j];
        nextLabel = nb.kind === "stop" ? nb.stop.label : nb.kind === "moment" ? nb.moment.label : nb.transit.label;
        break;
      }
    }
    const gap = nextCh - cursorCh;
    if (gap > 0) {
      raw.push({ kind: "travel", w: Math.min(gap, o.travelCapCh), fromCh: cursorCh, toCh: nextCh, label: nextLabel });
      cursorCh = nextCh;
    }
  }
  // Close out to chapterMax if the last beat stopped short.
  if (cursorCh < chapterMax) {
    raw.push({
      kind: "travel",
      w: Math.min(chapterMax - cursorCh, o.travelCapCh),
      fromCh: cursorCh,
      toCh: chapterMax,
      label: raw.length ? raw[raw.length - 1].label : "",
    });
  }

  const total = raw.reduce((a, r) => a + r.w, 0) || 1;
  const slices: (Slice & { label: string; moment?: JourneyMoment; transit?: JourneyTransit })[] = [];
  // Every window the camera departs from sea level for, with its targets.
  type CamWindow = { t0: number; t1: number; zoom: number; pitch: number; orbit: number; moment?: JourneyMoment };
  const camWindows: CamWindow[] = [];
  const momentWindows: [number, number, JourneyMoment][] = [];
  let acc = 0;
  for (const r of raw) {
    const t0 = acc / total;
    acc += r.w;
    const t1 = acc / total;
    if (r.kind === "dwell") {
      slices.push({ kind: "dwell", t0, t1, chapter: r.chapter, label: r.label, moment: r.moment });
      const isScene = r.moment?.kind !== "model" && !!r.moment;
      camWindows.push({
        t0, t1,
        zoom: isScene ? (r.moment?.zoom ?? o.deepZoom) : o.diveZoom,
        pitch: isScene ? (r.moment?.pitch ?? o.momentPitch) : o.divePitch,
        orbit: isScene ? 0 : o.orbitDegPerSec,
        moment: r.moment,
      });
      if (r.moment) momentWindows.push([t0, t1, r.moment]);
    } else {
      slices.push({ kind: "travel", t0, t1, fromCh: r.fromCh, toCh: r.toCh, label: r.label, transit: r.transit });
      if (r.transit) {
        camWindows.push({ t0, t1, zoom: r.transit.zoom, pitch: r.transit.pitch, orbit: 0 });
      }
    }
  }

  const findSlice = (t: number) => {
    const c = Math.max(0, Math.min(1, t));
    for (const s of slices) if (c <= s.t1) return s;
    return slices[slices.length - 1];
  };

  const chapterAt = (t: number): number => {
    const s = findSlice(t);
    if (s.kind === "dwell") return s.chapter;
    const u = s.t1 > s.t0 ? (Math.max(s.t0, Math.min(s.t1, t)) - s.t0) / (s.t1 - s.t0) : 0;
    return s.fromCh + (s.toCh - s.fromCh) * u;
  };

  /** Pulse 0→1→0 for a window, ramping over rampFrac of the window's own
   * width on both sides — the camera eases in on approach, out on departure. */
  const pulse = (t: number, w: CamWindow): number => {
    const ramp = (w.t1 - w.t0) * o.rampFrac || 0.02;
    if (t < w.t0) return smooth((t - (w.t0 - ramp)) / ramp);
    if (t > w.t1) return smooth(1 - (t - w.t1) / ramp);
    return 1;
  };

  const camAt = (t: number): CamTarget => {
    let best: CamWindow | null = null;
    let bestP = 0;
    for (const w of camWindows) {
      const p = pulse(t, w);
      if (p > bestP) {
        bestP = p;
        best = w;
      }
    }
    if (!best || bestP <= 0) return { zoom: o.outZoom, pitch: 0, orbitDegPerSec: 0 };
    return {
      zoom: o.outZoom + (best.zoom - o.outZoom) * bestP,
      pitch: best.pitch * bestP,
      // Orbit only once settled — a drifting bearing during the zoom ramp
      // reads as a wobble, not a reveal.
      orbitDegPerSec: bestP >= 0.98 ? best.orbit : 0,
    };
  };

  const zoomAt = (t: number): number => camAt(t).zoom;

  const labelAt = (t: number): string => findSlice(t).label;

  const momentAt = (t: number): JourneyMoment | null => {
    const c = Math.max(0, Math.min(1, t));
    for (const [m0, m1, m] of momentWindows) if (c >= m0 && c <= m1) return m;
    return null;
  };

  const momentSpans = () => momentWindows.map(([t0, t1, moment]) => ({ t0, t1, moment }));

  return { stops: marked, chapterAt, camAt, zoomAt, labelAt, momentAt, momentSpans };
}
