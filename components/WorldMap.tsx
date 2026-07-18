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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  type Map as MLMap,
  type Marker as MLMarker,
  type GeoJSONSource,
  type StyleSpecification,
  type MapMouseEvent,
  type ExpressionSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { World, WorldIsland, WorldFruitReveal, WorldHakiFact } from "@/lib/canon";
import type { Art } from "@/lib/art";
import {
  voyageGeometryAt, vesselAtChapter, presenceWindowAt, statusHoldersAt, isIslandFogged,
} from "@/lib/canon";
import { crewColor, WARLORD_COLOR } from "@/lib/crews";
import {
  lensColor, matchesFocus, resolveFocus, focusKey, revealedFruit, revealedHaki, HAKI_STYLE,
  type ResolvedFocus,
} from "@/lib/lenses";
import type { Focus, Lens, PresenceLens } from "@/lib/lenses";
import { poneglyphSvg, poneglyphInk, PONEGLYPH_INK, ROAD_PONEGLYPH_INK, type PoneglyphKind } from "./marks/poneglyph";
import { globeProven } from "@/config/projection-overrides";
import { createGlbLayer, type GlbLayer } from "./glb-layer";
import { OrbitControls } from "./OrbitControls";
import { buildModels, type RuntimeAsset, type RuntimeModel } from "./runtime-models";
import { altitudeT, columnOpacity, expandSkyWaypoints, SKY_BASE, SKY_BODY, transitBase } from "./skypiea";
import { makeWanoElement, WANO_ANCHOR, wanoOpacity } from "./wano";
import {
  depthT, expandDiveWaypoints, shimmerOpacity, transitBase as diveBase,
} from "./fishman";
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
   * Follow-cam: the camera chases the ship as the chapter moves (scrub, hotkeys,
   * playback). A user drag/rotate breaks it via onFollowBreak; zooming does not —
   * zooming while tracking is the point.
   */
  follow?: boolean;
  onFollowBreak?: () => void;
  /**
   * The isolate filter: when set, presence marks that fail lib/lenses'
   * matchesFocus dim to near-invisible. Geography, the voyage, and the ship
   * never dim — the filter isolates presence, not the world.
   */
  focus?: Focus | null;
  /** Camera target for non-island destinations (a search hit on a crew). The
      key forces re-fly when the same anchor is picked twice. */
  flyTarget?: { lng: number; lat: number; key: number; zoom?: number; pitch?: number } | null;
  /** The cinematic journey is running — the map flies the voyage itself. */
  journey?: boolean;
  /**
   * The journey's per-frame camera program, as a REF the schedule mutates —
   * zoom/pitch/orbit targets plus an optional stage focus to frame instead of
   * the ship (the Baratie sits off the raw voyage line). A ref, not state:
   * these change every frame and must never re-render React (the setState
   * version threw "Maximum update depth exceeded" mid-run — measured). The
   * chase damps toward whatever is in here; pitch is what makes both the 3D
   * models and the vertical 2.5D story cards actually visible.
   */
  journeyCam?: React.RefObject<{
    zoom: number;
    pitch: number;
    orbitDegPerSec: number;
    focus: [number, number] | null;
  } | null>;
  /** ?record=1 only: init WebGL with preserveDrawingBuffer so the in-browser
   * recorder can composite the canvas. Never on by default (perf). */
  preserveBuffer?: boolean;
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
  // 10B: island landmasses — warm dark earth under a parchment coastline.
  // The coast stroke carries the shape (same rule as the hollow rings).
  isle: "#2c2a22",
  isleCoast: "#7d7050",
} as const;

// Biome inks — muted chart tones near C.isle's value range so the map stays
// one cohesive document. The biome property ships for every island (same
// class as slug/debut); it only reaches PIXELS through the revealed(ch)-gated
// opacity channels in paint(), so a fogged island's tint is painted at 0.
const BIOME_FILL: Record<string, string> = {
  winter: "#2b3440",
  summer: "#33321f",
  desert: "#3a3120",
  jungle: "#243024",
  volcanic: "#382320",
  sky: "#343841",
};
const BIOME_COAST: Record<string, string> = {
  winter: "#93a4b5",
  summer: "#9a9058",
  desert: "#a08a58",
  jungle: "#6f8a62",
  volcanic: "#8a5a48",
  sky: "#b9c2cc",
};
const byBiome = (table: Record<string, string>, fallback: string): ExpressionSpecification =>
  ["match", ["get", "biome"], ...Object.entries(table).flat(), fallback] as unknown as ExpressionSpecification;

// Landfall terrain inks (gen_terrain.py kinds). Fills only — the true line
// kinds live in TERRAIN_LINE. Warm ember/frost/sand/cloud values sit inside
// the same muted chart register as the biome fills they draw on top of.
const TERRAIN_FILL: Record<string, string> = {
  "fire-ground": "#4a2318",
  "ice-ground": "#2e4358",
  "boundary": "#241a16",
  "volcano": "#5a3020",
  "crater": "#1f130d",
  "dune-a": "#362c1a",
  "dune-b": "#514226",
  "delta": "#2f4028",
  "cloud-puff-a": "#454c58",
  "cloud-puff-b": "#565e6b",
  "cloud-puff-c": "#6a7280",
  // Fish-Man Island, ten thousand metres down. Cold, dark, and lit from inside
  // its own bubble — the exact inverse of Skypiea's pearl.
  "abyss-veil": "#071e2c",
  "seabed": "#123640",
  "coral-a": "#3d6470",
  "coral-b": "#5c4a63",
  "shimmer-soft": "#12384a",
  "shimmer-core": "#2f7a94",
  // Thriller Bark — a ship, so: timber, not soil.
  "hull-deck": "#2b2320",
  "mast": "#443630",
  // rgba, not hex: terrain-fill's own opacity is the zoom x chapter crossfade,
  // so a kind that needs to be SEEN THROUGH carries its alpha in its ink.
  "grave-fog": "rgba(150,163,176,0.28)",
  // Whole Cake — sponge and cream, muted to chart inks. It should read as a
  // cake without leaving the atlas's register and turning into a birthday card.
  "cake-tier-a": "#5a3340",
  "cake-tier-b": "#7a5560",
  "candy-dot": "#c98aa0",
  // Water 7 — the city, its stone paler than the sea it stands in.
  "city-ground": "#3a3730",
  "dock": "#4e463a",
  // Enies Lobby — an island over a hole; the chasm is the darkest ink here.
  "chasm": "#02060a",
  "court-ground": "#3b3a33",
  "tower": "#6b6354",
  // Marineford — the crescent bay and the fortress that closes it.
  "fort-ground": "#39352f",
  "bay-water": "#0a2136",
  "fortress": "#585044",
  // Impel Down — the levels, darkening as they go down.
  "prison-level-0": "#2a2622",
  "prison-level-1": "#1d1a17",
  // Drum — snow, and the flat-topped drums standing in it.
  "snowfield": "#39434e",
  "drum-peak": "#4d5865",
  "drum-cap": "#68747f",
  // Zou — the back of a walking elephant.
  "back-ground": "#2c3a2a",
  "whale-tree": "#4a5c3c",
  "leg": "#3a3128",
};
const TERRAIN_LINE: Record<string, string> = {
  "crevasse": "#9fb4c8",
  "river": "#3d6a8a",
  "riverbank": "#2a2416",
  "cloud-wisp": "#d5dce6",
  "bubble-dome-outer": "#8fd4e8",
  "bubble-dome-inner": "#6fb3d2",
  "dome-highlight": "#dff2f8",
  "hull-rail": "#8a7256",
  "rigging": "#6d6355",
  "icing-river": "#e8d4d8",
  "canal": "#4f86a8",
  "fountain": "#9fd0e0",
  "falls": "#7fa8c4",
  "prison-ring": "#0f0d0b",
  "trunk": "#4a4034",
};
const byKind = (table: Record<string, string>, fallback: string): ExpressionSpecification =>
  ["match", ["get", "kind"], ...Object.entries(table).flat(), fallback] as unknown as ExpressionSpecification;

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

/**
 * 6E: every mark scales with zoom through one CSS var set by the map's zoom
 * handler. The scale lives on an inner wrapper — MapLibre owns the marker
 * root's transform for positioning, so scaling the root would fight it.
 */
function makeScaleWrap(origin = "50% 100%"): HTMLDivElement {
  const wrap = document.createElement("div");
  wrap.style.transform = "scale(var(--gli-mark-scale, 1))";
  wrap.style.transformOrigin = origin;
  return wrap;
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
  const wrap = makeScaleWrap();

  // The crew's Jolly Roger, flying above the ship. Set once (the crew never
  // changes); the vessel below it swaps as the reader sails.
  const flag = document.createElement("div");
  flag.style.lineHeight = "0";
  flag.style.marginBottom = "-3px";
  flag.style.filter =
    "drop-shadow(0 1px 2px rgba(0,0,0,0.7)) drop-shadow(0 0 3px rgba(239,230,212,0.3))";

  // THE ship. A soft dark shadow sits it ON the water; the gold aura keeps it
  // findable against the abyss at planet zoom.
  const glyph = document.createElement("div");
  glyph.style.filter =
    "drop-shadow(0 2px 3px rgba(0,0,0,0.6)) drop-shadow(0 0 7px rgba(227,176,75,0.45))";
  glyph.style.lineHeight = "0";

  const label = document.createElement("div");
  label.style.marginTop = "2px";
  label.style.fontSize = "9px";
  label.style.letterSpacing = "0.16em";
  label.style.textTransform = "uppercase";
  label.style.color = "rgba(239,230,212,0.82)";
  label.style.whiteSpace = "nowrap";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";

  wrap.appendChild(flag);
  wrap.appendChild(glyph);
  wrap.appendChild(label);
  el.appendChild(wrap);
  return { el, flag, glyph, label };
}

/** The live handles paint() needs to move and restyle the ship each frame. */
type ShipHandle = {
  marker: MLMarker;
  glyph: HTMLDivElement;
  label: HTMLDivElement;
  /** The ship's sea shadow during the Skypiea ascent/descent — pinned to the
      stream base and fading as the ship climbs (the 2.5D altitude cue). */
  shadow: MLMarker;
  shadowEl: HTMLDivElement;
};

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
  const wrap = makeScaleWrap();

  // A light halo behind the dark emblem cutout keeps a Jolly Roger readable
  // against the abyss — the flags are the map's landmarks now (6E).
  const flag = document.createElement("div");
  flag.style.lineHeight = "0";
  flag.style.marginBottom = "-2px";
  flag.style.filter =
    "drop-shadow(0 1px 2px rgba(0,0,0,0.7)) drop-shadow(0 0 3px rgba(239,230,212,0.35))";

  const hull = document.createElement("div");
  hull.style.lineHeight = "0";
  hull.style.filter = "drop-shadow(0 2px 3px rgba(0,0,0,0.55))";

  const label = document.createElement("div");
  label.style.marginTop = "2px";
  label.style.fontSize = "9px";
  label.style.letterSpacing = "0.14em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";

  wrap.appendChild(flag);
  wrap.appendChild(hull);
  wrap.appendChild(label);
  el.appendChild(wrap);
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
  const wrap = makeScaleWrap("50% 50%");

  const ring = document.createElement("div");
  ring.style.width = "26px";
  ring.style.height = "26px";
  ring.style.margin = "0 auto";
  ring.style.borderRadius = "9999px";
  ring.style.border = `1.6px solid ${WARLORD_COLOR}`;
  ring.style.background = "rgba(7,19,36,0.78)";
  ring.style.color = WARLORD_COLOR;
  ring.style.fontSize = "11px";
  ring.style.lineHeight = "23px";
  ring.style.overflow = "hidden";
  ring.style.fontFamily = "var(--font-geist-mono), monospace";
  ring.style.filter = "drop-shadow(0 1px 3px rgba(0,0,0,0.7))";

  const label = document.createElement("div");
  label.style.marginTop = "2px";
  label.style.fontSize = "8px";
  label.style.letterSpacing = "0.12em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.color = "rgba(140,154,181,0.9)";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";

  wrap.appendChild(ring);
  wrap.appendChild(label);
  el.appendChild(wrap);
  return { el, ring, label };
}

/**
 * Build (once, per stone) a poneglyph stele. Pooled exactly like the Warlord
 * ring: created once, moved and re-labelled per frame, `display:none` when the
 * stone is not in play. The label is the KIND, never the stone's name — "road"
 * is a category, but "Road Poneglyph — the Whale Tree" beside an island is a
 * sentence about the plot, so the name lives in the hover tooltip where the
 * reader has to ask for it.
 */
/**
 * The Baratie: a fish-shaped boat, because that is what it is.
 *
 * It is the only waypoint on the route with no island under it — the voyage
 * carries it as a slug-less stop at ch. 43, since the wiki has no Island Box
 * for a restaurant that floats. So it gets a marker rather than a coastline:
 * the sea does not have a Baratie on it, the Baratie is ON the sea.
 */
function makeBaratieElement(): { el: HTMLDivElement; wrap: HTMLDivElement } {
  const el = document.createElement("div");
  el.className = "baratieMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";
  const wrap = makeScaleWrap("50% 100%");

  const boat = document.createElement("div");
  boat.style.margin = "0 auto";
  boat.style.width = "34px";
  boat.style.height = "20px";
  boat.style.filter = "drop-shadow(0 1px 3px rgba(0,0,0,0.75))";
  // hull as a fish: blunt head at the bow, tail fin at the stern, one round eye
  boat.innerHTML = `<svg width="34" height="20" viewBox="0 0 34 20" fill="none" aria-hidden="true">
    <path d="M4.5 12.5c2-5 7-8.5 13-8.5 4.6 0 8 2 10 4.6L31 5.2v10.2l-3.4-3.2C25.6 14.7 22.2 17 17.5 17c-6 0-11-2.6-13-4.5z"
          fill="#7d5a3c" stroke="#2a1d12" stroke-width="1" stroke-linejoin="round"/>
    <circle cx="24.5" cy="9" r="1.4" fill="#f0e2c8" stroke="#2a1d12" stroke-width=".6"/>
    <path d="M8 9.5c2.5-1 5-1.4 7.5-1.2" stroke="#c9a06a" stroke-width=".9" stroke-linecap="round"/>
  </svg>`;

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "7px";
  label.style.letterSpacing = "0.14em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.color = "rgba(201,160,106,0.95)";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";
  label.textContent = "Baratie";

  wrap.appendChild(boat);
  wrap.appendChild(label);
  el.appendChild(wrap);
  // `wrap` is handed back, not `el`: MapLibre owns the marker element's own
  // opacity (that is how it fades marks behind the globe), so anything written
  // to el.style.opacity is silently overwritten on the next camera move. Same
  // trap the Skypiea sea-shadow fell into.
  return { el, wrap };
}

function makePoneglyphElement(kind: PoneglyphKind = "historical"): {
  el: HTMLDivElement;
  stone: HTMLDivElement;
  label: HTMLDivElement;
} {
  const el = document.createElement("div");
  el.className = "poneglyphMarker";
  el.style.display = "none";
  el.style.pointerEvents = "none";
  el.style.textAlign = "center";
  const wrap = makeScaleWrap("50% 100%");

  const stone = document.createElement("div");
  stone.style.margin = "0 auto";
  stone.style.width = "18px";
  stone.style.height = "21px";
  stone.style.filter = "drop-shadow(0 1px 3px rgba(0,0,0,0.8))";
  stone.innerHTML = poneglyphSvg(18, kind);

  const label = document.createElement("div");
  label.style.marginTop = "1px";
  label.style.fontSize = "7px";
  label.style.letterSpacing = "0.14em";
  label.style.textTransform = "uppercase";
  label.style.whiteSpace = "nowrap";
  label.style.color = "rgba(95,125,156,0.95)";
  label.style.fontFamily = "var(--font-geist-mono), monospace";
  label.style.textShadow = "0 1px 3px rgba(0,0,0,0.9)";

  wrap.appendChild(stone);
  wrap.appendChild(label);
  el.appendChild(wrap);
  return { el, stone, label };
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
  const wrap = makeScaleWrap("50% 50%");

  const ring = document.createElement("div");
  ring.style.width = "22px";
  ring.style.height = "22px";
  ring.style.margin = "0 auto";
  ring.style.borderRadius = "9999px";
  ring.style.overflow = "hidden";
  ring.style.background = "rgba(7,19,36,0.72)";
  ring.style.filter = "drop-shadow(0 1px 3px rgba(0,0,0,0.7))";

  const label = document.createElement("div"); // unused; keeps hidePresence uniform

  wrap.appendChild(ring);
  wrap.appendChild(label);
  el.appendChild(wrap);
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
function presenceOrbs(
  world: World, ch: number, layout: Map<string, PlacedPresence>, lens: Lens,
  focus: ResolvedFocus | null = null,
) {
  // dim: 0|1 stamped per feature — the isolate filter, resolved by the same
  // matchesFocus predicate the HTML pools use. Rebuilt every frame like the
  // rest of the source, so clearing the focus un-dims on the next paint.
  const dimOf = (e: { slug?: string; crewSlug?: string | null; fruit: WorldFruitReveal | null; haki: WorldHakiFact[] }) =>
    focus && !matchesFocus(focus, e, ch) ? 1 : 0;
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
          dim: dimOf({ slug: m.slug, crewSlug: crew.slug, fruit: m.fruit, haki: m.haki }),
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
        dim: dimOf({ slug: crew.slug, crewSlug: crew.slug, fruit: null, haki: [] }),
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
        dim: dimOf({ slug: c.slug, crewSlug: c.crewSlug, fruit: c.fruit, haki: c.haki }),
        color: lensColor(lens, { crewSlug: c.crewSlug, affiliation: c.affiliation, fruit: c.fruit, haki: c.haki, kind: "warlord" }, ch),
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

/**
 * THE RUNTIME-3D PILOT — the first Blender asset the app has ever rendered.
 *
 * The flag NAME is the asset track's own, from manifests/runtime-3d.json — not
 * invented here. It is an env var rather than the build-time literal in
 * config/flags.ts, because an env flag is the right interface for a pilot THEY
 * want toggled without a code change.
 *
 * The honest cost, measured rather than assumed: this block does NOT
 * dead-code-eliminate. An unset NEXT_PUBLIC_* is not inlined (the bundler cannot
 * prove a value it was never given), so ~1KB of dead branch ships — you can find
 * `knockup3d` in .next/static/ with the flag off. That is precisely the argument
 * config/flags.ts makes for the registry's literal `false`, which DOES eliminate
 * (0 files, grep-proven).
 *
 * What matters here is a different rule, and it holds: WORKFLOW says a model is
 * "never fetched before its chapter gate", and with the flag off the source is
 * never added, so the raster is never requested — verified at 0 network calls.
 *
 * The geometry is theirs too: four corner coordinates, declared in the manifest
 * beside `mode: "maplibre_image_source"`. The chapter beats they wrote —
 * {start:235, top:237, dwellEnd:300, splash:304} — are byte-identical to ASCENT
 * in components/skypiea.ts, and their `runtime_rule` names our own function:
 * "opacity follows columnOpacity(ch)". They built the asset against our code, so
 * the integration is one source and one gate we already had.
 *
 * BOTH the raster and the GLB, which is what `enable_glb_when` asks for: "feature
 * flag on, close zoom, supported projection, chapter gate open". The raster is
 * the far-zoom read and `runtime_policy.default` really is "fallback_raster" —
 * you have to dive to reach the model. This block used to end "the RASTER, not
 * the GLB… the ascent was built deliberately without three.js and that stays a
 * decision somebody makes on purpose." The decision got made on purpose;
 * components/glb-layer.ts is the renderer, and that file carries the reasoning.
 */
const RUNTIME_3D_ON = process.env.NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS === "1";
const KNOCK_UP_RASTER = "/art/runtime/skypiea-knock-up-stream.png";
const KNOCK_UP_GLB = "/art/runtime/skypiea-knock-up-stream.glb";
const KNOCK_UP_GLB_ID = "knockup-glb";
/** manifests/runtime-3d.json -> models[skypiea-knock-up-stream].integration.coordinates */
const KNOCK_UP_CORNERS: [[number, number], [number, number], [number, number], [number, number]] = [
  [-93.804825, 17.9745],
  [-88.467575, 17.9745],
  [-88.467575, 7.3],
  [-93.804825, 7.3],
];

/**
 * THE ASCENT STANDS UP, and this is the number that lets it.
 *
 * glb-layer draws in METRES (both of MapLibre's getMatrixForModel implementations
 * scale by a metric constant), and a .glb carries no real-world scale. So a
 * metres-per-unit has to come from somewhere, and the manifest declares none —
 * `mode: "maplibre_image_source"` plus four corners describes the FLAT fallback,
 * not a standing model. That absence is the trap: any number typed here would be
 * an invention wearing a constant's clothes.
 *
 * It is derivable, though, from the only two SEMANTIC spatial facts the manifest
 * states — `source_anchor` [-91.1362, 8.2] and `destination_anchor`
 * [-91.1362, 17.0745] — which are byte-identical to our own SKY_BASE and
 * SKY_BODY. Codex anchored the model to the constants in components/skypiea.ts.
 * The model's Y=0 plane is "Sea eruption footprint"; its Y-max is "Skypiea land
 * heart" and "Skypiea cloud shelf". So the model's vertical span IS the trip from
 * one anchor to the other, and one division gives the scale.
 *
 * What that buys is the thing worth having. The map's ascent is a 2.5D fake:
 * altitude is drawn as LATITUDE, which is why Skypiea's pin sits ~987km north of
 * the eruption rather than above it. Scale the model this way and the fake and
 * the truth agree in magnitude — the column stands exactly as tall as the map
 * believes the sky is far. Zoom out and Skypiea is north; dive in and the stream
 * is 987km of real vertical water. Neither read contradicts the other's numbers,
 * and they never share a screen, because `enable_glb_when` says close zoom.
 *
 * REJECTED: deriving the scale from KNOCK_UP_CORNERS (it would give 127,636 m/unit
 * and an 800km column). Those corners frame a RENDER — margins, glow, whatever the
 * orthographic camera needed. The anchors are semantics. Framing is not.
 */
const KNOCK_UP_MODEL_SPAN_UNITS = 6.225642 - -0.041364; // stats.bounds_blender, Z-up (== glTF Y)
const KNOCK_UP_M_PER_UNIT =
  (Math.abs(SKY_BODY[1] - SKY_BASE[1]) * 111_195) / KNOCK_UP_MODEL_SPAN_UNITS; // ≈ 157,460

/**
 * "Close zoom", made a number. The raster reaches full opacity at 4.6; from there
 * to 5.4 it hands over to the model, so the stream is one object at every zoom
 * rather than two competing ones — the same rule the vector column already
 * follows underneath. Below 4.6 the GLB is not merely hidden but ABSENT: no
 * layer, no three.js chunk, no 2.5MB.
 */
const GLB_MIN_ZOOM = 4.6;
const GLB_FULL_ZOOM = 5.4;

/**
 * THE ASSET TRACK'S FLAG, which is not the pilots' flag. runtime-3d.json v2 moved
 * the flag per-model: the 14 scene systems declare NEXT_PUBLIC_RUNTIME_3D_ASSETS,
 * the two original vertical-transition pilots keep
 * NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS. Merging them would be a tidy-up that
 * deletes a distinction the asset track is actively maintaining: they gate
 * different tracks, and it names both.
 *
 * Everything else that used to live here — Fish-Man Island's constants, its
 * measured 1-unit-is-1-degree scale, the rejected corner derivation, the
 * mercator-only reasoning — moved to components/runtime-models.ts, which is one
 * table for every model rather than one block per island. That is the asset
 * track's integration rule #1 ("do not create one loader per island"), and the
 * proof it was right is that this block was about to be copied eleven times.
 */
const RUNTIME_ASSETS_ON = process.env.NEXT_PUBLIC_RUNTIME_3D_ASSETS === "1";
// The East Blue 2.5D story layer (sim-models owns every gate; the dynamic
// import keeps zod + the artifact out of flag-off bundles). Its host
// self-registers zoomend/moveend listeners on first call.
const EAST_BLUE_2D_ON = process.env.NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS === "1";
function syncSims(m: MLMap, ch: number) {
  if (!EAST_BLUE_2D_ON) return;
  void import("@/components/sim-models").then((s) => s.syncSimulations(m, ch));
}

/**
 * The live models, or null when their gates are shut. Module scope because
 * paint() is module scope and there is exactly one map; `unload_when_hidden:
 * true` means these are null far more often than not.
 */
let knockUpLayer: GlbLayer | null = null;
/** The chapter the model's per-frame opacity closure reads. paint() owns it. */
let knockUpChapter = 1;

/** 0..1 for the model: the zoom hand-off, times the beat the manifest names. */
function glbOpacity(m: MLMap, ch: number): number {
  const t = Math.min(1, Math.max(0, (m.getZoom() - GLB_MIN_ZOOM) / (GLB_FULL_ZOOM - GLB_MIN_ZOOM)));
  return columnOpacity(ch) * t;
}

/**
 * The raster's opacity, which is one expression with a conditional tail. The
 * fade-out past GLB_MIN_ZOOM only exists once `ready()` — hand over to a model
 * that has not loaded and a reader on a cold cache watches the stream dissolve
 * into nothing for however long 2.5MB takes. The fallback stays until there is
 * something to fall forward to.
 */
function rasterOpacity(ch: number): ExpressionSpecification {
  const co = columnOpacity(ch);
  return knockUpLayer?.ready()
    ? ["interpolate", ["linear"], ["zoom"], 3.2, 0, GLB_MIN_ZOOM, co, GLB_FULL_ZOOM, 0]
    : ["interpolate", ["linear"], ["zoom"], 3.2, 0, GLB_MIN_ZOOM, co];
}

/**
 * `enable_glb_when: "feature flag on, close zoom, supported projection, chapter
 * gate open"` — the manifest's four conditions, as code.
 *
 * Three are here: the flag at the call sites, the zoom, and columnOpacity(ch) > 0
 * for the chapter. The fourth is absent BY VERIFICATION, not by oversight: both
 * projections are supported. glb-layer draws through getMatrixForModel, which
 * MapLibre implements for the globe as well as for mercator, so there is no
 * projection to refuse. Writing `if (projection === "mercator")` here would be
 * theatre — a check that never fires, implying a limit we do not have. The reason
 * `projection_unsupported` still exists in lib/scenes.ts is that it is real for
 * anything drawing through MapLibre's own shaders; it is simply not real for this.
 *
 * Add-on-demand IS the gate, same as the raster: a layer's onAdd is what fetches
 * three.js and the 2.5MB model, so a chapter-1 reader at zoom 6 requests neither.
 */
/**
 * THE MODEL TABLE. Null until the artifact lands — see loadRuntimeModels().
 */
let MODELS: RuntimeModel[] | null = null;
const modelLayers = new Map<string, GlbLayer>();
let modelChapter = 1;

/**
 * The artifact is 60KB and a STATIC import would put every byte of it in the main
 * bundle — fetched by a chapter-1 reader with the flag off, because an unset
 * NEXT_PUBLIC_* is not inlined and nothing here dead-code-eliminates. Same
 * reasoning as three.js in glb-layer, same shape: import it when a flag that is
 * on asks for it.
 *
 * Stated precisely, because the loose version is a trap this session fell into
 * three separate times: the chunk still EXISTS in .next/static — grep finds
 * "yakigashi-island" there with the flag off — and that is what a lazy chunk
 * looks like. Presence is not fetching. Measured in a browser: flag off, ch900,
 * 51 requests, the artifact's chunk among none of them.
 *
 * `footprintFor` is the visual_fit target, and it is the app's own geometry: the
 * silhouette this map already draws for the island at that anchor. 11 of 13
 * anchors land on a canon island exactly, so a model is scaled to cover the shape
 * the reader is already looking at. The 3D replaces the 2D at the 2D's size.
 */
/**
 * The island's silhouette span, in degrees, nearest this anchor.
 *
 * READ FROM THE FILE, NOT FROM THE MAP, and the first version got this wrong in a
 * way worth recording. It called `m.querySourceFeatures("silhouettes")`, which
 * only ever returns features from tiles that are LOADED RIGHT NOW. The table is
 * built once; if the island's tile happened not to be loaded at that instant —
 * which, on first paint at a far zoom, is every island — the footprint came back
 * null and every fitted model was skipped PERMANENTLY, with a reason that read
 * like a data problem. Ten of eleven islands silently vanished and the sheet said
 * "visual_fit needs a silhouette".
 *
 * The silhouettes are a static file the map already fetches (`/geo/islands.
 * silhouettes.json`, wired at the geojson source below), so reading it directly is
 * deterministic, viewport-independent, and free — the browser has it cached from
 * the source that drew the coastlines.
 */
function footprintFrom(sil: GeoJSON.FeatureCollection | null, lngLat: [number, number]): number | null {
  if (!sil) return null;
  let best: number | null = null;
  let bestD = Infinity;
  for (const f of sil.features) {
    const g = f.geometry;
    if (g.type !== "Polygon" && g.type !== "MultiPolygon") continue;
    const rings = (g.type === "Polygon" ? g.coordinates : g.coordinates.flat()) as [number, number][][];
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const ring of rings) for (const [x, y] of ring) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
    const d = Math.hypot((minX + maxX) / 2 - lngLat[0], (minY + maxY) / 2 - lngLat[1]);
    // 1.5 degrees: an anchor is either the island's own derived pin (11 of 13
    // match to 1e-4) or it is not that island at all. The window only forgives
    // an anchor placed at a landmark inside the island rather than its centroid.
    if (d < bestD && d < 1.5) { bestD = d; best = Math.max(maxX - minX, maxY - minY); }
  }
  return best;
}

async function loadRuntimeModels(m: MLMap): Promise<void> {
  if (MODELS) return;
  const [mod, sil] = await Promise.all([
    import("@/data/generated/runtime_assets.json"),
    fetch("/geo/islands.silhouettes.json").then((r) => r.json() as Promise<GeoJSON.FeatureCollection>).catch(() => null),
  ]);
  const assets = (mod.default as { assets: unknown[] }).assets as unknown as RuntimeAsset[];
  MODELS = buildModels(
    assets,
    (lngLat) => footprintFrom(sil, lngLat),
    globeProven,
    () => modelChapter,
  );
  // The data loads async, and the syncModels call that KICKED OFF this load
  // returned early (MODELS was null) without adding a thing. Nothing re-invokes
  // syncModels on its own — triggerRepaint only redraws — so a reader who has
  // finished diving before the data lands would sit on an island with no model
  // until they nudge the camera. Run it now, at the chapter that call recorded.
  syncModels(m, modelChapter);
  m.triggerRepaint();
}

/**
 * Every model's gate, in one loop. `enable_glb_when: "feature flag on, close
 * zoom, supported projection, chapter gate open"` — four conditions, once, rather
 * than once per island. Adding the twelfth is a data change.
 */
function syncModels(m: MLMap, ch: number) {
  modelChapter = ch;
  if (!MODELS) { void loadRuntimeModels(m); return; }
  const proj = (m.getProjection()?.type ?? "globe") as "globe" | "mercator";
  const zoomOk = m.getZoom() >= GLB_MIN_ZOOM;
  for (const model of MODELS) {
    if (model.skipped) continue;
    if (model.id === "skypiea-knock-up-stream") continue; // its own module owns it
    const open = ch >= model.reveal && zoomOk && model.projections.includes(proj);
    const live = modelLayers.get(model.id);
    if (open && !live) {
      const layer = createGlbLayer({
        id: `glb-${model.id}`,
        url: model.glb,
        lngLat: model.lngLat,
        metersPerUnit: model.metersPerUnit,
        opacity: () => Math.min(1, Math.max(0, (m.getZoom() - GLB_MIN_ZOOM) / (GLB_FULL_ZOOM - GLB_MIN_ZOOM))),
        nodeVisible: model.nodeVisible,
        hideNode: model.hideNode,
        onReady: () => {
          if (process.env.NODE_ENV !== "production") {
            (window as unknown as { __glbReady?: boolean }).__glbReady = true;
          }
        },
      });
      m.addLayer(layer, "voyage-glow");
      modelLayers.set(model.id, layer);
    } else if (!open && live) {
      if (m.getLayer(`glb-${model.id}`)) m.removeLayer(`glb-${model.id}`);
      modelLayers.delete(model.id);
    } else if (live) {
      // Scrubbing BACKWARDS has to re-fog geometry already on the GPU.
      live.regate();
    }
  }
}

function syncKnockUpGlb(m: MLMap, ch: number) {
  knockUpChapter = ch;
  const open = columnOpacity(ch) > 0 && m.getZoom() >= GLB_MIN_ZOOM;
  const present = !!m.getLayer(KNOCK_UP_GLB_ID);
  if (open && !present) {
    knockUpLayer = createGlbLayer({
      id: KNOCK_UP_GLB_ID,
      url: KNOCK_UP_GLB,
      // The model's own Y=0 plane is "Sea eruption footprint" — it lands on the
      // sea at the manifest's source_anchor, which is our SKY_BASE.
      lngLat: SKY_BASE,
      metersPerUnit: KNOCK_UP_M_PER_UNIT,
      opacity: () => glbOpacity(m, knockUpChapter),
      onReady: () => {
        // Now the hand-off is safe to write.
        if (m.getLayer("knockup3d")) m.setPaintProperty("knockup3d", "raster-opacity", rasterOpacity(knockUpChapter));
        // Dev-only, beside window.__map and for the same reason: "the model is
        // on the GPU" is otherwise unobservable from a test, and audit_glb would
        // have to sleep and hope instead of assert.
        if (process.env.NODE_ENV !== "production") {
          (window as unknown as { __glbReady?: boolean }).__glbReady = true;
        }
      },
    });
    m.addLayer(knockUpLayer, "voyage-glow"); // under the route: the ship rides UP it
  } else if (!open && present) {
    m.removeLayer(KNOCK_UP_GLB_ID);
    knockUpLayer = null;
    if (m.getLayer("knockup3d")) m.setPaintProperty("knockup3d", "raster-opacity", rasterOpacity(ch));
  }
}

/**
 * The Baratie's stop on the route. It has no island record — the wiki has no
 * Island Box for a floating restaurant — so it rides the voyage as a slug-less
 * waypoint and gets a marker instead of a coastline.
 */
const BARATIE_CHAPTER = 43;

/** Revealed: the reader has met this island. */
const revealed = (ch: number): ExpressionSpecification => ["<=", ["get", "debut"], ch];

/**
 * The voyage with both vertical legs written in: Skypiea's ascent up the
 * Knock-Up Stream, and the dive to Fish-Man Island.
 *
 * A COMPOSITION, not two systems. Each expander splices virtual waypoints
 * around its own island and leaves the rest of the list alone, so they commute —
 * and everything downstream (the ship position, the dashed path, the follow-cam)
 * reads the voyage only through this one function. That is why neither vertical
 * leg needed a special case anywhere else: to the interpolator, going up a
 * water spout and going down to the seabed are both just the next waypoint.
 *
 * Memoized per waypoint array so the per-frame paint sweep stays
 * allocation-free; worldAtChapter/Readout keep the pure canon list.
 */
const skyExpandedCache = new WeakMap<object, ReturnType<typeof expandSkyWaypoints>>();
function expandedWaypoints(wps: World["voyage"]["waypoints"]) {
  let e = skyExpandedCache.get(wps);
  if (!e) {
    e = expandDiveWaypoints(expandSkyWaypoints(wps));
    skyExpandedCache.set(wps, e);
  }
  return e;
}

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
  follow = false,
  onFollowBreak,
  focus = null,
  flyTarget = null,
  journey = false,
  journeyCam,
  preserveBuffer = false,
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
  const poneglyphMarks = useRef<Map<string, PresenceHandle>>(new Map());
  const baratie = useRef<{ marker: MLMarker; el: HTMLDivElement; wrap: HTMLDivElement } | null>(null);
  const wano = useRef<{ marker: MLMarker; el: HTMLDivElement; img: HTMLImageElement } | null>(null);
  // paint() runs on the chapter tween; it reads the live lens through this ref.
  const lensRef = useRef(lens);
  useEffect(() => {
    lensRef.current = lens;
  }, [lens]);
  const focusRef = useRef<Focus | null>(focus);

  /**
   * The focus, with any holder set resolved for this chapter.
   *
   * "Emperors" and "Marines" are set-membership questions about the world at a
   * chapter, not properties of an orb, so they cost an O(statuses) scan to
   * answer. Resolving once per (focus, chapter) instead of once per orb per
   * paint keeps a 4x playback sweep from re-deriving the same set eighty times a
   * frame. Memoised on the floored chapter because that is the gate's own
   * resolution — the tween's fractional chapter cannot change who holds a seat.
   */
  const resolvedFocus = useCallback((): ResolvedFocus | null => {
    const f = focusRef.current;
    if (!f) return null;
    const ch = Math.floor(chapterRef.current);
    const key = `${focusKey(f)}@${ch}`;
    if (resolvedRef.current?.key !== key) {
      resolvedRef.current = { key, rf: resolveFocus(world, f, ch) };
    }
    return resolvedRef.current.rf;
  }, [world]);
  const resolvedRef = useRef<{ key: string; rf: ResolvedFocus } | null>(null);

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

  // Follow-cam. One damped step per paint frame; when the sweep stops, a
  // self-terminating rAF finishes the convergence (decay ~0.82^n, so ~half a
  // second from anywhere). jumpTo, never easeTo: easeTo restarts its own
  // animation every frame and fights itself.
  const followRef = useRef(follow);
  const breakRef = useRef(onFollowBreak);
  useEffect(() => {
    breakRef.current = onFollowBreak;
  }, [onFollowBreak]);
  const chaseRaf = useRef<number | null>(null);

  // The cinematic journey rides the SAME camera path as the follow chase, on
  // purpose. The first version gave it its own rAF; it read chapterRef a frame or
  // two behind the ship and visibly TRAILED the route line. The chase runs inside
  // the paint effect, in the same commit as each swept update (chapterRef is
  // refreshed by an earlier effect on the same [chapter] dep), so it is
  // frame-synced to the ship — which is exactly why manual scrubbing tracks the
  // line and the old journey did not.
  const journeyRef = useRef(journey);
  // The camera program ref comes straight from the engine (stable identity);
  // reading .current per chase step needs no effects and no re-renders.
  const journeyCamRef = useRef(journeyCam ?? null);
  journeyCamRef.current = journeyCam ?? null;
  /** Timestamp of the previous chase step, for orbit deg/sec integration. */
  const chasePrevT = useRef<number | null>(null);

  const chase = useCallback(function chaseStep() {
    chaseRaf.current = null;
    const m = map.current;
    if (!m || !ready.current) return;
    const journeying = journeyRef.current;
    if (!followRef.current && !journeying) return;
    const { ship: pos } = voyageGeometryAt(expandedWaypoints(world.voyage.waypoints), chapterRef.current);
    if (!pos) return;
    // The schedule's camera program for this instant (zoom/pitch/orbit/focus).
    // A dwell frames the STAGE, not the ship — the Baratie's scene anchor and
    // Marineford's model both sit off the raw voyage line. Null = the ship.
    const cam = journeying ? journeyCamRef.current?.current ?? null : null;
    const focus = cam?.focus ?? null;
    const target = focus ?? pos;
    const c = m.getCenter();
    const dLng = ((((target[0] - c.lng) % 360) + 540) % 360) - 180; // shortest way round
    const dLat = target[1] - c.lat;
    // The journey glues the ship near screen centre so it never drifts off the
    // line — a much tighter pull than the follow chase, which leads the ship a
    // little while you scrub. Zoom eases separately toward the schedule's target.
    const k = journeying ? 0.5 : 0.18;
    const upd: { center: [number, number]; zoom?: number; pitch?: number; bearing?: number } = {
      center: [c.lng + dLng * k, c.lat + dLat * k],
    };
    let settled = true;
    const nowT = performance.now();
    const dt = chasePrevT.current !== null ? Math.min(0.1, (nowT - chasePrevT.current) / 1000) : 0;
    chasePrevT.current = nowT;
    if (cam) {
      const z = m.getZoom();
      const dz = cam.zoom - z;
      if (Math.abs(dz) > 0.008) {
        upd.zoom = z + dz * 0.12;
        settled = false;
      }
      // Pitch rides the schedule — up for dives, transits and story stages
      // (vertical cards and Blender models are invisible top-down), back flat
      // for the sea legs.
      const p = m.getPitch();
      const dp = cam.pitch - p;
      if (Math.abs(dp) > 0.2) {
        upd.pitch = p + dp * 0.09;
        settled = false;
      }
      // The orbit drift — the walk-around-the-model shot. Integrated in
      // deg/sec so frame rate doesn't change the speed; when the drift ends
      // the bearing damps home to north.
      const b = m.getBearing();
      if (cam.orbitDegPerSec !== 0) {
        upd.bearing = b + cam.orbitDegPerSec * dt;
        settled = false;
      } else if (Math.abs(b) > 0.3) {
        upd.bearing = b * 0.94;
        settled = false;
      }
    } else if (journeying) {
      // No program yet (first frames): keep today's flat glue.
      settled = Math.abs(m.getPitch()) < 0.2;
      if (!settled) upd.pitch = m.getPitch() * 0.91;
    }
    if (Math.hypot(dLng, dLat) < 0.02 && settled) return; // fully settled
    m.jumpTo(upd);
    // Keep stepping ourselves whenever unfinished business remains. The paint
    // effect drives a step per swept frame during travel — but a DWELL holds
    // the chapter, paint stops, and without this tail the camera froze mid-
    // flight to the stage and the orbit never turned (measured: 1.4° of drift
    // across a 6s dwell). chaseStep nulls chaseRaf on entry, so a paint-driven
    // step and this tail never stack.
    if (!journeying || chaseRaf.current === null) {
      chaseRaf.current = requestAnimationFrame(chaseStep);
    }
  }, [world]);

  useEffect(() => {
    followRef.current = follow;
    if (!follow) {
      if (chaseRaf.current !== null) cancelAnimationFrame(chaseRaf.current);
      chaseRaf.current = null;
      return;
    }
    chase(); // re-engaging the follow recenters on the ship immediately
  }, [follow, chase]);

  // ─── THE CINEMATIC JOURNEY: JUST THE HELM LOCK ─────────────────────────────
  // The camera itself is driven by `chase` above (frame-synced). This effect only
  // locks manual input for the run — no pan, no globe-rotate, no grab-and-spin,
  // so a stray touch mid-recording cannot derail the shot — and restores it after.
  useEffect(() => {
    journeyRef.current = journey;
    const m = map.current;
    if (!m || !ready.current) return;
    if (journey) {
      m.dragPan.disable();
      m.dragRotate.disable();
      // THE TRAIL IS THE STORY. At the resting style the voyage line is a faint
      // thread you cannot read at speed; the journey makes it the hero — a thick
      // gold wake with a bright glow — so the route the ship traces is the thing
      // you watch. Restored on stop.
      m.setPaintProperty("voyage-glow", "line-width", 16);
      m.setPaintProperty("voyage-glow", "line-blur", 10);
      m.setPaintProperty("voyage-glow", "line-opacity", 0.6);
      m.setPaintProperty("voyage-line", "line-color", C.goldLit);
      m.setPaintProperty("voyage-line", "line-width", [
        "interpolate", ["linear"], ["zoom"], 0, 3, 3, 4, 6, 5.5,
      ] as never);
      m.setPaintProperty("voyage-line", "line-opacity", 1);
      chase(); // begin tracking immediately, without waiting for the first frame
    } else {
      m.dragPan.enable();
      // dragRotate stays OFF — the globe never free-spins now; rotation is only
      // the deliberate hold-to-lock-a-target gesture (see below).
      // A run stopped mid-dwell leaves the camera pitched/turned; lay it back.
      if (m.getPitch() > 0.5 || Math.abs(m.getBearing()) > 0.5) {
        m.easeTo({ pitch: 0, bearing: 0, duration: 600 });
      }
      // Restore the resting voyage style.
      m.setPaintProperty("voyage-glow", "line-width", 6);
      m.setPaintProperty("voyage-glow", "line-blur", 7);
      m.setPaintProperty("voyage-glow", "line-opacity", 0.3);
      m.setPaintProperty("voyage-line", "line-color", C.parchment);
      m.setPaintProperty("voyage-line", "line-width", [
        "interpolate", ["linear"], ["zoom"], 0, 1.4, 3, 2, 6, 2.8,
      ] as never);
      m.setPaintProperty("voyage-line", "line-opacity", 0.85);
    }
  }, [journey, chase]);

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
    /** A poneglyph stele. Only ever a stone the reader has been told about. */
    stone?: {
      name: string;
      kind: string;
      note: string | null;
      label: string;
      confidence: string;
      verified: boolean;
    } | null;
  } | null>(null);

  // MapLibre needs a WebGL context and there are real browsers that will not give
  // it one: hardware acceleration off, a GPU blocklist, a privacy extension, a
  // headless CI runner. Without a guard the constructor throws, the throw escapes
  // the effect, and the whole route unmounts behind an error overlay — the chapter
  // axis, the roster and the scrubber all die with the canvas. They shouldn't: the
  // panels are plain data and render fine on their own. So the map degrades alone.
  const [glFailed, setGlFailed] = useState(false);
  // The island currently locked as the orbit pivot (non-null only while you hold
  // to rotate), and whether the camera is tilted/turned at all. Both drive the
  // OrbitControls chrome; the machinery lives in the map-init effect.
  const [orbitTarget, setOrbitTarget] = useState<string | null>(null);
  const [tilted, setTilted] = useState(false);

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
        // 10B: original generated coastline polygons (public/geo/, MIT — ours).
        // Fetched as a static asset so 311KB of geometry stays out of the bundle.
        silhouettes: { type: "geojson", data: "/geo/islands.silhouettes.json" },
        // Landfall: hero-island terrain (fire/ice, dunes, cloud terraces).
        // Static like the silhouettes; features carry {slug, debut, kind, sort}
        // and their pixels ride the same revealed(ch) gate in paint().
        terrain: { type: "geojson", data: "/geo/islands.terrain.json" },
        // Presence orbs: rebuilt per frame from the swept chapter. Only REVEALED
        // entities are ever in this source — spoiler safety is structural here,
        // not an opacity trick.
        presence: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        // The stones. Same rule as presence: only the ones the reader has been
        // told about are ever in the source, so a fogged stone has nothing to
        // hover, nothing to query, and no pixels.
        poneglyphs: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        // Yonko territory: a soft disc per Emperor, rebuilt per frame from who
        // actually holds a seat at this chapter. Same rule as everything else —
        // if it is in this source, the reader has been told.
        territory: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
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

        // 10B: landmasses. Invisible at orbit, fading in as you approach so the
        // chart resolves from "pins on water" into "a world with coastlines".
        // Opacity is chapter-gated per frame by paint() — fog has no shoreline.
        // THE FLOAT ILLUSION: Skypiea's shadow on the sea, under every
        // landmass. Its own outline, shrunk — the same seed guarantees the
        // match. Chapter-gated in paint() like the coastline it belongs to.
        { id: "sky-shadow", type: "fill", source: "terrain",
          filter: ["in", ["get", "kind"], ["literal", ["sky-shadow-soft", "sky-shadow-core"]]],
          paint: { "fill-color": "#04070d", "fill-opacity": 0 } },

        // THE CARVED-UP SEA. At orbit the New World should look claimed, because
        // it is: four Emperors, and everyone else lives in the gaps between
        // them. Fades out by z4 — up close this is a map of places, not a map
        // of who is winning.
        { id: "territory", type: "fill", source: "territory",
          paint: {
            "fill-color": ["get", "color"],
            "fill-opacity": ["interpolate", ["linear"], ["zoom"], 1.4, 0.14, 4.0, 0],
          } },

        { id: "island-shapes", type: "fill", source: "silhouettes",
          paint: { "fill-color": byBiome(BIOME_FILL, C.isle), "fill-opacity": 0 } },

        // LANDFALL. Painted ground for the hero islands, between the landmass
        // fill and its coast stroke so the ink outline always stays on top.
        // All start at opacity 0; paint() runs the zoom-x-chapter crossfade.
        { id: "terrain-fill", type: "fill", source: "terrain",
          // the sky-* furniture (shadow, column) has its own layers + gating
          filter: ["!", ["in", ["get", "kind"], ["literal",
            ["sky-shadow-soft", "sky-shadow-core", "sky-column-1", "sky-column-2", "sky-column-3", "sky-jet",
             "shimmer-soft", "shimmer-core",
             // lines, not fills — the mirror of terrain-line's allowlist
             "bubble-dome-outer", "bubble-dome-inner", "dome-highlight",
             "hull-rail", "rigging", "icing-river", "canal", "fountain",
             "falls", "prison-ring", "trunk"]]]],
          layout: { "fill-sort-key": ["get", "sort"] } as never,
          paint: {
            "fill-color": byKind(TERRAIN_FILL, C.isle),
            "fill-opacity": 0,
          } },
        { id: "terrain-glow", type: "line", source: "terrain",
          filter: ["==", ["get", "kind"], "fire-glow"],
          paint: {
            "line-color": "#ff7a45",
            "line-width": 2.6,
            "line-blur": 6,
            "line-opacity": 0,
          } },
        { id: "terrain-line", type: "line", source: "terrain",
          // line layers also outline polygons — restrict to the true lines
          filter: ["in", ["get", "kind"], ["literal", ["crevasse", "river", "riverbank", "cloud-wisp",
            "bubble-dome-outer", "bubble-dome-inner", "dome-highlight",
            "hull-rail", "rigging", "icing-river", "canal", "fountain",
            "falls", "prison-ring", "trunk"]]],
          paint: {
            "line-color": byKind(TERRAIN_LINE, C.isleCoast),
            "line-width": ["match", ["get", "kind"],
              "riverbank", 3.2, "river", 1.3, "cloud-wisp", 0.9,
              "bubble-dome-outer", 1.4, "bubble-dome-inner", 0.9, "dome-highlight", 1.8,
              "hull-rail", 1.6, "rigging", 0.7, "icing-river", 2.6, "canal", 1.8,
              "fountain", 1.1, "falls", 1.2, "prison-ring", 0.6, "trunk", 5.0, 0.8] as never,
            "line-opacity": 0,
          } },

        { id: "island-shapes-coast", type: "line", source: "silhouettes",
          paint: {
            "line-color": byBiome(BIOME_COAST, C.isleCoast),
            "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.5, 5, 1.5],
            "line-opacity": 0,
          } },

        // The Grand Line: the sea route. Gold, because it is the voyage.
        { id: "grand-glow", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 9, "line-blur": 9, "line-opacity": 0.22 } },
        { id: "grand", type: "line", source: "grand", paint: { "line-color": C.gold, "line-width": 1.1, "line-opacity": 0.75 } },

        // The Red Line: the continent. Clay, because it is land.
        { id: "red-glow", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 10, "line-blur": 10, "line-opacity": 0.25 } },
        { id: "red", type: "line", source: "red", paint: { "line-color": C.redLine, "line-width": 2.4, "line-opacity": 0.9 } },

        // THE KNOCK-UP STREAM. Nested pearl trapezoids from the sea up to
        // Skypiea's south coast (inner = brighter: the fake gradient), under
        // the voyage line so the dashed route visibly rides UP the column.
        // Opacity is columnOpacity(ch), set per frame in paint().
        { id: "sky-column", type: "fill", source: "terrain",
          filter: ["in", ["get", "kind"], ["literal", ["sky-column-1", "sky-column-2", "sky-column-3"]]],
          paint: { "fill-color": "#b9c2cc", "fill-opacity": 0 } },
        { id: "sky-jet", type: "line", source: "terrain",
          filter: ["==", ["get", "kind"], "sky-jet"],
          paint: { "line-color": "#dfe7f2", "line-width": 1.6, "line-blur": 4, "line-opacity": 0 } },

        // THE DIVE SCAR. The mirror of the stream, and it lives beside it for
        // the same reason: both are things happening to the SEA, not to an
        // island, so neither rides the terrain layers' zoom crossfade — you
        // should be able to see the water close over from orbit.
        // Opacity is shimmerOpacity(ch), set per frame in paint().
        { id: "dive-shimmer", type: "fill", source: "terrain",
          filter: ["in", ["get", "kind"], ["literal", ["shimmer-soft", "shimmer-core"]]],
          paint: { "fill-color": byKind(TERRAIN_FILL, "#12384a"), "fill-opacity": 0 } },

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
            // dim=1 is the isolate filter: non-matching orbs fall to a whisper
            "circle-opacity": ["case", ["==", ["get", "dim"], 1], 0.05, 0.9],
            "circle-stroke-color": C.parchment,
            "circle-stroke-width": ["match", ["get", "kind"], "warlord", 1.2, 0.6],
            "circle-stroke-opacity": ["case", ["==", ["get", "dim"], 1], 0.05, byConfidence(0.85, 0.55, 0.3)],
          },
        },
        {
          id: "presence-hit",
          type: "circle",
          source: "presence",
          layout: { visibility: lens !== "off" ? "visible" : "none" },
          paint: { "circle-radius": 11, "circle-color": "rgba(0,0,0,0)" },
        },

        // THE GLINT. At orbit the steles themselves are too small to read, so
        // each known stone leaves a single dot on the water — about ten pixels
        // across the whole globe, which is the point: "there are secrets written
        // into this world, and you have found some of them". It fades out as the
        // stele resolves on approach so the two never draw at once.
        {
          id: "poneglyph-glint",
          type: "circle",
          source: "poneglyphs",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 1.5, 3, 2.2],
            // The Road stones glint in their own aged crimson — the reader is
            // counting a set of four, and the map should read like the story.
            "circle-color": ["match", ["get", "kind"], "road", ROAD_PONEGLYPH_INK, PONEGLYPH_INK] as never,
            "circle-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 0.9, 3.4, 0],
            "circle-stroke-color": C.parchment,
            "circle-stroke-width": 0.5,
            "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 2.2, 0.5, 3.4, 0],
          },
        },
        {
          id: "poneglyph-hit",
          type: "circle",
          source: "poneglyphs",
          paint: { "circle-radius": 12, "circle-color": "rgba(0,0,0,0)" },
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
        // Recording only: lets the compositor read the WebGL canvas back per
        // frame. Costs a buffer swap, which is why it rides ?record=1 and not
        // the default path. (v5 moved the GL attrs under canvasContextAttributes.)
        ...(preserveBuffer ? { canvasContextAttributes: { preserveDrawingBuffer: true } } : {}),
        center: [-20, 6],
        zoom: 1.9,
        minZoom: 0.4,
        // 8.5, not deeper: the hero islands' 128-pt rings stay smooth to here;
        // regular 56-pt coastlines go visibly polygonal much past it.
        maxZoom: 8.5,
        // 75, up from the default 60: orbiting a 3D island wants to look at it
        // nearly side-on (towers, tiers, a waterfall column), and 60 is too
        // shallow for that. Only reachable once you have dived into a model.
        maxPitch: 75,
        // NB: `padding` is a CAMERA option, not a MapOptions one — it is applied via
        // setPadding() on load, below.
        attributionControl: false,
        // One world, not an infinite tiling strip. This is a chart of a planet.
        renderWorldCopies: false,
        // OFF, always. The built-in dragRotate spun the globe on right/ctrl-drag,
        // which felt like the world "turning circular" while just navigating.
        // Rotation is now only the deliberate hold-to-lock-a-target gesture below,
        // so a plain drag ALWAYS pans, freely, at any zoom on any projection.
        dragRotate: false,
        // Arrow keys belong to the chapter scrub (Atlas), not the camera —
        // MapLibre's KeyboardHandler would otherwise pan/rotate whenever the
        // canvas has focus, fighting the chapter hotkeys.
        keyboard: false,
      });
    } catch (err) {
      console.warn("[dead-reckoning] map disabled, no WebGL context:", err);
      setGlFailed(true);
      return;
    }
    map.current = m;

    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    // 6E: one CSS var drives every HTML mark's size. Floor of 1 at the resting
    // zoom (1.9) so the Merry and the Jolly Rogers read WITHOUT zooming; grows
    // toward ~2.2x as you dive so the marks feel anchored to the world, capped
    // before labels turn into billboards.
    const applyMarkScale = () => {
      const s = Math.min(2.2, Math.max(1, Math.pow(2, (m!.getZoom() - 1.9) * 0.5)));
      holder.current?.style.setProperty("--gli-mark-scale", s.toFixed(3));
    };
    m.on("zoom", applyMarkScale);
    applyMarkScale();

    // The model's gate is half chapter and half ZOOM, and paint() only runs on
    // the chapter tween — so without this, diving toward an erupting stream would
    // never add the layer. Cheap: a getLayer check and an early return.
    if (RUNTIME_3D_ON || RUNTIME_ASSETS_ON || EAST_BLUE_2D_ON) {
      const syncGlb = () => {
        if (RUNTIME_3D_ON) syncKnockUpGlb(m!, chapterRef.current);
        // Fish-Man Island also gates on PROJECTION, and setProjection fires
        // neither zoom nor moveend — hence the explicit third listener.
        if (RUNTIME_ASSETS_ON) syncModels(m!, chapterRef.current);
        syncSims(m!, chapterRef.current);
      };
      m.on("zoom", syncGlb);
      m.on("moveend", syncGlb);
      m.on("projectiontransition", syncGlb);

      // ─── HOLD TO ORBIT A LOCKED ISLAND ─────────────────────────────────
      // A plain drag ALWAYS pans — navigate freely, any zoom, any projection, and
      // the globe never spins on its own (dragRotate is off). To ROTATE, press and
      // HOLD: after a short beat the nearest island locks as the pivot, the world
      // centres on it, and dragging orbits AROUND it (left/right = spin, up/down =
      // tilt). Release returns to free pan. A quick drag is never a rotate — the
      // hold has to resolve first — which is exactly what "won't let me move"
      // needed: nothing auto-disables the pan anymore.
      //
      // Custom pointer handling because setBearing/setPitch work on BOTH
      // projections, unlike the built-in dragRotate (globe-only), and because the
      // pivot must be a chosen island, not the screen centre.
      const canvas = m.getCanvas();
      const HOLD_MS = 260; // press this long, holding still, to lock and orbit
      const MOVE_CANCEL = 6; // px of travel that turns a would-be hold into a pan
      const orbit = { active: false, downX: 0, downY: 0, bearing: 0, pitch: 0, ptr: -1 };
      let holdTimer: ReturnType<typeof setTimeout> | null = null;

      const nearestRevealedIsland = (clientX: number, clientY: number): WorldIsland | null => {
        const r = canvas.getBoundingClientRect();
        const ll = m.unproject([clientX - r.left, clientY - r.top]);
        let best: WorldIsland | null = null;
        let bd = 30; // degrees — generous; a press near an island locks it
        for (const isl of world.islands) {
          if (isl.lng == null || isl.lat == null) continue;
          if (isIslandFogged(isl, chapterRef.current)) continue; // never lock a fogged island
          const d = Math.hypot(isl.lng - ll.lng, isl.lat - ll.lat);
          if (d < bd) { bd = d; best = isl; }
        }
        return best;
      };

      const engage = (clientX: number, clientY: number, ptrId: number) => {
        const target = nearestRevealedIsland(clientX, clientY);
        if (!target) return; // nothing to lock onto — stay in free pan
        orbit.active = true;
        orbit.downX = clientX;
        orbit.downY = clientY;
        orbit.bearing = m.getBearing();
        orbit.pitch = m.getPitch();
        orbit.ptr = ptrId;
        m.dragPan.disable(); // now the drag orbits, not pans
        breakRef.current?.(); // taking the wheel yields the follow-chase
        m.jumpTo({ center: [target.lng, target.lat] }); // orbit pivots on the target
        try { canvas.setPointerCapture(ptrId); } catch {}
        canvas.style.cursor = "grabbing";
        setOrbitTarget(target.name);
      };

      const disengage = () => {
        if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
        if (!orbit.active) return;
        orbit.active = false;
        m.dragPan.enable(); // free pan returns
        try { if (canvas.hasPointerCapture(orbit.ptr)) canvas.releasePointerCapture(orbit.ptr); } catch {}
        canvas.style.cursor = "";
        setOrbitTarget(null);
      };

      const onDown = (e: PointerEvent) => {
        if (e.button !== 0 || journeyRef.current) return; // the journey owns the helm
        orbit.downX = e.clientX;
        orbit.downY = e.clientY;
        if (holdTimer) clearTimeout(holdTimer);
        holdTimer = setTimeout(() => { holdTimer = null; engage(e.clientX, e.clientY, e.pointerId); }, HOLD_MS);
      };
      const onMove = (e: PointerEvent) => {
        if (orbit.active) {
          m.setBearing(orbit.bearing - (e.clientX - orbit.downX) * 0.4);
          m.setPitch(Math.max(0, Math.min(75, orbit.pitch + (e.clientY - orbit.downY) * 0.35)));
          return;
        }
        // Moved before the hold resolved -> it's a pan; abandon the would-be lock.
        if (holdTimer && Math.hypot(e.clientX - orbit.downX, e.clientY - orbit.downY) > MOVE_CANCEL) {
          clearTimeout(holdTimer);
          holdTimer = null;
        }
      };
      canvas.addEventListener("pointerdown", onDown);
      canvas.addEventListener("pointermove", onMove);
      canvas.addEventListener("pointerup", disengage);
      canvas.addEventListener("pointercancel", disengage);

      // Keep the "level view" affordance honest: it shows whenever the camera is
      // tilted or turned, so you can straighten up after a hold-orbit.
      const syncTilt = () => setTilted(m.getPitch() > 1 || Math.abs(m.getBearing()) > 1);
      m.on("pitch", syncTilt);
      m.on("rotate", syncTilt);
      m.on("moveend", syncTilt);
    }

    // A drag or a user rotate is the reader taking the wheel — follow yields.
    // Programmatic camera moves (easeTo/jumpTo) fire neither with an
    // originalEvent, so the chase itself never breaks its own follow.
    m.on("dragstart", () => breakRef.current?.());
    m.on("rotatestart", (e) => {
      if ((e as { originalEvent?: unknown }).originalEvent) breakRef.current?.();
    });

    for (const l of WORLD_LABELS) {
      const el = document.createElement("div");
      el.className = "mapLabel";
      el.textContent = l.text;
      const size = l.kind === "sea" ? "13px" : "9px";
      el.style.fontSize = size;
      el.style.color = l.kind === "line" ? "rgba(239,230,212,.66)" : "rgba(140,154,181,.62)";
      if (l.kind === "belt") el.style.color = "rgba(91,104,128,.7)";
      // Phase 9: the seas are named in the sea-document face, like a real chart.
      if (l.kind === "sea") {
        el.style.fontFamily = "var(--font-document), Georgia, serif";
        el.style.fontStyle = "italic";
        el.style.textTransform = "none";
        el.style.letterSpacing = "0.3em";
      }
      new maplibregl.Marker({ element: el, opacityWhenCovered: "0" }).setLngLat(l.lngLat).addTo(m);
    }

    // The ship. One marker, moved and restyled every frame by paint(). It starts at
    // the first waypoint and hidden; paint() reveals it once the reader reaches ch. 1.
    const parts = makeShipElement();
    // The reader's own colors: the real Straw Hat flag where we have it.
    const ownFlag = art?.flags[world.voyage.crewSlug];
    parts.flag.innerHTML = ownFlag
      ? artImg(ownFlag, 26)
      : jollyRogerSvg(world.voyage.crewSlug, { size: 22 });
    const start = world.voyage.waypoints[0];
    const shipMarker = new maplibregl.Marker({ element: parts.el, opacityWhenCovered: "0.1" })
      .setLngLat(start ? [start.lng, start.lat] : [0, 0])
      .addTo(m);
    // The ascent shadow: a small dark ellipse on the sea, hidden until the
    // ship actually rides the Knock-Up Stream. The fade/scale live on an
    // INNER node — MapLibre owns the marker element's own opacity (the
    // behind-the-globe fade) and would clobber ours.
    const shadowWrap = document.createElement("div");
    shadowWrap.style.cssText = "pointer-events:none;";
    const shadowEl = document.createElement("div");
    shadowEl.style.cssText =
      "width:26px;height:10px;border-radius:9999px;background:#04070d;" +
      "filter:blur(2px);display:none;";
    shadowWrap.appendChild(shadowEl);
    const shipShadow = new maplibregl.Marker({ element: shadowWrap })
      .setLngLat(start ? [start.lng, start.lat] : [0, 0])
      .addTo(m);
    ship.current = {
      marker: shipMarker, glyph: parts.glyph, label: parts.label,
      shadow: shipShadow, shadowEl,
    };

    // The presence pools (Phase 5): one flag per crew, one monogram per Warlord,
    // built ONCE, hidden and EMPTY. paint() populates a marker only while its
    // window is active, and clears it again when it hides — the DOM at chapter 1
    // contains no future crew's name, even after a scrub to 1125 and back.
    const crewPool = crewFlags.current;
    const warlordPool = warlordMarks.current;
    const memberPool = memberMarks.current;
    for (const crew of world.presence.crews) {
      const p = makeCrewFlagElement();
      const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.1" })
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
      const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.1" })
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
        const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.1" })
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

    // One stele per stone, built once, hidden and EMPTY — the same pooling as
    // every other mark. A stone the reader has not been told about has no
    // element populated, so its name is not in the DOM to be read out.
    // The Baratie. Its position comes from the voyage waypoint itself — the
    // slug-less stop at ch. 43 — so the restaurant and the route can never
    // disagree about where dinner is.
    const bw = world.voyage.waypoints.find((w) => w.slug === null && w.chapter === BARATIE_CHAPTER);
    if (bw) {
      const parts = makeBaratieElement();
      const marker = new maplibregl.Marker({ element: parts.el, opacityWhenCovered: "0.1" })
        .setLngLat([bw.lng, bw.lat])
        .addTo(m);
      baratie.current = { marker, el: parts.el, wrap: parts.wrap };
    }

    // Wano — the marker-style country (see components/wano.ts for why it is a
    // sprite and why it stands still). Created hidden; paint() reveals it at
    // its verified arrival chapter.
    {
      const parts = makeWanoElement();
      const marker = new maplibregl.Marker({ element: parts.el, opacityWhenCovered: "0.1" })
        .setLngLat(WANO_ANCHOR)
        .addTo(m);
      wano.current = { marker, el: parts.el, img: parts.img };
    }

    const poneglyphPool = poneglyphMarks.current;
    for (const pg of world.poneglyphs) {
      const p = makePoneglyphElement(pg.kind);
      const marker = new maplibregl.Marker({ element: p.el, opacityWhenCovered: "0.1" })
        .setLngLat([0, 0])
        .addTo(m);
      poneglyphPool.set(pg.slug, {
        marker,
        parts: { el: p.el, ring: p.stone, label: p.label },
        shown: false,
        paintKey: null,
        populated: false,
      });
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
      // Then the stones. Ahead of islands for the same reason presence is: a
      // stele stands ON an island pin, and the more specific mark should win.
      const gf = m.queryRenderedFeatures(e.point, { layers: ["poneglyph-hit"] })[0];
      if (gf) {
        m.getCanvas().style.cursor = "pointer";
        setHover({
          x: e.point.x,
          y: e.point.y,
          island: null,
          stone: {
            name: gf.properties?.name as string,
            kind: gf.properties?.kind as string,
            note: (gf.properties?.note as string) || null,
            label: gf.properties?.label as string,
            confidence: gf.properties?.confidence as string,
            verified: gf.properties?.verified === true || gf.properties?.verified === "true",
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
      const isFogged = island != null && isIslandFogged(island, chapterRef.current);

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
      onSelect(isIslandFogged(island, chapterRef.current) ? null : slug);
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
        poneglyphs: poneglyphMarks.current,
        baratie: baratie.current,
        wano: wano.current,
        lens: lensRef.current,
        focus: resolvedFocus(),
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
      if (chaseRaf.current !== null) cancelAnimationFrame(chaseRaf.current);
      chaseRaf.current = null;
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
      poneglyphs: poneglyphMarks.current,
      baratie: baratie.current,
        wano: wano.current,
      lens: lensRef.current,
      focus: resolvedFocus(),
    }, art);
    chase(); // one damped camera step per sweep frame; settles on its own after
  }, [chapter, world, art, chase]);

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
      poneglyphs: poneglyphMarks.current,
      baratie: baratie.current,
        wano: wano.current,
      lens: lensRef.current,
      focus: resolvedFocus(),
    }, art);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [features]);

  /* ------------------------------------------------------------ projection */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    m.setProjection({ type: projection });

    // A zoom that frames a sphere leaves a flat map cropped, and vice versa. The
    // toggle has to reframe or half the world falls off the edge. dragRotate stays
    // OFF on both projections — rotation is the hold-to-lock gesture, not a spin.
    if (projection === "globe") {
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
      poneglyphs: poneglyphMarks.current,
      baratie: baratie.current,
        wano: wano.current,
      lens,
      focus: resolvedFocus(),
    }, art);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lens]);

  /* ----------------------------------------------------------------- focus */
  useEffect(() => {
    focusRef.current = focus;
    const m = map.current;
    if (!m || !ready.current) return;
    // Re-run the sweep so orbs re-stamp their dim flag and pools re-class now.
    paint(m, chapterRef.current, world, ship.current, {
      crews: crewFlags.current,
      chars: warlordMarks.current,
      members: memberMarks.current,
      poneglyphs: poneglyphMarks.current,
      baratie: baratie.current,
        wano: wano.current,
      lens: lensRef.current,
      focus: resolvedFocus(),
    }, art);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  /* -------------------------------------------------------------- flyTarget */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current || !flyTarget) return;
    // A search pick just brings the island on screen (zoom 3.2). A directory
    // DIVE carries its own zoom/pitch to land you past GLB_MIN_ZOOM with the
    // camera tilted, so the 3D model is actually there when you arrive.
    m.easeTo({
      center: [flyTarget.lng, flyTarget.lat],
      zoom: flyTarget.zoom ?? Math.max(m.getZoom(), 3.2),
      pitch: flyTarget.pitch ?? m.getPitch(),
      duration: 1100,
    });
  }, [flyTarget]);

  /* --------------------------------------------------------------- selected */
  useEffect(() => {
    const m = map.current;
    if (!m || !ready.current) return;
    m.setFilter("islands-selected", ["==", ["get", "slug"], selected ?? " none"]);
    if (selected) {
      const i = bySlug.get(selected);
      if (i) m.easeTo({ center: [i.lng, i.lat], zoom: Math.max(m.getZoom(), 3.2), duration: 900 });
    }
  }, [selected, bySlug]);

  const hoveredIsland = hover?.island ?? null;
  const hoveredPresence = hover?.presence ?? null;
  const hoveredStone = hover?.stone ?? null;
  // "fog" is the LAST case, not the default: it means the reader hovered an
  // island they have not reached. A stone or a crew mark also carries no island,
  // so both have to be excluded or hovering a stele reads as "uncharted waters".
  const hoveringFog =
    hover !== null && hover.island === null && !hoveredPresence && !hoveredStone;

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
          <OrbitControls
            orbitTarget={orbitTarget}
            tilted={tilted}
            onLevel={() => map.current?.easeTo({ pitch: 0, bearing: 0, duration: 500 })}
          />
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
          {hoveredStone ? (
            <div className="min-w-[168px] max-w-[210px] rounded-md border border-rope bg-ink/95 px-2.5 py-1.5 shadow-2xl backdrop-blur">
              <div className="font-mono text-[8px] uppercase tracking-[0.2em]" style={{ color: poneglyphInk(hoveredStone.kind as PoneglyphKind) }}>
                {hoveredStone.kind === "road"
                  ? "Road Poneglyph"
                  : hoveredStone.kind === "instructional"
                    ? "Instructional Poneglyph"
                    : "Poneglyph"}
              </div>
              <div className="mt-0.5 text-[12px] font-medium leading-snug text-parchment">
                {hoveredStone.name}
              </div>
              <div className="mt-0.5 text-[10px] leading-snug text-muted">{hoveredStone.label}</div>
              {hoveredStone.note && (
                <div className="mt-0.5 font-mono text-[9px] text-gold-2">{hoveredStone.note}</div>
              )}
              <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2">
                {hoveredStone.confidence === "canon" ? "read on the page" : "placement inferred"}
                {!hoveredStone.verified && " · unverified"}
              </div>
            </div>
          ) : hoveredPresence ? (
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
  poneglyphs: Map<string, PresenceHandle>;
  baratie: { marker: MLMarker; el: HTMLDivElement; wrap: HTMLDivElement } | null;
  wano: { marker: MLMarker; el: HTMLDivElement; img: HTMLImageElement } | null;
  focus: ResolvedFocus | null;
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
  // Skypiea's virtual waypoints are in here — the ascent IS this same lerp.
  const { path, ship: pos } = voyageGeometryAt(expandedWaypoints(world.voyage.waypoints), ch);
  (m.getSource("voyage") as GeoJSONSource | undefined)?.setData(voyageLine(path));
  if (ship) {
    const vessel = vesselAtChapter(world.vessels, ch);
    if (pos && vessel) {
      ship.marker.setLngLat(pos);
      // The Going Merry and Thousand Sunny have real renders; the barrel and the
      // nameless first boat do not, and keep their original SVG.
      const shipArt = art?.ships[vessel.slug];
      ship.glyph.innerHTML = shipArt ? artImg(shipArt, 52) : vesselGlyph(vessel.slug);
      ship.label.textContent = vessel.name;
      ship.marker.getElement().style.display = "";

      // The 2.5D ascent (pure f(ch) — a backward scrub re-descends for free):
      // riding the stream, the ship swells slightly and throws white spray;
      // its sea shadow stays at the base, shrinking and fading as it climbs.
      const t = altitudeT(ch);
      const transit = t > 0 && t < 1;
      if (transit) {
        const bump = 1 + 0.25 * Math.sin(Math.PI * t);
        ship.glyph.style.transform = `scale(${bump.toFixed(3)})`;
        ship.glyph.style.filter = "drop-shadow(0 5px 5px rgba(223,231,242,0.45))";
        const base = transitBase(ch);
        ship.shadow.setLngLat(base);
        ship.shadowEl.style.display = "";
        ship.shadowEl.style.opacity = ((1 - t) * 0.5).toFixed(3);
        ship.shadowEl.style.transform = `scale(${(1 - t * 0.6).toFixed(3)})`;
      } else {
        ship.glyph.style.transform = "";
        ship.glyph.style.filter = "";
        ship.shadowEl.style.display = "none";
      }

      // THE DIVE — the same idea with the sign flipped. Aloft the ship swells
      // and throws light; under the sea it shrinks, the colour drains out of it,
      // and the water above closes into a haze. The transform and filter are set
      // on the GLYPH, an inner node: MapLibre owns the marker element's own
      // opacity (that is how it fades marks behind the globe), so writing there
      // gets silently clobbered.
      //
      // Written AFTER the ascent block on purpose, and safely: the two events
      // are 350 chapters apart, so at most one of them is ever mid-transit, and
      // the surface case of each is a no-op reset.
      const d = depthT(ch);
      if (d > 0) {
        const shrink = 1 - 0.3 * d;
        ship.glyph.style.transform = `scale(${shrink.toFixed(3)})`;
        ship.glyph.style.filter =
          `saturate(${(1 - 0.6 * d).toFixed(2)}) brightness(${(1 - 0.25 * d).toFixed(2)}) ` +
          `drop-shadow(0 0 ${(6 * d).toFixed(1)}px rgba(63,140,168,0.55))`;
        // Falling or rising, the surface they left is still up there.
        if (d < 1) {
          ship.shadow.setLngLat(diveBase(ch));
          ship.shadowEl.style.display = "";
          ship.shadowEl.style.opacity = ((1 - d) * 0.4).toFixed(3);
          ship.shadowEl.style.transform = `scale(${(1 - d * 0.5).toFixed(3)})`;
        } else {
          ship.shadowEl.style.display = "none";
        }
      }
    } else {
      ship.marker.getElement().style.display = "none";
      ship.shadowEl.style.display = "none";
    }
  }

  // THE KNOCK-UP STREAM + the island's shadow on the sea. Column opacity is
  // its own story beat (erupts 235-237, stands while aloft, fades to a
  // trace); the shadow gates on Skypiea's debut like any coastline.
  const co = columnOpacity(ch);
  m.setPaintProperty("sky-column", "fill-opacity", [
    "match", ["get", "kind"],
    "sky-column-1", 0.3 * co, "sky-column-2", 0.5 * co, "sky-column-3", 0.75 * co, 0,
  ]);
  m.setPaintProperty("sky-jet", "line-opacity", 0.7 * co);
  m.setPaintProperty("sky-shadow", "fill-opacity", [
    "interpolate", ["linear"], ["zoom"],
    2.0, 0,
    3.2, ["case", revealed(ch), ["match", ["get", "kind"], "sky-shadow-core", 0.3, 0.12], 0],
  ]);

  // The Blender Knock-Up Stream. Added only when its gate is open and removed
  // the moment it closes — WORKFLOW's rules, verbatim: "Models unload when
  // hidden; they are never fetched before their chapter gate." An image source
  // fetches its URL the instant it is added, so "add on demand" IS the gate;
  // an always-present source with opacity 0 would have fetched at chapter 1.
  if (RUNTIME_3D_ON) {
    const on = columnOpacity(ch) > 0;
    const present = !!m.getSource("knockup3d");
    if (on && !present) {
      m.addSource("knockup3d", { type: "image", url: KNOCK_UP_RASTER, coordinates: KNOCK_UP_CORNERS });
      m.addLayer(
        { id: "knockup3d", type: "raster", source: "knockup3d",
          paint: { "raster-opacity": 0, "raster-fade-duration": 0 } },
        "voyage-glow", // under the route: the ship rides UP it, not behind it
      );
    } else if (!on && present) {
      if (m.getLayer("knockup3d")) m.removeLayer("knockup3d");
      m.removeSource("knockup3d");
    }
    if (m.getLayer("knockup3d")) {
      // Their runtime_rule: "opacity follows columnOpacity(ch)". The vector
      // column stays underneath and fades out as the render fades in, so the
      // stream is one object at every zoom rather than two competing ones.
      // Past GLB_MIN_ZOOM the raster hands over to the model by the same logic,
      // one rung further in — but ONLY once the model can actually draw.
      m.setPaintProperty("knockup3d", "raster-opacity", rasterOpacity(ch));
    }
    syncKnockUpGlb(m, ch);
  }
  if (RUNTIME_ASSETS_ON) syncModels(m, ch);
  syncSims(m, ch);

  // THE DIVE SCAR, the same idea upside down. shimmerOpacity is its story beat
  // (the sea closes at 602-605, stands as a scar while the crew is under, fades
  // to a trace once they surface). No revealed() gate and no zoom fade, and both
  // are deliberate: the scar is drawn at DIVE_BASE, off Sabaody — an island the
  // reader is standing on when it happens — so it is not Fish-Man Island's
  // geometry leaking, it is the water they just went through.
  const so = shimmerOpacity(ch);
  m.setPaintProperty("dive-shimmer", "fill-opacity", [
    "match", ["get", "kind"], "shimmer-core", 0.85 * so, "shimmer-soft", 0.5 * so, 0,
  ]);

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

  // 10B: landmasses chart in with their pins. Zoom decides how much land you
  // see (a whisper at orbit, solid on approach); the chapter decides WHETHER —
  // an unread island has no coastline at any zoom.
  m.setPaintProperty("island-shapes", "fill-opacity", [
    "interpolate", ["linear"], ["zoom"],
    1.4, 0,
    2.6, ["case", revealed(ch), 0.45, 0],
    5.5, ["case", revealed(ch), 0.68, 0],
  ]);
  m.setPaintProperty("island-shapes-coast", "line-opacity", [
    "interpolate", ["linear"], ["zoom"],
    1.6, 0,
    2.8, ["case", revealed(ch), 0.55, 0],
    5.5, ["case", revealed(ch), 0.85, 0],
  ]);

  // LANDFALL. Hero terrain crossfades in on the dive — invisible until the
  // approach, solid at the deck. Chapter gates WHETHER, exactly like the
  // coastline above: a fogged hero island never shows a single ember.
  m.setPaintProperty("terrain-fill", "fill-opacity", [
    "interpolate", ["linear"], ["zoom"],
    3.6, 0,
    4.8, ["case", revealed(ch), 0.55, 0],
    6.8, ["case", revealed(ch), 0.9, 0],
  ]);
  m.setPaintProperty("terrain-line", "line-opacity", [
    "interpolate", ["linear"], ["zoom"],
    3.8, 0,
    5.0, ["case", revealed(ch), 0.6, 0],
    6.8, ["case", revealed(ch), 0.95, 0],
  ]);
  m.setPaintProperty("terrain-glow", "line-opacity", [
    "interpolate", ["linear"], ["zoom"],
    3.6, 0,
    4.8, ["case", revealed(ch), 0.25, 0],
    6.8, ["case", revealed(ch), 0.5, 0],
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
        // Isolate filter: style-only class toggle, per-frame like setLngLat —
        // deliberately NOT part of paintKey (no DOM content changes).
        h.parts.el.classList.toggle(
          "gliDim",
          !!pools.focus && !matchesFocus(pools.focus, { slug: crew.slug, crewSlug: crew.slug, fruit: null, haki: [] }, ch),
        );
        // The flag stays a crew landmark under every lens, so its key is the
        // window alone — lens flips never touch this DOM.
        if (h.shown && h.paintKey === String(placed.w.order)) continue; // DOM unchanged
        if (!h.populated) {
          // Real Jolly Roger where we have one; original SVG mark otherwise.
          const flagArt = art?.flags[crew.slug];
          h.parts.flag.innerHTML = flagArt ? artImg(flagArt, 44) : jollyRogerSvg(crew.slug, { size: 26 });
          // The crew's real ship rides under the flag; fall back to the ink hull cue.
          const shipArt = crew.vessel ? art?.ships[crew.vessel.slug] : undefined;
          h.parts.hull.innerHTML = shipArt
            ? artImg(shipArt, 38)
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
          mh.parts.el.classList.toggle(
            "gliDim",
            !!pools.focus && !matchesFocus(pools.focus, { slug: mem.slug, crewSlug: crew.slug, fruit: mem.fruit, haki: mem.haki }, ch),
          );
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
        h.parts.el.classList.toggle(
          "gliDim",
          !!pools.focus && !matchesFocus(pools.focus, { slug: c.slug, crewSlug: c.crewSlug, fruit: c.fruit, haki: c.haki }, ch),
        );
        // The ring follows the lens: its key carries the color, so a mid-scrub
        // reveal recolors the ring the frame it happens. Content (portrait or
        // monogram) populates once; colors re-apply on every key change.
        const color = lensColor(pools.lens, { crewSlug: c.crewSlug, affiliation: c.affiliation, fruit: c.fruit, haki: c.haki, kind: "warlord" }, ch);
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
        presenceOrbs(world, ch, layout, pools.lens, pools.focus),
      );
    }
  }

  /* -------------------------------------------------------------- territory */
  // Who holds the sea, as of this chapter. A disc at each Emperor crew's
  // active anchorage, in their own ink. Both halves of statusHoldersAt matter
  // here: Whitebeard's water goes back to being nobody's when he dies, and the
  // Straw Hats' does not exist until 1053.
  {
    const holders = statusHoldersAt(world, "yonko", Math.floor(ch));
    const features: GeoJSON.Feature[] = [];
    for (const crew of world.presence.crews) {
      if (!holders.has(crew.slug)) continue;
      const w = presenceWindowAt(crew.windows, ch);
      if (!w) continue;
      // a 48-gon rather than a circle-layer: a real polygon follows the globe's
      // curvature, and these are big enough (9 degrees) for that to show
      const ring: [number, number][] = [];
      for (let i = 0; i <= 48; i++) {
        const th = (i / 48) * Math.PI * 2;
        ring.push([w.lng + Math.cos(th) * 9, w.lat + Math.sin(th) * 9 * 0.72]);
      }
      features.push({
        type: "Feature",
        properties: { slug: crew.slug, color: crewColor(crew.slug) },
        geometry: { type: "Polygon", coordinates: [ring] },
      });
    }
    (m.getSource("territory") as GeoJSONSource | undefined)?.setData({
      type: "FeatureCollection", features,
    });
  }

  /* ---------------------------------------------------------------- Baratie */
  // Two beats, no window table needed for one mark: it appears when the reader
  // reaches it, and it stays. It never sinks and nobody blows it up — it just
  // stops being where the story is, so it dims to a landmark rather than
  // vanishing. (The Grand Line has no monopoly on places that matter.)
  if (pools?.baratie) {
    if (ch >= BARATIE_CHAPTER) {
      pools.baratie.el.style.display = "";
      pools.baratie.wrap.style.opacity = ch > 68 ? "0.5" : "1";
    } else {
      pools.baratie.el.style.display = "none";
    }
  }

  /* ------------------------------------------------------------------- Wano */
  // Same two-beat shape as the Baratie: arrives (ch 909, the one VERIFIED
  // beat), stands. The climb animation waits for human-verified chapters —
  // the sprite renderer withholds rather than invents (wano.ts header).
  if (pools?.wano) {
    const o = wanoOpacity(ch);
    if (o > 0) {
      pools.wano.el.style.display = "";
      pools.wano.img.style.opacity = String(o);
    } else {
      pools.wano.el.style.display = "none";
      pools.wano.img.style.opacity = "0";
    }
  }

  /* ------------------------------------------------------------- poneglyphs */
  // Outside the lens gate on purpose: the stones are not presence. Turning the
  // presence layer off is "stop showing me people", and the reader who does that
  // is exactly the one reading the map for its secrets.
  {
    const features: GeoJSON.Feature[] = [];
    const dimStone = pools?.focus ? pools.focus.focus.kind !== "poneglyph" : false;
    for (const pg of world.poneglyphs) {
      const h = pools?.poneglyphs.get(pg.slug);
      // revealedChapter AND an active custody window. Two gates, because they
      // answer different questions: has the reader been told this stone exists,
      // and is it anywhere right now.
      const w = pg.revealedChapter <= ch ? presenceWindowAt(pg.custody, ch) : null;
      if (!w) {
        if (h) hidePresence(h);
        continue;
      }
      features.push({
        type: "Feature",
        properties: {
          slug: pg.slug,
          name: pg.name,
          kind: pg.kind,
          note: pg.note ?? "",
          label: w.label,
          confidence: w.confidence,
          verified: w.verified,
        },
        geometry: { type: "Point", coordinates: [w.lng, w.lat] },
      });
      if (!h) continue;
      h.marker.setLngLat([w.lng, w.lat]);
      // Focused on the stones: they hold their ink and everything else dims (the
      // presence pools handle their own side). Focused on anything else: the
      // stones dim like any other bystander.
      h.parts.el.classList.toggle("gliDim", dimStone);
      const key = `${w.order}|${pg.kind}`;
      if (h.shown && h.paintKey === key) continue;
      if (!h.populated) {
        // Only the Road stones are labelled, and only "road": the four of them
        // are a set the reader is actively counting, and the word is short
        // enough to sit under a mark. "INSTRUCTIONAL" and "HISTORICAL" set in
        // the same place are longer than the island they stand on and turn the
        // sea into a glossary. Those stones are identified by their SHAPE, and
        // named in the tooltip — where the reader has to ask.
        h.parts.label.textContent = pg.kind === "road" ? "road" : "";
        h.populated = true;
      }
      h.parts.el.style.display = "";
      h.shown = true;
      h.paintKey = key;
    }
    (m.getSource("poneglyphs") as GeoJSONSource | undefined)?.setData({
      type: "FeatureCollection",
      features,
    });
  }
}
