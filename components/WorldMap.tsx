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
  type Marker as MLMarker,
  type GeoJSONSource,
  type StyleSpecification,
  type MapMouseEvent,
  type ExpressionSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { World, WorldIsland } from "@/lib/canon";
import type { Art } from "@/lib/art";
import { voyageGeometryAt, vesselAtChapter, presenceWindowAt } from "@/lib/canon";
import { crewColor, WARLORD_COLOR } from "@/lib/crews";
import { lensColor, revealedFruit, revealedHaki, HAKI_STYLE } from "@/lib/lenses";
import type { Lens, PresenceLens } from "@/lib/lenses";
import type { HakiType } from "@/lib/canon";
import { jollyRogerSvg } from "./marks/jolly-roger";
import CompassRose from "./marks/CompassRose";
import {
  BLUES,
  CALM_BELTS,
  CALM_BELT_HATCH,
  GRAND_LINE,
  GRAND_LINE_LANE,
  RED_LINE,
  RED_LINE_LAND,
  POLAR_DEEP,
  GRATICULE,
  WORLD_LABELS,
} from "./world-geometry";

export type Projection = "globe" | "mercator";

type Props = {
  world: World;
  /** Phase 6 official art (slug -> /art/… url). Optional — absent => the SVG marks are used. */
  art?: Art;
  /** The tweened chapter. A float on purpose — it drives the reveal sweep. */
  chapter: number;
  projection: Projection;
  showOffCanon: boolean;
  /**
   * The presence lens (Phase 6A). "off" hides the Crews & Warlords layer;
   * "crew" | "fruit" | "haki" pick what the orb colors MEAN. Chapter-gated
   * like everything else — a power below its reveal chapter does not exist.
   */
  lens: PresenceLens;
  selected: string | null;
  onSelect: (slug: string | null) => void;
  /**
   * Admin placement mode (the /admin/place tool). When both are set, a map click
   * reports its lng/lat instead of selecting an island — that's how a human
   * upgrades a derived pin to a confirmed one.
   */
  placingSlug?: string | null;
  onPlaceAt?: (lngLat: [number, number]) => void;
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
  // Route A — cartographic tones.
  laneParadise: "#123049", // the navigable Grand Line channel, warm side
  laneNewWorld: "#0b2035", // the New World half — colder, rougher
  beltDeep: "#060f1e", // dead, windless Calm Belt water
  beltHatch: "#243a5a", // the cross-hatch strokes inside the belts
  land: "#3a2620", // Red Line continent — clay/earth, not ocean
  landLit: "#513528",
  deep: "#04090f", // open-ocean depth toward the poles
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

/**
 * The traveled route as a LineString FeatureCollection. Fewer than two points is
 * not a line — the crew has not left port yet — so it renders as nothing.
 */
function voyageLine(path: [number, number][]) {
  return {
    type: "FeatureCollection" as const,
    features:
      path.length >= 2
        ? [
            {
              type: "Feature" as const,
              properties: {},
              geometry: { type: "LineString" as const, coordinates: path },
            },
          ]
        : [],
  };
}

/**
 * The ship marks. Original SVG — a hull and sails, no licensed art. The vessel is
 * distinguished by its rig so the swap from boat -> Merry -> Sunny reads on screen:
 * a small boat has one lateen sail, the Going Merry one square sail, the Thousand
 * Sunny two sails under a small sun. Unknown slugs fall back to the small boat.
 */
function vesselGlyph(slug: string | null | undefined): string {
  const P = C.parchment;
  const G = C.goldLit;
  const hull = `<path d="M3 15 H21 L18.2 20 H5.8 Z" fill="${P}" stroke="${G}" stroke-width="0.6"/>`;
  const mast = `<line x1="12" y1="2.5" x2="12" y2="15" stroke="${P}" stroke-width="1"/>`;
  if (slug === "thousand-sunny") {
    return `<svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="3" r="2" fill="${G}"/>
      ${mast}
      <path d="M12 6 L7 13 H12 Z" fill="${P}"/>
      <path d="M12 6 L17 13 H12 Z" fill="${G}" opacity="0.85"/>
      ${hull}</svg>`;
  }
  if (slug === "going-merry") {
    return `<svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
      ${mast}
      <path d="M6 5 H18 V13 H6 Z" fill="${P}"/>
      ${hull}</svg>`;
  }
  if (slug === "barrel") {
    // Chapter 1: Luffy adrift in a barrel. A stave cask, no sail.
    return `<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="7" y="5" width="10" height="14" rx="4" fill="${P}" stroke="${G}" stroke-width="0.7"/>
      <line x1="7.4" y1="9" x2="16.6" y2="9" stroke="${G}" stroke-width="0.8"/>
      <line x1="7.4" y1="15" x2="16.6" y2="15" stroke="${G}" stroke-width="0.8"/></svg>`;
  }
  // small boat (default)
  return `<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
    ${mast}
    <path d="M12 4 L12 14 L6 14 Z" fill="${P}"/>
    ${hull}</svg>`;
}

/**
 * An <img> string for a map mark (Phase 6 real art). Injected as innerHTML so the
 * spoiler-clearing in hidePresence (innerHTML="" / textContent="") wipes it too —
 * a backward scrub must leave no /art/<slug>.webp URL naming a future entity in
 * the DOM. `round` gives a circular portrait; `ring` outlines it in the crew ink.
 */
function artImg(url: string, w: number, opts?: { round?: boolean; ring?: string }): string {
  const shape = opts?.round
    ? `width:${w}px;height:${w}px;object-fit:cover;border-radius:9999px;`
    : `width:${w}px;height:auto;border-radius:2px;`;
  const ring = opts?.ring ? `outline:1.4px solid ${opts.ring};outline-offset:-1px;` : "";
  return `<img src="${url}" alt="" draggable="false" style="display:block;margin:0 auto;${shape}${ring}">`;
}

/** Build (once) the DOM element MapLibre re-positions each frame for the ship. */
function makeShipElement(): {
  el: HTMLDivElement;
  flag: HTMLDivElement;
  glyph: HTMLDivElement;
  label: HTMLDivElement;
} {
  const el = document.createElement("div");
  el.className = "shipMarker";
  el.style.display = "none";
  el.style.transform = "translateY(-2px)";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";

  // The crew's Jolly Roger, flying above the ship. Set once (the crew never
  // changes); the vessel below it swaps as the reader sails.
  const flag = document.createElement("div");
  flag.style.lineHeight = "0";
  flag.style.marginBottom = "-3px";
  flag.style.filter = "drop-shadow(0 0 4px rgba(0,0,0,0.6))";

  const glyph = document.createElement("div");
  glyph.style.filter = "drop-shadow(0 0 5px rgba(227,176,75,0.55))";
  glyph.style.lineHeight = "0";

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "8px";
  label.style.letterSpacing = "0.16em";
  label.style.textTransform = "uppercase";
  label.style.color = "rgba(239,230,212,0.82)";
  label.style.whiteSpace = "nowrap";
  label.style.fontFamily = "var(--font-geist-mono), monospace";

  el.appendChild(flag);
  el.appendChild(glyph);
  el.appendChild(label);
  return { el, flag, glyph, label };
}

/** The live handles paint() needs to move and restyle the ship each frame. */
type ShipHandle = { marker: MLMarker; glyph: HTMLDivElement; label: HTMLDivElement };

/**
 * A tiny generic hull in the crew's ink — the "someone's ship rides here" cue
 * under a presence flag. Deliberately simpler than the Straw Hats' vesselGlyph:
 * theirs is THE ship, these are marks on a chart.
 */
function crewHullGlyph(color: string): string {
  return `<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
    <line x1="12" y1="5" x2="12" y2="14" stroke="${color}" stroke-width="1.2"/>
    <path d="M12 6 L7.5 13 H12 Z" fill="${color}" opacity="0.85"/>
    <path d="M4.5 14 H19.5 L17 18.5 H7 Z" fill="${color}"/></svg>`;
}

/**
 * Build (once, per presence crew) the flag marker element. EVERYTHING user-visible
 * starts EMPTY — no name, no flag SVG — and is populated by paint() only while the
 * crew's window is active. Hiding clears it again, so a backward scrub re-fogs the
 * DOM: at chapter 1 an Elements-panel search finds no future crew's name anywhere.
 */
function makeCrewFlagElement(): {
  el: HTMLDivElement;
  flag: HTMLDivElement;
  hull: HTMLDivElement;
  label: HTMLDivElement;
} {
  const el = document.createElement("div");
  el.className = "crewFlagMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";

  const flag = document.createElement("div");
  flag.style.lineHeight = "0";
  flag.style.marginBottom = "-2px";
  flag.style.filter = "drop-shadow(0 0 4px rgba(0,0,0,0.65))";

  const hull = document.createElement("div");
  hull.style.lineHeight = "0";

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "8px";
  label.style.letterSpacing = "0.14em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.fontFamily = "var(--font-geist-mono), monospace";

  el.appendChild(flag);
  el.appendChild(hull);
  el.appendChild(label);
  return { el, flag, hull, label };
}

/** Build (once, per Warlord) the monogram ring. Letter and name start EMPTY. */
function makeWarlordElement(): {
  el: HTMLDivElement;
  ring: HTMLDivElement;
  label: HTMLDivElement;
} {
  const el = document.createElement("div");
  el.className = "warlordMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";

  const ring = document.createElement("div");
  ring.style.width = "18px";
  ring.style.height = "18px";
  ring.style.margin = "0 auto";
  ring.style.borderRadius = "9999px";
  ring.style.border = `1.4px solid ${WARLORD_COLOR}`;
  ring.style.background = "rgba(7,19,36,0.72)";
  ring.style.color = WARLORD_COLOR;
  ring.style.fontSize = "9px";
  ring.style.lineHeight = "15px";
  ring.style.overflow = "hidden";
  ring.style.fontFamily = "var(--font-geist-mono), monospace";
  ring.style.filter = "drop-shadow(0 0 3px rgba(0,0,0,0.6))";

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "7.5px";
  label.style.letterSpacing = "0.12em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.color = "rgba(140,154,181,0.85)";
  label.style.fontFamily = "var(--font-geist-mono), monospace";

  el.appendChild(ring);
  el.appendChild(label);
  return { el, ring, label };
}

/**
 * Build (once, per crew member) a small portrait ring. Like the Warlord ring but
 * smaller and label-less — the flag above carries the crew name, and hovering the
 * orb underneath names the member. The empty `label` div only keeps hidePresence
 * uniform across every pooled marker. Portrait + border are set on populate.
 */
function makeMemberElement(): { el: HTMLDivElement; ring: HTMLDivElement; label: HTMLDivElement } {
  const el = document.createElement("div");
  el.className = "memberMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";

  const ring = document.createElement("div");
  ring.style.width = "15px";
  ring.style.height = "15px";
  ring.style.margin = "0 auto";
  ring.style.borderRadius = "9999px";
  ring.style.overflow = "hidden";
  ring.style.background = "rgba(7,19,36,0.72)";
  ring.style.filter = "drop-shadow(0 0 2px rgba(0,0,0,0.6))";

  const label = document.createElement("div"); // unused; keeps hidePresence uniform

  el.appendChild(ring);
  el.appendChild(label);
  return { el, ring, label };
}

/**
 * A pooled presence marker. `paintKey` is the diff key: paint() only touches
 * the DOM when the active window — or, for Warlord monograms, the lens color —
 * actually changes, so the per-frame cost of the sweep stays allocation-free.
 */
type PresenceHandle = {
  marker: MLMarker;
  parts: { el: HTMLDivElement; label: HTMLDivElement } & Record<string, HTMLDivElement>;
  shown: boolean;
  paintKey: string | null;
  populated: boolean;
};

/**
 * Where each active presence entity actually SITS this frame. Anchors come from
 * the active window; entities sharing an anchor (the Summit War puts six of
 * them on Marineford) fan out in a deterministic ring — sorted by slug, so the
 * layout is stable across frames, reloads, and the server/client boundary.
 */
type PlacedPresence = { w: NonNullable<ReturnType<typeof presenceWindowAt>>; lng: number; lat: number };

function presenceLayout(world: World, ch: number): Map<string, PlacedPresence> {
  const active: { slug: string; w: PlacedPresence["w"] }[] = [];
  for (const c of world.presence.crews) {
    const w = presenceWindowAt(c.windows, ch);
    if (w) active.push({ slug: c.slug, w });
  }
  for (const c of world.presence.characters) {
    const w = presenceWindowAt(c.windows, ch);
    if (w) active.push({ slug: c.slug, w });
  }
  const groups = new Map<string, typeof active>();
  for (const a of active) {
    const key = `${a.w.lng.toFixed(2)},${a.w.lat.toFixed(2)}`;
    const g = groups.get(key);
    if (g) g.push(a);
    else groups.set(key, [a]);
  }
  const out = new Map<string, PlacedPresence>();
  for (const g of groups.values()) {
    if (g.length === 1) {
      out.set(g[0].slug, { w: g[0].w, lng: g[0].w.lng, lat: g[0].w.lat });
      continue;
    }
    g.sort((a, b) => a.slug.localeCompare(b.slug));
    g.forEach((a, i) => {
      const ang = (i / g.length) * Math.PI * 2 - Math.PI / 2;
      out.set(a.slug, {
        w: a.w,
        lng: a.w.lng + Math.cos(ang) * 2.6,
        lat: a.w.lat + Math.sin(ang) * 2.0,
      });
    });
  }
  return out;
}

/**
 * The presence-orb source data for one frame: only REVEALED entities exist here,
 * and a power fact below its reveal chapter is not a property with a null value —
 * the property does not exist. The source is rebuilt every frame, so a backward
 * scrub deletes revealed facts the same way it deletes entities.
 */
function presenceOrbs(world: World, ch: number, layout: Map<string, PlacedPresence>, lens: Lens) {
  const features: GeoJSON.Feature[] = [];
  for (const crew of world.presence.crews) {
    const placed = layout.get(crew.slug);
    if (!placed) continue;
    const revealedMembers = crew.members.filter((m) => m.fromChapter <= ch);
    const n = revealedMembers.length;
    revealedMembers.forEach((m, i) => {
      // A deterministic little ring around the flag, so member orbs never stack.
      const a = (i / Math.max(1, n)) * Math.PI * 2 - Math.PI / 2;
      const fruit = revealedFruit(m, ch);
      const haki = revealedHaki(m, ch);
      features.push({
        type: "Feature",
        properties: {
          slug: m.slug,
          name: m.name,
          crewSlug: crew.slug,
          crewName: crew.name,
          vesselName: crew.vessel?.name ?? null,
          kind: "member",
          color: lensColor(lens, { crewSlug: crew.slug, fruit: m.fruit, haki: m.haki, kind: "member" }, ch),
          confidence: m.confidence,
          verified: m.verified,
          ...(fruit ? { fruitName: fruit.name, fruitType: fruit.type } : {}),
          ...(haki.length ? { hakiTypes: haki.map((h) => h.type).join("|") } : {}),
        },
        geometry: {
          type: "Point",
          coordinates: [placed.lng + Math.cos(a) * 2.1, placed.lat + Math.sin(a) * 1.5],
        },
      });
    });
    // The flag itself gets an invisible hit feature so hover works on it too.
    features.push({
      type: "Feature",
      properties: {
        slug: crew.slug,
        name: crew.name,
        crewSlug: crew.slug,
        crewName: placed.w.label,
        vesselName: crew.vessel?.name ?? null,
        kind: "crew",
        color: crewColor(crew.slug),
        confidence: placed.w.confidence,
        verified: placed.w.verified,
      },
      geometry: { type: "Point", coordinates: [placed.lng, placed.lat] },
    });
  }
  for (const c of world.presence.characters) {
    const placed = layout.get(c.slug);
    if (!placed) continue;
    const fruit = revealedFruit(c, ch);
    const haki = revealedHaki(c, ch);
    features.push({
      type: "Feature",
      properties: {
        slug: c.slug,
        name: c.name,
        crewSlug: c.crewSlug,
        crewName: c.affiliation,
        vesselName: null,
        kind: "warlord",
        color: lensColor(lens, { crewSlug: c.crewSlug, fruit: c.fruit, haki: c.haki, kind: "warlord" }, ch),
        confidence: placed.w.confidence,
        verified: placed.w.verified,
        ...(fruit ? { fruitName: fruit.name, fruitType: fruit.type } : {}),
        ...(haki.length ? { hakiTypes: haki.map((h) => h.type).join("|") } : {}),
      },
      geometry: { type: "Point", coordinates: [placed.lng, placed.lat] },
    });
  }
  return { type: "FeatureCollection" as const, features };
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

export default function WorldMap({
  world,
  art,
  chapter,
  projection,
  showOffCanon,
  lens,
  selected,
  onSelect,
  placingSlug = null,
  onPlaceAt,
}: Props) {
  const holder = useRef<HTMLDivElement | null>(null);
  const map = useRef<MLMap | null>(null);
  const ready = useRef(false);
  const ship = useRef<ShipHandle | null>(null);

  // The presence pools: one HTML marker per crew flag / Warlord monogram, built
  // once on load and diffed per frame by paint(). NEVER created per frame.
  const crewFlags = useRef<Map<string, PresenceHandle>>(new Map());
  const warlordMarks = useRef<Map<string, PresenceHandle>>(new Map());
  // One portrait ring per named crew member (Phase 6). Keyed by member slug
  // (unique across crews). Positions track the member-orb ring around the flag.
  const memberMarks = useRef<Map<string, PresenceHandle>>(new Map());
  // paint() runs on the chapter tween; it reads the live lens through this ref.
  const lensRef = useRef(lens);
  useEffect(() => {
    lensRef.current = lens;
  }, [lens]);

  // Placement mode is read by the click handler, which is registered once on
  // mount and so must read current values through a ref (same pattern as chapter).
  const placeRef = useRef<{ slug: string | null; onPlaceAt?: (p: [number, number]) => void }>({
    slug: placingSlug,
    onPlaceAt,
  });
  useEffect(() => {
    placeRef.current = { slug: placingSlug, onPlaceAt };
  }, [placingSlug, onPlaceAt]);

  // The map's event handlers are registered once, on mount, so they close over the
  // first `chapter` forever. This ref is how they read the current one. It is
  // written in an effect, never during render — a ref write during render is what
  // the react-hooks/refs rule exists to stop, and it would be a real hazard here.
  const chapterRef = useRef(chapter);
  useEffect(() => {
    chapterRef.current = chapter;
  }, [chapter]);

  const [hover, setHover] = useState<{
    x: number;
    y: number;
    island: WorldIsland | null;
    /** A presence mark (crew flag / member orb / Warlord). Only ever REVEALED entities. */
    presence?: {
      name: string;
      crewName: string | null;
      vesselName: string | null;
      kind: string;
      confidence: string;
      verified: boolean;
      /** Power facts — present ONLY when revealed at this chapter (the feature
          simply has no such property otherwise, so the tooltip cannot leak). */
      fruitName: string | null;
      fruitType: string | null;
      hakiTypes: string | null;
    } | null;
  } | null>(null);

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
        deep: { type: "geojson", data: POLAR_DEEP },
        lane: { type: "geojson", data: GRAND_LINE_LANE },
        belts: { type: "geojson", data: CALM_BELTS },
        belthatch: { type: "geojson", data: CALM_BELT_HATCH },
        redland: { type: "geojson", data: RED_LINE_LAND },
        grat: { type: "geojson", data: GRATICULE },
        grand: { type: "geojson", data: GRAND_LINE },
        red: { type: "geojson", data: RED_LINE },
        voyage: { type: "geojson", data: voyageLine([]) },
        islands: { type: "geojson", data: features },
        // Presence orbs: rebuilt per frame from the swept chapter. Only REVEALED
        // entities are ever in this source — spoiler safety is structural here,
        // not an opacity trick.
        presence: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
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

        // Open-ocean depth: the sea darkens toward the poles.
        { id: "deep", type: "fill", source: "deep", paint: { "fill-color": C.deep, "fill-opacity": 0.55 } },

        // The Grand Line sea-lane — the navigable channel down the equator, warmer
        // on the Paradise side, colder and rougher in the New World.
        {
          id: "lane",
          type: "fill",
          source: "lane",
          paint: {
            "fill-color": ["match", ["get", "half"], "paradise", C.laneParadise, "new-world", C.laneNewWorld, C.laneParadise],
            "fill-opacity": 0.9,
          },
        },

        // The Calm Belts — windless, Sea-King water. Dark dead water + cross-hatch
        // so they read as the danger they are, not a faint tint.
        { id: "belts", type: "fill", source: "belts", paint: { "fill-color": C.beltDeep, "fill-opacity": 0.72 } },
        { id: "belt-hatch", type: "line", source: "belthatch", paint: { "line-color": C.beltHatch, "line-width": 0.5, "line-opacity": 0.5 } },

        // The Red Line, as a continent. Drawn here (over the water, under the grid
        // and coastlines) so the red strokes below become its coast.
        { id: "red-land", type: "fill", source: "redland", paint: { "fill-color": C.land, "fill-opacity": 0.96 } },
        { id: "red-land-edge", type: "line", source: "redland", paint: { "line-color": C.landLit, "line-width": 0.8, "line-opacity": 0.7 } },

        { id: "graticule", type: "line", source: "grat", paint: { "line-color": C.grat, "line-width": 0.6, "line-opacity": 0.55 } },

        // The Grand Line: the sea route. Gold, because it is the voyage.
        { id: "grand-glow", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 9, "line-blur": 9, "line-opacity": 0.22 } },
        { id: "grand", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 1.1, "line-opacity": 0.75 } },

        // The Red Line: the continent. Clay, because it is land.
        { id: "red-glow", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 10, "line-blur": 10, "line-opacity": 0.25 } },
        { id: "red", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 2.4, "line-opacity": 0.9 } },

        // THE VOYAGE: the crew's actual traveled route, drawn up to the reader's
        // chapter. Brighter and heavier than the Grand Line (which is the sea's
        // geometry, not their path) so it reads as "where they have sailed." Its
        // data is replaced every frame by paint() as the chapter tweens, so the
        // wake extends leg by leg. `line-round` joins keep the zigzags from spiking.
        {
          id: "voyage-glow",
          type: "line",
          source: "voyage",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": C.goldLit, "line-width": 6, "line-blur": 7, "line-opacity": 0.3 },
        },
        {
          id: "voyage-line",
          type: "line",
          source: "voyage",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": C.parchment,
            "line-width": ["interpolate", ["linear"], ["zoom"], 0, 1.4, 3, 2, 6, 2.8],
            "line-opacity": 0.85,
            "line-dasharray": [2.5, 1.6],
          },
        },

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

        // WHO SAILS HERE (Phase 5). Member orbs in the crew's ink; Warlord anchor
        // dots under their monograms. The source only ever holds revealed
        // entities, so there is no fog case to paint.
        {
          id: "presence-orbs",
          type: "circle",
          source: "presence",
          filter: ["!=", ["get", "kind"], "crew"],
          layout: { visibility: lens !== "off" ? "visible" : "none" },
          paint: {
            "circle-radius": [
              "interpolate", ["linear"], ["zoom"],
              0, ["match", ["get", "kind"], "warlord", 2.6, 2],
              3, ["match", ["get", "kind"], "warlord", 4.2, 3.4],
              6, ["match", ["get", "kind"], "warlord", 6.4, 5.2],
            ],
            "circle-color": ["get", "color"],
            "circle-opacity": 0.9,
            "circle-stroke-color": C.parchment,
            "circle-stroke-width": ["match", ["get", "kind"], "warlord", 1.2, 0.6],
            "circle-stroke-opacity": byConfidence(0.85, 0.55, 0.3),
          },
        },
        {
          id: "presence-hit",
          type: "circle",
          source: "presence",
          layout: { visibility: lens !== "off" ? "visible" : "none" },
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

    // The ship. One marker, moved and restyled every frame by paint(). It starts at
    // the first waypoint and hidden; paint() reveals it once the reader reaches ch. 1.
    const parts = makeShipElement();
    parts.flag.innerHTML = jollyRogerSvg(world.voyage.crewSlug, { size: 22 });
    const start = world.voyage.waypoints[0];
    const shipMarker = new maplibregl.Marker({ element: parts.el, opacityWhenCovered: "0.2" })
      .setLngLat(start ? [start.lng, start.lat] : [0, 0])
      .addTo(m);
    ship.current = { marker: shipMarker, glyph: parts.glyph, label: parts.label };

    // The presence pools (Phase 5): one flag per crew, one monogram per Warlord,
    // built ONCE, hidden and EMPTY. paint() populates a marker only while its
    // window is active, and clears it again when it hides — the DOM at chapter 1
    // contains no future crew's name, even after a scrub to 1125 and back.
    const crewPool = crewFlags.current;
    const warlordPool = warlordMarks.current;
    const memberPool = memberMarks.current;
    for (const crew of world.presence.crews) {
      const p = makeCrewFlagElement();
      const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.2" })
        .setLngLat([0, 0])
        .addTo(m);
      crewPool.set(crew.slug, {
        marker,
        parts: { el: p.el, flag: p.flag, hull: p.hull, label: p.label },
        shown: false,
        paintKey: null,
        populated: false,
      });
    }
    for (const c of world.presence.characters) {
      const p = makeWarlordElement();
      const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.2" })
        .setLngLat([0, 0])
        .addTo(m);
      warlordPool.set(c.slug, {
        marker,
        parts: { el: p.el, ring: p.ring, label: p.label },
        shown: false,
        paintKey: null,
        populated: false,
      });
    }
    // One portrait ring per named crew member, built once, hidden and EMPTY. paint()
    // positions and populates them around each active flag; hidePresence clears them.
    for (const crew of world.presence.crews) {
      for (const mem of crew.members) {
        const p = makeMemberElement();
        const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.2" })
          .setLngLat([0, 0])
          .addTo(m);
        memberPool.set(mem.slug, {
          marker,
          parts: { el: p.el, ring: p.ring, label: p.label },
          shown: false,
          paintKey: null,
          populated: false,
        });
      }
    }

    const onMove = (e: MapMouseEvent) => {
      // Presence first: a crew flag or Warlord sits ON an island pin at most
      // home bases, and the more specific mark should win the tooltip. The
      // presence source only ever contains revealed entities, so everything on
      // a feature here is safe to render.
      const pf = m.queryRenderedFeatures(e.point, { layers: ["presence-hit"] })[0];
      if (pf) {
        m.getCanvas().style.cursor = "pointer";
        setHover({
          x: e.point.x,
          y: e.point.y,
          island: null,
          presence: {
            name: pf.properties?.name as string,
            crewName: (pf.properties?.crewName as string) ?? null,
            vesselName: (pf.properties?.vesselName as string) ?? null,
            kind: pf.properties?.kind as string,
            confidence: pf.properties?.confidence as string,
            verified: pf.properties?.verified === true || pf.properties?.verified === "true",
            fruitName: (pf.properties?.fruitName as string) ?? null,
            fruitType: (pf.properties?.fruitType as string) ?? null,
            hakiTypes: (pf.properties?.hakiTypes as string) ?? null,
          },
        });
        return;
      }
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
      // Placement mode: a click anywhere reports its lng/lat for the targeted island.
      if (placeRef.current.onPlaceAt && placeRef.current.slug) {
        placeRef.current.onPlaceAt([e.lngLat.lng, e.lngLat.lat]);
        return;
      }
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
      paint(m, chapterRef.current, world, ship.current, {
        crews: crewFlags.current,
        chars: warlordMarks.current,
        members: memberMarks.current,
        lens: lensRef.current,
      }, art);
    });

    if (process.env.NODE_ENV !== "production") {
      (window as unknown as { __map?: MLMap }).__map = m;
    }

    return () => {
      ready.current = false;
      ship.current = null;
      crewPool.clear();
      warlordPool.clear();
      memberPool.clear();
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
    paint(m, chapter, world, ship.current, {
      crews: crewFlags.current,
      chars: warlordMarks.current,
      members: memberMarks.current,
      lens: lensRef.current,
    }, art);
  }, [chapter, world, art]);

  /* --------------------------------------------------- islands live-update */
  // The island source is set once at create. When positions change underneath us
  // (the /admin/place editor moves a pin), push the new features and re-fog so the
  // pin jumps immediately. A no-op in the main app, where world.islands is stable.
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    (m.getSource("islands") as GeoJSONSource | undefined)?.setData(features);
    paint(m, chapter, world, ship.current, {
      crews: crewFlags.current,
      chars: warlordMarks.current,
      members: memberMarks.current,
      lens: lensRef.current,
    }, art);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [features]);

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

  /* ------------------------------------------------------------------ lens */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    const on = lens !== "off";
    m.setLayoutProperty("presence-orbs", "visibility", on ? "visible" : "none");
    m.setLayoutProperty("presence-hit", "visibility", on ? "visible" : "none");
    // Re-run the sweep so the pools hide (or recolor) immediately.
    paint(m, chapterRef.current, world, ship.current, {
      crews: crewFlags.current,
      chars: warlordMarks.current,
      members: memberMarks.current,
      lens,
    }, art);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lens]);

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
  const hoveredPresence = hover?.presence ?? null;
  const hoveringFog = hover !== null && hover.island === null && !hoveredPresence;

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

      {/* Cartographic overlays — decorative, never intercept pointer events. A soft
          vignette and a faint procedural paper grain turn the canvas into an aged
          chart. Both are offline (the grain is an inline SVG turbulence data-URI). */}
      {!glFailed && (
        <>
          <div className="mapVignette pointer-events-none absolute inset-0 z-[5]" />
          <div className="mapGrain pointer-events-none absolute inset-0 z-[5]" />
          <div className="pointer-events-none absolute bottom-6 left-[316px] z-[6]">
            <CompassRose size={72} />
          </div>
        </>
      )}

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
          {hoveredPresence ? (
            <div className="min-w-[150px] rounded-md border border-rope bg-ink/95 px-2.5 py-1.5 shadow-2xl backdrop-blur">
              <div className="text-[12px] font-medium text-parchment">{hoveredPresence.name}</div>
              {hoveredPresence.crewName && (
                <div className="mt-0.5 font-mono text-[10px] tracking-[0.06em] text-gold">
                  {hoveredPresence.crewName}
                </div>
              )}
              {hoveredPresence.vesselName && hoveredPresence.kind !== "warlord" && (
                <div className="mt-0.5 font-mono text-[9px] text-muted">
                  ⛵ {hoveredPresence.vesselName}
                </div>
              )}
              {/* Power lines. If the property reached the feature it is revealed
                  by construction — there is no gate to re-check here. */}
              {hoveredPresence.fruitName && (
                <div className="mt-0.5 font-mono text-[9px] text-muted">
                  {hoveredPresence.fruitName} · {hoveredPresence.fruitType}
                </div>
              )}
              {hoveredPresence.hakiTypes && (
                <div className="mt-0.5 font-mono text-[9px] text-muted">
                  Haki:{" "}
                  {hoveredPresence.hakiTypes
                    .split("|")
                    .map((t) => HAKI_STYLE[t as HakiType].label)
                    .join(" · ")}
                </div>
              )}
              <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                {hoveredPresence.confidence === "canon"
                  ? "placement from the story"
                  : hoveredPresence.confidence === "derived"
                    ? "home-base placement"
                    : "representative anchorage"}
                {!hoveredPresence.verified && " · unverified"}
              </div>
            </div>
          ) : hoveringFog ? (
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
type PresencePools = {
  crews: Map<string, PresenceHandle>;
  chars: Map<string, PresenceHandle>;
  members: Map<string, PresenceHandle>;
  lens: PresenceLens;
};

/** Hide a pooled presence marker AND scrub its user-visible content out of the DOM. */
function hidePresence(h: PresenceHandle) {
  if (!h.shown && !h.populated) return;
  h.parts.el.style.display = "none";
  h.parts.label.textContent = "";
  if (h.parts.flag) h.parts.flag.innerHTML = "";
  if (h.parts.hull) h.parts.hull.innerHTML = "";
  if (h.parts.ring) h.parts.ring.textContent = "";
  h.shown = false;
  h.populated = false;
  h.paintKey = null;
}

function paint(
  m: MLMap,
  ch: number,
  world: World,
  ship: ShipHandle | null,
  pools?: PresencePools,
  art?: Art,
) {
  // THE VOYAGE. Re-derive the traveled route and the ship's position for this
  // (fractional) chapter and push both. The line grows leg by leg; the ship glides
  // along the active leg; the vessel glyph swaps at the acquisition chapters.
  const { path, ship: pos } = voyageGeometryAt(world.voyage.waypoints, ch);
  (m.getSource("voyage") as GeoJSONSource | undefined)?.setData(voyageLine(path));
  if (ship) {
    const vessel = vesselAtChapter(world.vessels, ch);
    if (pos && vessel) {
      ship.marker.setLngLat(pos);
      // The Going Merry and Thousand Sunny have real renders; the barrel and the
      // nameless first boat do not, and keep their original SVG.
      const shipArt = art?.ships[vessel.slug];
      ship.glyph.innerHTML = shipArt ? artImg(shipArt, 34) : vesselGlyph(vessel.slug);
      ship.label.textContent = vessel.name;
      ship.marker.getElement().style.display = "";
    } else {
      ship.marker.getElement().style.display = "none";
    }
  }

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

  // WHO SAILS HERE (Phase 5). Flags and monograms are pooled HTML markers,
  // diffed against the active window so a frame where nothing changes touches
  // no DOM. Orbs are one setData, same as the voyage line. Hiding a marker
  // CLEARS its name and flag — a backward scrub re-fogs the DOM, not just the
  // pixels.
  if (pools) {
    if (pools.lens === "off") {
      for (const h of pools.crews.values()) hidePresence(h);
      for (const h of pools.chars.values()) hidePresence(h);
      for (const h of pools.members.values()) hidePresence(h);
      (m.getSource("presence") as GeoJSONSource | undefined)?.setData({
        type: "FeatureCollection",
        features: [],
      });
    } else {
      const layout = presenceLayout(world, ch);
      for (const crew of world.presence.crews) {
        const h = pools.crews.get(crew.slug);
        if (!h) continue;
        const placed = layout.get(crew.slug);
        if (!placed) {
          hidePresence(h);
          continue;
        }
        // Position is set every frame: the cluster fan moves a flag when a
        // NEIGHBOUR arrives or leaves, even though its own window is unchanged.
        h.marker.setLngLat([placed.lng, placed.lat]);
        // The flag stays a crew landmark under every lens, so its key is the
        // window alone — lens flips never touch this DOM.
        if (h.shown && h.paintKey === String(placed.w.order)) continue; // DOM unchanged
        if (!h.populated) {
          // Real Jolly Roger where we have one; original SVG mark otherwise.
          const flagArt = art?.flags[crew.slug];
          h.parts.flag.innerHTML = flagArt ? artImg(flagArt, 30) : jollyRogerSvg(crew.slug, { size: 20 });
          // The crew's real ship rides under the flag; fall back to the ink hull cue.
          const shipArt = crew.vessel ? art?.ships[crew.vessel.slug] : undefined;
          h.parts.hull.innerHTML = shipArt
            ? artImg(shipArt, 26)
            : crew.vessel
              ? crewHullGlyph(crewColor(crew.slug))
              : "";
          h.parts.label.textContent = crew.name;
          h.parts.label.style.color = crewColor(crew.slug);
          h.populated = true;
        }
        h.parts.el.style.display = "";
        h.shown = true;
        h.paintKey = String(placed.w.order);
      }
      // Member portrait rings (Phase 6). They sit in the same ring as the member
      // orbs and are RE-POSITIONED EVERY FRAME: a new arrival changes n, which
      // changes every sibling's angle — so this can't ride the flag's DOM skip.
      for (const crew of world.presence.crews) {
        const placed = layout.get(crew.slug);
        const revealed = placed ? crew.members.filter((mm) => mm.fromChapter <= ch) : [];
        const n = revealed.length;
        for (const mem of crew.members) {
          const mh = pools.members.get(mem.slug);
          if (!mh) continue;
          const idx = revealed.findIndex((r) => r.slug === mem.slug);
          if (!placed || idx === -1) {
            hidePresence(mh); // crew off the board, or member not yet joined
            continue;
          }
          const a = (idx / Math.max(1, n)) * Math.PI * 2 - Math.PI / 2;
          mh.marker.setLngLat([placed.lng + Math.cos(a) * 2.1, placed.lat + Math.sin(a) * 1.5]);
          if (!mh.populated) {
            const portrait = art?.characters[mem.slug];
            if (!portrait) {
              hidePresence(mh); // no art — the GeoJSON orb dot underneath carries it
              continue;
            }
            mh.parts.ring.innerHTML =
              `<img src="${portrait}" alt="" draggable="false" ` +
              `style="display:block;width:100%;height:100%;object-fit:cover;border-radius:9999px;">`;
            mh.parts.ring.style.border = `1.4px solid ${crewColor(crew.slug)}`;
            mh.populated = true;
          }
          mh.parts.el.style.display = "";
          mh.shown = true;
          mh.paintKey = String(placed.w.order);
        }
      }
      for (const c of world.presence.characters) {
        const h = pools.chars.get(c.slug);
        if (!h) continue;
        const placed = layout.get(c.slug);
        if (!placed) {
          hidePresence(h);
          continue;
        }
        h.marker.setLngLat([placed.lng, placed.lat]);
        // The ring follows the lens: its key carries the color, so a mid-scrub
        // reveal recolors the ring the frame it happens. Content (portrait or
        // monogram) populates once; colors re-apply on every key change.
        const color = lensColor(pools.lens, { crewSlug: c.crewSlug, fruit: c.fruit, haki: c.haki, kind: "warlord" }, ch);
        const key = `${placed.w.order}|${pools.lens}|${color}`;
        if (h.shown && h.paintKey === key) continue;
        if (!h.populated) {
          // A real portrait fills the crew-colour ring; the monogram letter is the
          // fallback. The img is a child node, so hidePresence's textContent="" wipes
          // it on a backward scrub — no future Warlord's face URL lingers in the DOM.
          const portrait = art?.characters[c.slug];
          if (portrait) {
            h.parts.ring.innerHTML =
              `<img src="${portrait}" alt="" draggable="false" ` +
              `style="display:block;width:100%;height:100%;object-fit:cover;border-radius:9999px;">`;
          } else {
            h.parts.ring.textContent = c.name[0];
          }
          h.parts.label.textContent = c.name;
          h.populated = true;
        }
        h.parts.ring.style.borderColor = color;
        h.parts.ring.style.color = color;
        h.parts.el.style.display = "";
        h.shown = true;
        h.paintKey = key;
      }
      (m.getSource("presence") as GeoJSONSource | undefined)?.setData(
        presenceOrbs(world, ch, layout, pools.lens),
      );
    }
  }
}
