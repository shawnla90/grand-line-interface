/**
 * lib/journey.ts — the cinematic-journey timeline. PURE, no React, no map.
 *
 * Turns the 26 chapter-stamped voyage stops into a ~90s screen-recordable flight:
 * given progress t ∈ [0,1] it returns the fractional chapter to sweep to and the
 * zoom the camera should be at. The engine drives the chapter (fog + ship), the
 * map drives the camera; both read this one schedule so they never disagree.
 *
 * The shape Shawn asked for: stay zoomed OUT over open sea so the curved voyage
 * line reads on the globe, and DWELL with a deep zoom-in at each island we built
 * in 3D so the Blender models are the hero beats. So time is not linear in
 * chapters — long ocean crossings are capped (they'd otherwise eat the whole
 * run), and the 3D stops get a held slice where the chapter barely advances.
 */

export type JourneyStop = { chapter: number; slug: string | null; label: string; deep: boolean };

type Slice =
  | { kind: "dwell"; t0: number; t1: number; chapter: number }
  | { kind: "travel"; t0: number; t1: number; fromCh: number; toCh: number };

export type Journey = {
  stops: JourneyStop[];
  /** Fractional chapter at progress t∈[0,1]. */
  chapterAt: (t: number) => number;
  /** Camera zoom at progress t∈[0,1]: OUT over sea, DEEP at a 3D stop. */
  zoomAt: (t: number) => number;
  /** The current leg's label, for the on-screen caption. */
  labelAt: (t: number) => string;
};

export type JourneyOpts = {
  outZoom?: number; // sea travel
  deepZoom?: number; // at a 3D stop
  travelCapCh?: number; // no single ocean crossing dominates the clock
  dwellWeight?: number; // relative time held at a 3D stop
  rampFrac?: number; // fraction of a neighbouring travel slice the zoom eases over
};

const DEFAULTS: Required<JourneyOpts> = {
  outZoom: 3.0,
  deepZoom: 5.8,
  travelCapCh: 120,
  dwellWeight: 44,
  rampFrac: 0.42,
};

function smooth(x: number): number {
  const c = Math.max(0, Math.min(1, x));
  return c * c * (3 - 2 * c); // smoothstep
}

/**
 * The voyage stops we linger on — the islands we built in 3D that sit on the
 * route. These are the hero beats: the camera dives to show the Blender model.
 * A curated list, not a derived one, on purpose — it is art direction (which
 * stops deserve a spotlight), and hardcoding it keeps the 60KB runtime-assets
 * artifact out of the main bundle. If a model is added to the voyage, add it here.
 * (Skypiea's knock-up stream and whisky-peak have models too but their anchors
 * sit off the raw waypoint — candidates to add once the footage is judged.)
 */
export const DEEP_VOYAGE_SLUGS = new Set<string>([
  "conomi-islands", // Arlong Park
  "loguetown",
  "skypiea", // the Knock-Up Stream — the ship rides the water column up; the hero beat
  "sabaody-archipelago",
  "fish-man-island",
  "dressrosa",
  "zou",
  "whole-cake-island", // Totto Land
]);

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
): Journey {
  const o = { ...DEFAULTS, ...opts };

  const marked: JourneyStop[] = stops.map((s) => ({
    chapter: s.chapter,
    slug: s.slug,
    label: s.label,
    deep: s.slug != null && deepSlugs.has(s.slug),
  }));

  // Weighted slices: a dwell AT each 3D stop, a travel BETWEEN stops, and a final
  // travel from the last stop to chapterMax so the story finishes charting.
  type Raw =
    | { kind: "dwell"; w: number; chapter: number; label: string }
    | { kind: "travel"; w: number; fromCh: number; toCh: number; label: string };
  const raw: Raw[] = [];
  for (let i = 0; i < marked.length; i++) {
    const s = marked[i];
    if (s.deep) raw.push({ kind: "dwell", w: o.dwellWeight, chapter: s.chapter, label: s.label });
    const nextCh = i + 1 < marked.length ? marked[i + 1].chapter : chapterMax;
    const gap = nextCh - s.chapter;
    if (gap > 0) {
      raw.push({
        kind: "travel",
        w: Math.min(gap, o.travelCapCh),
        fromCh: s.chapter,
        toCh: nextCh,
        label: i + 1 < marked.length ? marked[i + 1].label : s.label,
      });
    }
  }

  const total = raw.reduce((a, r) => a + r.w, 0) || 1;
  const slices: (Slice & { label: string })[] = [];
  const deepWindows: [number, number][] = [];
  let acc = 0;
  for (const r of raw) {
    const t0 = acc / total;
    acc += r.w;
    const t1 = acc / total;
    if (r.kind === "dwell") {
      slices.push({ kind: "dwell", t0, t1, chapter: r.chapter, label: r.label });
      deepWindows.push([t0, t1]);
    } else {
      slices.push({ kind: "travel", t0, t1, fromCh: r.fromCh, toCh: r.toCh, label: r.label });
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

  const zoomAt = (t: number): number => {
    // 1 inside a deep dwell, ramping from 0 over rampFrac of the adjacent travel
    // slices, so the camera eases in on approach and out on departure.
    let pulse = 0;
    for (const [d0, d1] of deepWindows) {
      const w = (d1 - d0) * o.rampFrac || 0.02;
      let p: number;
      if (t < d0) p = smooth((t - (d0 - w)) / w);
      else if (t > d1) p = smooth(1 - (t - d1) / w);
      else p = 1;
      pulse = Math.max(pulse, p);
    }
    return o.outZoom + (o.deepZoom - o.outZoom) * pulse;
  };

  const labelAt = (t: number): string => findSlice(t).label;

  return { stops: marked, chapterAt, zoomAt, labelAt };
}
