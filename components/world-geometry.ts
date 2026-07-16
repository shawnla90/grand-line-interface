/**
 * components/world-geometry.ts — the One Piece planet, generated from code.
 *
 * There are no tiles, no sprites, no fonts and no external URLs anywhere in this
 * map. The entire world is GeoJSON built at module load. It works offline, it
 * costs nothing to serve, and it cannot rot when someone else's CDN goes away.
 *
 * ============================================================================
 * THE MODEL — this must agree with canon/islands.coords.json or every pin lies
 * ============================================================================
 * canon/islands.coords.json:_model states it exactly:
 *
 *   "Grand Line = equator (lat 0), Red Line = the 0/180 meridian. They quarter
 *    the globe: North Blue upper-left, West Blue upper-right, East Blue
 *    lower-left, South Blue lower-right. Paradise runs lng -180..0, New World
 *    0..180, so longitude reads as voyage progress."
 *
 * Two perpendicular great circles. They intersect at exactly two points, and the
 * canon reading of those points is the reason longitude is meaningful:
 *
 *   lng -180 / +180, lat 0  = Reverse Mountain — the entrance to the Grand Line
 *   lng    0,        lat 0  = the Red Line crossing — Sabaody / Fish-Man Island
 *                             / Mary Geoise, the midpoint of the voyage
 *
 * So sailing the story = travelling left to right. Chapter 1 is far west, the
 * Red Line is dead centre, Laugh Tale is far east. The map is a progress bar
 * that happens to be a planet.
 *
 * Verified against the real pins in data/canon.json:
 *   Grand Line sea lane   |lat| <= 8.7    -> belts start outside it, at 9.5
 *   Calm Belt islands      lat 11.8..13.4 -> inside the 9.5..17 bands
 *   Blue islands          |lat| >= 19.4   -> inside the >= 17 quadrants
 *   Paradise  lng -171..-4.8   New World  lng 10.4..173.9
 */

import type { FeatureCollection, Feature, Polygon, LineString } from "geojson";

/** Where the Grand Line sea lane ends and the Calm Belts begin. */
const BELT_INNER = 9.5;
/** Where the Calm Belts end and the four Blues begin. */
const BELT_OUTER = 17;
/** Polygons stop short of the true pole: a fill whose edge is a single point
 *  subdivides badly on a globe. The background shows through, which is correct —
 *  nobody has mapped the poles of this planet either. */
const POLE = 89;

/* -------------------------------------------------------------------------- */
/* densification                                                               */
/* -------------------------------------------------------------------------- */

/**
 * A straight line in lng/lat space is NOT a straight line on a globe. MapLibre
 * subdivides geometry for globe rendering, but two-point geometry gives it
 * nothing to work with at the edges. Densifying first makes every belt and
 * quadrant curve correctly in both projections, and costs a few hundred floats.
 */
function lerpRow(lngA: number, lngB: number, lat: number, steps = 96): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i <= steps; i++) out.push([lngA + ((lngB - lngA) * i) / steps, lat]);
  return out;
}

function lerpCol(lng: number, latA: number, latB: number, steps = 96): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i <= steps; i++) out.push([lng, latA + ((latB - latA) * i) / steps]);
  return out;
}

/** A densified lng/lat quad, wound as a closed ring. */
function quad(
  lngA: number,
  lngB: number,
  latA: number,
  latB: number,
  props: Record<string, unknown>,
): Feature<Polygon> {
  const ring: [number, number][] = [
    ...lerpRow(lngA, lngB, latA),
    ...lerpCol(lngB, latA, latB).slice(1),
    ...lerpRow(lngB, lngA, latB).slice(1),
    ...lerpCol(lngA, latB, latA).slice(1),
  ];
  return { type: "Feature", properties: props, geometry: { type: "Polygon", coordinates: [ring] } };
}

function line(coords: [number, number][], props: Record<string, unknown>): Feature<LineString> {
  return { type: "Feature", properties: props, geometry: { type: "LineString", coordinates: coords } };
}

/**
 * Fill a lng/lat box with 45° diagonal strokes — cross-hatch, generated as real
 * geometry. A MapLibre fill-pattern would need a raster sprite served from a URL,
 * which is the one thing this map may not have; hatch-as-geometry stays offline.
 * Each stroke is clipped to the box (so it never bleeds past the Calm Belt) and
 * lightly densified so it curves correctly on the globe.
 */
function hatchLines(
  lngA: number,
  lngB: number,
  latA: number,
  latB: number,
  spacing: number,
  id: string,
): Feature<LineString>[] {
  const out: Feature<LineString>[] = [];
  // Strokes lie on lng = lat + k. Sweep k so every stroke crosses the box.
  let n = 0;
  for (let k = lngA - latB; k <= lngB - latA; k += spacing) {
    const lo = Math.max(latA, lngA - k);
    const hi = Math.min(latB, lngB - k);
    if (hi - lo <= 0.01) continue;
    const seg: [number, number][] = [];
    const steps = 6;
    for (let i = 0; i <= steps; i++) {
      const lat = lo + ((hi - lo) * i) / steps;
      seg.push([lat + k, lat]);
    }
    out.push(line(seg, { id: `${id}-${n++}` }));
  }
  return out;
}

/* -------------------------------------------------------------------------- */
/* the world                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * The four Blues, as quadrants of the two great circles.
 *
 * Every quadrant is split at lng 0 anyway by the Red Line, so no polygon ever
 * spans 360 degrees of longitude — which is what keeps the antimeridian from
 * turning a fill inside out.
 */
export const BLUES: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    quad(-180, 0, BELT_OUTER, POLE, { id: "north-blue", name: "North Blue" }),
    quad(0, 180, BELT_OUTER, POLE, { id: "west-blue", name: "West Blue" }),
    quad(-180, 0, -POLE, -BELT_OUTER, { id: "east-blue", name: "East Blue" }),
    quad(0, 180, -POLE, -BELT_OUTER, { id: "south-blue", name: "South Blue" }),
  ],
};

/** The two Calm Belts, flanking the Grand Line. Windless, and full of Sea Kings. */
export const CALM_BELTS: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    quad(-180, 0, BELT_INNER, BELT_OUTER, { id: "calm-belt-nw" }),
    quad(0, 180, BELT_INNER, BELT_OUTER, { id: "calm-belt-ne" }),
    quad(-180, 0, -BELT_OUTER, -BELT_INNER, { id: "calm-belt-sw" }),
    quad(0, 180, -BELT_OUTER, -BELT_INNER, { id: "calm-belt-se" }),
  ],
};

/** Cross-hatch inside the Calm Belts — the dead, windless water reads as danger. */
export const CALM_BELT_HATCH: FeatureCollection<LineString> = {
  type: "FeatureCollection",
  features: [
    ...hatchLines(-180, 180, BELT_INNER, BELT_OUTER, 6, "cbh-n"),
    ...hatchLines(-180, 180, -BELT_OUTER, -BELT_INNER, 6, "cbh-s"),
  ],
};

/**
 * The Grand Line sea-lane: the navigable channel |lat| <= BELT_INNER down the
 * equator, split at lng 0 so Paradise and the New World can read as different
 * seas. The gold centreline (GRAND_LINE) still runs on top of this band.
 */
export const GRAND_LINE_LANE: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    quad(-180, 0, -BELT_INNER, BELT_INNER, { id: "lane-paradise", half: "paradise" }),
    quad(0, 180, -BELT_INNER, BELT_INNER, { id: "lane-new-world", half: "new-world" }),
  ],
};

/**
 * Open-ocean depth: two polar bands (|lat| >= 55) darkened, so the sea deepens
 * toward the edges of the chart instead of sitting at one flat navy everywhere.
 */
export const POLAR_DEEP: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    quad(-180, 0, 55, POLE, { id: "deep-nw" }),
    quad(0, 180, 55, POLE, { id: "deep-ne" }),
    quad(-180, 0, -POLE, -55, { id: "deep-sw" }),
    quad(0, 180, -POLE, -55, { id: "deep-se" }),
  ],
};

/**
 * The Grand Line (the equator) and the Red Line (the 0/180 meridian).
 *
 * The Red Line is drawn as two meridians because a great circle through the
 * poles is two half-meridians 180 degrees apart. In mercator the lng-180 half
 * lands on the antimeridian and MapLibre's world copies render it at both edges;
 * on the globe the two halves close into a single ring.
 */
export const GRAND_LINE: FeatureCollection<LineString> = {
  type: "FeatureCollection",
  features: [
    line(lerpRow(-180, 0, 0, 128), { id: "paradise", name: "Paradise" }),
    line(lerpRow(0, 180, 0, 128), { id: "new-world", name: "New World" }),
  ],
};

export const RED_LINE: FeatureCollection<LineString> = {
  type: "FeatureCollection",
  features: [
    line(lerpCol(0, -POLE, POLE, 128), { id: "red-line-0" }),
    // The far half of the ring, drawn at BOTH antimeridian edges. The map renders
    // a single world copy (this is a chart, not a navigation map), so geometry at
    // lng 180 would otherwise only appear on the right edge and the flat view
    // would look asymmetric. On the globe the two coincide into one meridian.
    line(lerpCol(180, -POLE, POLE, 128), { id: "red-line-180" }),
    line(lerpCol(-180, -POLE, POLE, 128), { id: "red-line-180w" }),
  ],
};

/**
 * The Red Line as a CONTINENT, not a stroke: a banded landmass along the 0/180
 * meridian. Width gives it presence (it is the wall that halves the world) and
 * on the globe it fills the antimeridian seam. Drawn under the red centre-lines,
 * which then read as its coastlines.
 */
const RED_HALF_WIDTH = 3.2;
export const RED_LINE_LAND: FeatureCollection<Polygon> = {
  type: "FeatureCollection",
  features: [
    quad(-RED_HALF_WIDTH, RED_HALF_WIDTH, -POLE, POLE, { id: "red-land-0" }),
    quad(180 - RED_HALF_WIDTH, 180, -POLE, POLE, { id: "red-land-180e" }),
    quad(-180, -180 + RED_HALF_WIDTH, -POLE, POLE, { id: "red-land-180w" }),
  ],
};

/** A faint lat/lng grid. Pure instrument furniture — it sells "chart", not "app". */
export const GRATICULE: FeatureCollection<LineString> = {
  type: "FeatureCollection",
  features: [
    ...[-150, -120, -90, -60, -30, 30, 60, 90, 120, 150].map((lng) =>
      line(lerpCol(lng, -POLE, POLE, 64), { id: `mer-${lng}` }),
    ),
    ...[-60, -30, 30, 60].map((lat) => line(lerpRow(-180, 180, lat, 128), { id: `par-${lat}` })),
  ],
};

/**
 * Cartographic labels. Rendered as HTML markers, not symbol layers — a symbol
 * layer needs a `glyphs` PBF endpoint, and that would be the one external asset
 * this map is not allowed to have.
 */
export type WorldLabel = {
  id: string;
  text: string;
  lngLat: [number, number];
  kind: "sea" | "belt" | "line";
};

export const WORLD_LABELS: WorldLabel[] = [
  { id: "north-blue", text: "North Blue", lngLat: [-90, 48], kind: "sea" },
  { id: "west-blue", text: "West Blue", lngLat: [90, 48], kind: "sea" },
  { id: "east-blue", text: "East Blue", lngLat: [-90, -48], kind: "sea" },
  { id: "south-blue", text: "South Blue", lngLat: [90, -48], kind: "sea" },
  { id: "paradise", text: "Paradise", lngLat: [-112, 2.6], kind: "line" },
  { id: "new-world", text: "New World", lngLat: [112, 2.6], kind: "line" },
  { id: "red-line", text: "Red Line", lngLat: [0, 34], kind: "line" },
  { id: "calm-belt-n", text: "Calm Belt", lngLat: [-150, 13.2], kind: "belt" },
  { id: "calm-belt-s", text: "Calm Belt", lngLat: [-150, -13.2], kind: "belt" },
];

/**
 * The two points where the Red Line and the Grand Line cross. These are the only
 * two places a ship can pass between hemispheres, and they anchor the whole
 * longitude-as-progress reading of the map.
 */
export const CROSSINGS: { id: string; text: string; lngLat: [number, number] }[] = [
  { id: "reverse-mountain", text: "Reverse Mountain", lngLat: [-180, 0] },
  { id: "red-line-crossing", text: "The Red Line", lngLat: [0, 0] },
];
