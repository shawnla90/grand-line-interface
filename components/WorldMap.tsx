"use client";

/**
 * components/WorldMap.tsx — the instrument's canvas.
 *
 * MapLibre GL v5. No tile source, no sprite, no glyphs, no external URL of any
 * kind. The entire style is a plain object built at runtime and the entire world
 * is GeoJSON generated from code (see world-geometry.ts). It renders offline, it
 * costs nothing to serve, and there is no art dependency to license.
 *
 * NO SYMBOL LAYERS, DELIBERATELY. A `symbol` layer with a text-field requires a
 * `glyphs` PBF endpoint — that would be the one external asset this map is not
 * allowed to have. Every label is an HTML Marker instead, which also means the
 * labels are real typography (letter-spaced, themed) rather than raster glyphs.
 * MapLibre v5 Markers support `opacityWhenCovered`, so they correctly fade when
 * they rotate behind the globe.
 *
 * THE FOG IS A SWEEP, NOT A SWITCH. The parent tweens `chapter` as a float, and
 * every frame we re-evaluate the paint expressions against it. Islands therefore
 * pop in one at a time, in voyage order, as the number counts up — and each one
 * flares briefly as it is charted. That is the shot.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  type Map as MLMap,
  type StyleSpecification,
  type MapMouseEvent,
  type ExpressionSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { World, WorldIsland } from "@/lib/canon";
import { BLUES, CALM_BELTS, GRAND_LINE, RED_LINE, GRATICULE, WORLD_LABELS } from "./world-geometry";

export type Projection = "globe" | "mercator";

type Props = {
  world: World;
  /** The tweened chapter. A float on purpose — it drives the reveal sweep. */
  chapter: number;
  projection: Projection;
  showOffCanon: boolean;
  selected: string | null;
  onSelect: (slug: string | null) => void;
};

/* -------------------------------------------------------------------------- */
/* palette — mirrors app/globals.css                                           */
/* -------------------------------------------------------------------------- */

const C = {
  ocean: "#071324",
  oceanLit: "#0d2036",
  grat: "#16233c",
  belt: "#1b2c4d",
  gold: "#e3b04b",
  goldLit: "#f0c877",
  redLine: "#9c4436",
  parchment: "#efe6d4",
  fog: "#5b6880",
} as const;

/** How long an island keeps glowing after you first read about it, in chapters. */
const CHART_FLARE = 40;
/** Fogged islands are visible as a trace, never as an identity. */
const FOG_OPACITY = 0.13;

/** The rails float over the map, so the visible water is not the whole canvas. */
const MAP_PADDING = { left: 300, right: 270, top: 40, bottom: 20 };

/* -------------------------------------------------------------------------- */
/* geometry -> features                                                        */
/* -------------------------------------------------------------------------- */

function islandFeatures(islands: WorldIsland[]) {
  return {
    type: "FeatureCollection" as const,
    features: islands.map((i) => ({
      type: "Feature" as const,
      properties: {
        slug: i.slug,
        // `debut` is only meaningful for manga islands. Off-canon islands are not
        // "future" — they are not on the manga timeline at all, so they get their
        // own layer and never take part in the fog.
        debut: i.debutChapter ?? 0,
        kind: i.status === "manga" && i.debutChapter !== null ? "manga" : "off",
        confidence: i.confidence,
      },
      geometry: { type: "Point" as const, coordinates: [i.lng, i.lat] },
    })),
  };
}

/* -------------------------------------------------------------------------- */
/* paint expressions                                                           */
/* -------------------------------------------------------------------------- */

/** Revealed: the reader has met this island. */
const revealed = (ch: number): ExpressionSpecification => ["<=", ["get", "debut"], ch];

/**
 * RULE 4, RENDERED. The map must not let a position a machine guessed look like
 * a position a human confirmed.
 *
 *   canon   -> solid filled pin      (a human has confirmed this)
 *   derived -> hollow ring           (machine-derived from voyage order + region)
 *   guess   -> faint ghost dot       (no debut chapter, no region: a placement)
 *
 * Today every one of the 256 mappable islands is `derived` and none is `canon`,
 * so this map is currently ALL hollow rings. That is not a bug and it is not
 * hidden — the legend counts it out loud.
 */
const byConfidence = <T extends string | number>(canon: T, derived: T, guess: T): ExpressionSpecification =>
  [
    "match",
    ["get", "confidence"],
    "canon",
    canon,
    "derived",
    derived,
    "guess",
    guess,
    derived, // fallback: unknown confidence is treated as the machine's best guess
  ] as ExpressionSpecification;

/* -------------------------------------------------------------------------- */
/* component                                                                   */
/* -------------------------------------------------------------------------- */

export default function WorldMap({ world, chapter, projection, showOffCanon, selected, onSelect }: Props) {
  const holder = useRef<HTMLDivElement | null>(null);
  const map = useRef<MLMap | null>(null);
  const ready = useRef(false);

  // The map's event handlers are registered once, on mount, so they close over the
  // first `chapter` forever. This ref is how they read the current one. It is
  // written in an effect, never during render — a ref write during render is what
  // the react-hooks/refs rule exists to stop, and it would be a real hazard here.
  const chapterRef = useRef(chapter);
  useEffect(() => {
    chapterRef.current = chapter;
  }, [chapter]);

  const [hover, setHover] = useState<{ x: number; y: number; island: WorldIsland | null } | null>(null);

  // MapLibre needs a WebGL context and there are real browsers that will not give
  // it one: hardware acceleration off, a GPU blocklist, a privacy extension, a
  // headless CI runner. Without a guard the constructor throws, the throw escapes
  // the effect, and the whole route unmounts behind an error overlay — the chapter
  // axis, the roster and the scrubber all die with the canvas. They shouldn't: the
  // panels are plain data and render fine on their own. So the map degrades alone.
  const [glFailed, setGlFailed] = useState(false);

  const bySlug = useMemo(() => new Map(world.islands.map((i) => [i.slug, i])), [world.islands]);
  const features = useMemo(() => islandFeatures(world.islands), [world.islands]);

  /* ---------------------------------------------------------------- create */
  useEffect(() => {
    if (!holder.current || map.current) return;

    const style: StyleSpecification = {
      version: 8,
      name: "dead-reckoning",
      projection: { type: projection },
      // A globe needs an atmosphere or it reads as a flat disc.
      sky: {
        "sky-color": "#0a1730",
        "horizon-color": "#28507e",
        "fog-color": "#050a12",
        "fog-ground-blend": 0.6,
        "horizon-fog-blend": 0.7,
        "sky-horizon-blend": 0.9,
        "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 0.9, 5, 0.4, 7, 0],
      },
      sources: {
        blues: { type: "geojson", data: BLUES },
        belts: { type: "geojson", data: CALM_BELTS },
        grat: { type: "geojson", data: GRATICULE },
        grand: { type: "geojson", data: GRAND_LINE },
        red: { type: "geojson", data: RED_LINE },
        islands: { type: "geojson", data: features },
      },
      layers: [
        { id: "ocean", type: "background", paint: { "background-color": C.ocean } },

        // The four Blues, as quadrants of the two great circles.
        {
          id: "blues",
          type: "fill",
          source: "blues",
          paint: {
            "fill-color": [
              "match",
              ["get", "id"],
              "north-blue", "#0c1d33",
              "west-blue", "#0b1b30",
              "east-blue", "#0d2038",
              "south-blue", "#0a1a2e",
              "#0b1c32",
            ],
            "fill-opacity": 0.85,
          },
        },

        // The Calm Belts — windless water either side of the Grand Line.
        {
          id: "belts",
          type: "fill",
          source: "belts",
          paint: { "fill-color": C.belt, "fill-opacity": 0.28 },
        },

        { id: "graticule", type: "line", source: "grat", paint: { "line-color": C.grat, "line-width": 0.6, "line-opacity": 0.55 } },

        // The Grand Line: the sea route. Gold, because it is the voyage.
        { id: "grand-glow", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 9, "line-blur": 9, "line-opacity": 0.22 } },
        { id: "grand", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 1.1, "line-opacity": 0.75 } },

        // The Red Line: the continent. Clay, because it is land.
        { id: "red-glow", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 10, "line-blur": 10, "line-opacity": 0.25 } },
        { id: "red", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 2.4, "line-opacity": 0.9 } },

        // Off-canon locations: film / anime-only / game. They have no chapter, so
        // they can never be fogged. Hidden by default; the toggle says exactly why.
        //
        // TWO ORTHOGONAL ENCODINGS, and this layer is why they have to be separate:
        //   COLOUR    = canonicity        (gold = in the manga, grey = not)
        //   GEOMETRY  = position confidence (solid / hollow ring / ghost dot)
        // So an off-canon island whose position was still only guessed reads as a
        // grey ghost, and the legend's counts describe exactly what is on screen.
        {
          id: "islands-off",
          type: "circle",
          source: "islands",
          filter: ["==", ["get", "kind"], "off"],
          layout: { visibility: showOffCanon ? "visible" : "none" },
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 2.2, 3, 3.6, 6, 6],
            "circle-color": C.fog,
            "circle-opacity": byConfidence(0.6, 0.12, 0.34),
            "circle-stroke-color": "#7d8aa3",
            "circle-stroke-width": byConfidence(1, 1.2, 0),
            "circle-stroke-opacity": byConfidence(0.75, 0.8, 0),
          },
        },

        // The flare: an island you have just charted.
        {
          id: "islands-flare",
          type: "circle",
          source: "islands",
          filter: ["==", ["get", "kind"], "manga"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 9, 3, 15, 6, 26],
            "circle-color": C.goldLit,
            "circle-blur": 1,
            "circle-opacity": 0,
          },
        },

        // The fog: something is out there. Not what, not who.
        {
          id: "islands-fog",
          type: "circle",
          source: "islands",
          filter: ["==", ["get", "kind"], "manga"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 1.4, 3, 2.2, 6, 3.4],
            "circle-color": C.fog,
            "circle-opacity": 0,
            "circle-stroke-width": 0,
          },
        },

        // The world you have actually read.
        {
          id: "islands",
          type: "circle",
          source: "islands",
          filter: ["==", ["get", "kind"], "manga"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 2.9, 3, 4.6, 6, 7.5],
            "circle-color": byConfidence(C.gold, C.gold, C.fog),
            "circle-opacity": 0,
            "circle-stroke-color": byConfidence(C.parchment, C.goldLit, C.fog),
            "circle-stroke-width": byConfidence(1, 1.5, 0),
            "circle-stroke-opacity": 0,
          },
        },

        {
          id: "islands-selected",
          type: "circle",
          source: "islands",
          filter: ["==", ["get", "slug"], " none"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 8, 3, 12, 6, 18],
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": C.parchment,
            "circle-stroke-width": 1.4,
            "circle-stroke-opacity": 0.9,
          },
        },

        // Invisible, generous hit target. Includes fogged islands on purpose: the
        // reader can hover the unknown and be told, honestly, that it is unknown.
        {
          id: "islands-hit",
          type: "circle",
          source: "islands",
          paint: { "circle-radius": 11, "circle-color": "rgba(0,0,0,0)" },
        },
      ],
    };

    let m: MLMap;
    try {
      // v5 removed maplibregl.supported(); the constructor itself throws
      // "Failed to initialize WebGL" when it cannot get a context, so catching it
      // here is both the check and the handler.
      m = new maplibregl.Map({
        container: holder.current,
        style,
        center: [-20, 6],
        zoom: 1.9,
        minZoom: 0.4,
        maxZoom: 7,
        // NB: `padding` is a CAMERA option, not a MapOptions one — it is applied via
        // setPadding() on load, below.
        attributionControl: false,
        // One world, not an infinite tiling strip. This is a chart of a planet.
        renderWorldCopies: false,
        dragRotate: projection === "globe",
      });
    } catch (err) {
      console.warn("[dead-reckoning] map disabled, no WebGL context:", err);
      setGlFailed(true);
      return;
    }
    map.current = m;

    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    for (const l of WORLD_LABELS) {
      const el = document.createElement("div");
      el.className = "mapLabel";
      el.textContent = l.text;
      const size = l.kind === "sea" ? "11px" : "9px";
      el.style.fontSize = size;
      el.style.color = l.kind === "line" ? "rgba(239,230,212,.66)" : "rgba(140,154,181,.62)";
      if (l.kind === "belt") el.style.color = "rgba(91,104,128,.7)";
      new maplibregl.Marker({ element: el, opacityWhenCovered: "0" }).setLngLat(l.lngLat).addTo(m);
    }

    const onMove = (e: MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["islands-hit"] })[0];
      if (!f) {
        setHover(null);
        m.getCanvas().style.cursor = "";
        return;
      }
      const slug = f.properties?.slug as string;
      const island = bySlug.get(slug) ?? null;
      const isFogged =
        island != null &&
        island.status === "manga" &&
        island.debutChapter !== null &&
        island.debutChapter > chapterRef.current;

      m.getCanvas().style.cursor = isFogged ? "not-allowed" : "pointer";
      // A fogged island passes `null` — its NAME NEVER ENTERS THE DOM.
      setHover({ x: e.point.x, y: e.point.y, island: isFogged ? null : island });
    };

    const onLeave = () => {
      setHover(null);
      m.getCanvas().style.cursor = "";
    };

    const onClick = (e: MapMouseEvent) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["islands-hit"] })[0];
      if (!f) return onSelect(null);
      const slug = f.properties?.slug as string;
      const island = bySlug.get(slug);
      if (!island) return onSelect(null);
      const isFogged =
        island.status === "manga" && island.debutChapter !== null && island.debutChapter > chapterRef.current;
      onSelect(isFogged ? null : slug);
    };

    m.on("mousemove", onMove);
    m.on("mouseout", onLeave);
    m.on("click", onClick);

    // A MapLibre style error does not throw — it is dispatched as an event. With
    // no listener a bad style fails silently and you get a black rectangle.
    m.on("error", (e) => console.error("[maplibre]", e.error?.message ?? e));

    m.on("load", () => {
      ready.current = true;
      // The rails float over the map, so the centre of the canvas is not the centre
      // of the visible water. Pad first, then frame — otherwise the globe sits
      // behind the left panel.
      m.setPadding(MAP_PADDING);
      m.jumpTo({ center: [-20, 6], zoom: 1.9 });
      paint(m, chapterRef.current);
    });

    if (process.env.NODE_ENV !== "production") {
      (window as unknown as { __map?: MLMap }).__map = m;
    }

    return () => {
      ready.current = false;
      m.remove();
      map.current = null;
    };
    // Created once. Everything after is imperative — a React re-render must never
    // tear down a WebGL context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ----------------------------------------------------------------- paint */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    paint(m, chapter);
  }, [chapter]);

  /* ------------------------------------------------------------ projection */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    m.setProjection({ type: projection });

    // A zoom that frames a sphere leaves a flat map cropped, and vice versa. The
    // toggle has to reframe or half the world falls off the edge.
    if (projection === "globe") {
      m.dragRotate.enable();
      m.easeTo({ center: [-20, 6], zoom: 1.9, duration: 700 });
    } else {
      m.dragRotate.disable();
      m.fitBounds(
        [
          [-179, -74],
          [179, 74],
        ],
        { padding: MAP_PADDING, duration: 700 },
      );
    }
  }, [projection]);

  /* -------------------------------------------------------------- off-canon */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    m.setLayoutProperty("islands-off", "visibility", showOffCanon ? "visible" : "none");
  }, [showOffCanon]);

  /* --------------------------------------------------------------- selected */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    m.setFilter("islands-selected", ["==", ["get", "slug"], selected ?? " none"]);
    if (selected) {
      const i = bySlug.get(selected);
      if (i) m.easeTo({ center: [i.lng, i.lat], duration: 900 });
    }
  }, [selected, bySlug]);

  const hoveredIsland = hover?.island ?? null;
  const hoveringFog = hover !== null && hover.island === null;

  return (
    <div className="absolute inset-0">
      {/* h-full, NOT absolute inset-0. MapLibre stamps `.maplibregl-map` onto this
          element and maplibre-gl.css declares `.maplibregl-map { position: relative }`.
          That has the same specificity as Tailwind's `.absolute`, so the winner is
          decided by stylesheet order — and MapLibre's wins, which silently drops the
          element out of absolute positioning, collapses it to height:0, and renders a
          perfectly correct map into a box with no height. Sizing with h-full/w-full
          does not care about `position`, so the cascade race cannot bite. */}
      <div ref={holder} className="h-full w-full" />

      {glFailed && (
        <div className="absolute inset-0 z-30 grid place-items-center bg-ink/80 px-6 text-center backdrop-blur">
          <div className="max-w-sm">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-2">
              Chart unavailable
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-muted">
              This browser will not give the atlas a WebGL context, so the globe cannot draw.
              Everything else on this page is still true — the chapter, the arc, the roster and
              the count of what you have charted are plain numbers and do not need a GPU.
            </p>
          </div>
        </div>
      )}

      {hover && (
        <div
          className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+14px)]"
          style={{ left: hover.x, top: hover.y }}
        >
          {hoveringFog ? (
            <div className="rounded-md border border-rope bg-ink/95 px-2.5 py-1.5 shadow-2xl backdrop-blur">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-2">
                Uncharted
              </div>
              <div className="mt-0.5 text-[11px] text-muted">Beyond your chapter</div>
            </div>
          ) : (
            hoveredIsland && (
              <div className="min-w-[150px] rounded-md border border-rope bg-ink/95 px-2.5 py-1.5 shadow-2xl backdrop-blur">
                <div className="text-[12px] font-medium text-parchment">{hoveredIsland.name}</div>
                {hoveredIsland.debutChapter !== null && (
                  <div className="mt-0.5 font-mono text-[10px] tabular-nums text-gold">
                    ch. {hoveredIsland.debutChapter}
                  </div>
                )}
                <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                  {hoveredIsland.confidence === "canon"
                    ? "confirmed"
                    : hoveredIsland.confidence === "derived"
                      ? "position derived"
                      : "position guessed"}
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* the sweep                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Re-evaluate the fog against a (fractional) chapter. Called every frame while
 * the chapter tweens, which is what makes the world unfurl in voyage order
 * instead of blinking into existence.
 *
 * ~413 features across 4 layers is nothing for MapLibre to re-evaluate; the cost
 * is bounded by the frame rate, and the tween settles in about a second.
 */
function paint(m: MLMap, ch: number) {
  // Revealed islands, styled by how much we actually trust their position.
  m.setPaintProperty("islands", "circle-opacity", [
    "case",
    revealed(ch),
    // A hollow ring is a ring: the fill barely reads, the stroke carries it.
    byConfidence(0.95, 0.14, 0.34),
    0,
  ]);
  m.setPaintProperty("islands", "circle-stroke-opacity", ["case", revealed(ch), byConfidence(0.9, 1, 0), 0]);

  // Everything after where you are.
  m.setPaintProperty("islands-fog", "circle-opacity", [
    "case",
    [">", ["get", "debut"], ch],
    FOG_OPACITY,
    0,
  ]);

  // The flare on a freshly charted island, decaying over the next ~40 chapters.
  m.setPaintProperty("islands-flare", "circle-opacity", [
    "case",
    [">", ["get", "debut"], ch],
    0,
    ["interpolate", ["linear"], ["-", ch, ["get", "debut"]], 0, 0.45, CHART_FLARE, 0],
  ]);
}
