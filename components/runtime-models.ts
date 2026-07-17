/**
 * components/runtime-models.ts — one table, every Blender model.
 *
 * The asset track's integration rule #1 is "do not create one loader per island",
 * and it is right for a reason that shows up immediately: there were two
 * hand-written sync functions for two models, and eleven more would have been
 * eleven more copies of the same twenty lines with different constants. This is
 * that table. Adding the twelfth island is a data change.
 *
 * Pure: no React, no MapLibre, no DOM. It turns the sync artifact into placement
 * facts and gate predicates; WorldMap owns the map and glb-layer owns the GPU.
 *
 * ── THE SCALE IS A LOOK, AND IT SAYS SO ────────────────────────────────────
 *
 * 13 of 16 models declare `scale_policy: {mode: "visual_fit_not_canon_scale",
 * use_model_bounds: true}`. That is the asset track telling us there is NO canon
 * metres-per-unit to be found and to fit the bounds to something we choose. The
 * three models WITHOUT that policy are exactly the three that carry enough
 * information to be measured, which is why they got bespoke derivations:
 *
 *   fish-man-island          its coastline_contract seeds OUR generator
 *                            ("silhouette:fish-man-island", radius, elong,
 *                            points:128) and ships the geojson; the GLB's bounds
 *                            equal that bbox to four decimals. 1 unit = 1 degree.
 *                            MEASURED.
 *   skypiea-knock-up-stream  a "vertical-transition-sprite" with "no geographic
 *                            coastline clipping" and no scale at all — so its
 *                            metres-per-unit is DERIVED from its two anchors.
 *   wano-waterfall-ascent    same track; not wired (see WANO in WorldMap).
 *
 * For everything else we fit, and the thing we fit to is the island the atlas
 * ALREADY DRAWS: 11 of 13 anchors land on a canon island's coordinate exactly
 * (to 1e-4), so each model is scaled to cover its own silhouette. The 3D model
 * replaces the 2D shape at the 2D shape's size. That is honest — it is a look
 * chosen by the app, derived from the app's own deterministic geometry — and it
 * is labelled `visual_fit` everywhere it surfaces, because a reader deserves to
 * know which numbers on this map are measurements and which are art direction.
 *
 * NOT the image-source `coordinates`: those frame a RENDER, margins and glow
 * included. WorldMap rejects them twice already, with the arithmetic.
 * NOT the anchor as a scale hint: 13 models carry `anchor_usage:
 * "atlas_anchor_only"` and `anchor_warning: "never use it as evidence of relative
 * canon topology"`. It places. It does not measure.
 */

export type RuntimeAsset = {
  id: string;
  label: string | null;
  glb: string;
  anchor: [number, number] | null;
  chapter_beats: Record<string, unknown>;
  component_gates: { id: string; role?: string; reveal_chapter: number | null; verification?: string; default_hidden?: boolean }[];
  withheld_variants: string[];
  projection_support: string[] | null;
  scale_policy: { mode: string; use_model_bounds?: boolean } | null;
  bounds_blender: { min: [number, number, number]; max: [number, number, number] } | null;
  gate_unverified: boolean;
  feature_flag: string | null;
  route_policy: string | null;
  anchor_warning: string | null;
};

export type ScaleMode = "measured_degrees" | "derived_anchors" | "visual_fit";

export type RuntimeModel = {
  id: string;
  glb: string;
  lngLat: [number, number];
  /** Metres per model unit, fed to glb-layer. */
  metersPerUnit: number;
  scaleMode: ScaleMode;
  /**
   * The archipelago spread multiplier applied to the visual_fit footprint. 1 for
   * a single place, >1 for a many-island system (Totto Land). Recorded so the
   * contact sheet and inspector can say "visual_fit x3.5" rather than pretend the
   * scale was untouched.
   */
  spread: number;
  /** The whole-model chapter gate. See gateChapter(). */
  reveal: number;
  /** True when some component needs hiding that the model gate cannot express. */
  perNode: boolean;
  projections: ("globe" | "mercator")[];
  /**
   * The node predicate, or undefined when a whole-model gate says everything.
   * Built HERE, where the asset is in scope. It was briefly built at the call
   * site from a RuntimeModel cast to a RuntimeAsset — which type-checks, produces
   * a predicate with no gates and no withheld list, and therefore shows
   * everything. A leak that compiles.
   */
  nodeVisible?: (extras: Record<string, unknown>, name: string) => boolean;
  /**
   * Decorative backdrop nodes to hide at load. Only set for spread archipelagos,
   * whose flat "ocean stage" plate otherwise buries the islands on a map that is
   * already sea. Not a spoiler gate — permanent, load-time. See glb-layer.
   */
  hideNode?: (nodeName: string) => boolean;
  /** Why this model is not wired, or null if it is. */
  skipped: string | null;
};

/**
 * The decorative sea/stage plate an archipelago blockout sits on. Matched on the
 * GLTF-exported node name (spaces -> underscores). Deliberately narrow: "* ocean
 * stage", "* sea stage", "cloud shadow" — the pure backdrops. NOT "* backdrop" or
 * "* stage" broadly, because an event scene (Loguetown's "Execution backdrop")
 * carries a backdrop that is the scene, not a throwaway, and this is only ever
 * applied to spread archipelagos anyway.
 */
const BACKDROP_PLATE = /(?:ocean|sea)_stage|cloud_shadow/i;

/** 1 degree of latitude, in metres. The map's own convention. */
export const M_PER_DEG = 111_195;

/** Ids whose scale is measured or derived rather than fitted. */
const BESPOKE: Record<string, { metersPerUnit: number; mode: ScaleMode }> = {
  // Measured: GLB bounds == the shipped coastline bbox, to four decimals.
  "fish-man-island": { metersPerUnit: M_PER_DEG, mode: "measured_degrees" },
  // Derived: source_anchor -> destination_anchor over the model's own Y span.
  // Kept in WorldMap beside the ascent it belongs to; named here so the table
  // knows not to fit it.
  "skypiea-knock-up-stream": { metersPerUnit: NaN, mode: "derived_anchors" },
};

/**
 * THE WHOLE-MODEL CHAPTER GATE.
 *
 * `safe_full_scene`, not `base_reveal`, and the difference is the spoiler. The
 * asset track's own words: "Use `safe_full_scene_chapter` for the complete PNG
 * fallback. It is intentionally later than the base scene gate when the fallback
 * contains later landmarks." The same is true of the model: Arlong Park's base is
 * 69 but its full scene is safe only at 70, and the Tarai system's base is 522
 * while its full scene waits until 525.
 *
 * The cost is revealing late — 1 chapter for Arlong Park, 56 for Dressrosa. Per-
 * node gating buys those chapters back, and where a model has it we gate at
 * `base_reveal` and let the nodes hold the line. Late is a blemish. Early is a
 * spoiler, and this atlas has exactly one promise.
 */
export function gateChapter(a: RuntimeAsset, perNode: boolean): number | null {
  const b = a.chapter_beats as { base_reveal?: number; safe_full_scene?: number };
  if (perNode && typeof b.base_reveal === "number") return b.base_reveal;
  const ch = b.safe_full_scene ?? b.base_reveal;
  return typeof ch === "number" ? ch : null;
}

/** Does this model carry geometry the whole-model gate cannot speak for? */
export function needsPerNode(a: RuntimeAsset): boolean {
  const b = a.chapter_beats as { base_reveal?: number };
  return a.component_gates.some(
    (g) =>
      g.default_hidden === true ||
      g.verification === "chapter_to_verify" ||
      g.reveal_chapter === null ||
      (typeof g.reveal_chapter === "number" && g.reveal_chapter !== b.base_reveal),
  );
}

/**
 * A node's own verdict, read from its glTF extras.
 *
 * DEFAULTS TO HIDDEN, and every branch here is the safe one. A node we cannot
 * identify, a component we have no gate for, a reveal chapter nobody has
 * verified — all of them draw nothing. The failure mode of being too shy is a
 * missing rock; the failure mode of being too generous is Mary Geoise's lower
 * ports 800 chapters early.
 *
 * The manifest and the extras are OR'd, never trusted individually. Mary Geoise's
 * manifest says `default_hidden: true` for three components while all 20 of its
 * nodes say `default_hidden: false` — the two sources contradict each other, and
 * only a reader who believes both can be safe. sync_runtime_assets reports the
 * contradiction; this honours it.
 */
export function makeNodeVisible(a: RuntimeAsset, getChapter: () => number) {
  const gates = new Map(a.component_gates.map((g) => [g.id, g]));
  const withheld = new Set(a.withheld_variants);
  return (extras: Record<string, unknown>, _name: string): boolean => {
    const cid = extras.component_id as string | undefined;
    // Untagged geometry rides the model's own gate — the layer is only added
    // once that is open, so this is "part of the base scene", not "ungated".
    if (!cid) return true;
    if (withheld.has(cid)) return false;
    if (extras.default_hidden === true) return false;
    if (extras.gate_confidence === "chapter_to_verify") return false;

    const g = gates.get(cid);
    if (g && (g.default_hidden === true || g.verification === "chapter_to_verify")) return false;

    // A reveal chapter from either source; null/absent in BOTH means nobody has
    // verified it, and an unverified gate is not a gate.
    const rc = (extras.reveal_chapter as number | undefined) ?? g?.reveal_chapter ?? null;
    if (rc === null || rc === undefined) return false;
    return getChapter() >= rc;
  };
}

/**
 * How many of a model's components are their own ISLANDS, not parts of one.
 *
 * This is the difference between Totto Land and Arlong Park, and the `role` field
 * states it outright. Totto Land's 36 components are 1 `central_main_island` + 1
 * `nested_landmark` + 34 `subsidiary_island` — thirty-five real islands. Arlong
 * Park's 4 are `island_group` + `village` + `fortified_headquarters` +
 * `narrative_landmark` — one island's parts. So counting island-role components
 * separates the archipelago (fit to a region) from the single place (fit to one
 * silhouette), from the data, without a hand-maintained list of which is which.
 */
export function islandComponentCount(a: RuntimeAsset): number {
  return a.component_gates.filter(
    (g) => /island|kingdom|archipelago/i.test(g.role ?? "") || g.id.endsWith("-island"),
  ).length;
}

/** Below this, a model is one place and fits one silhouette. At/above, it spreads. */
export const ARCHIPELAGO_MIN_ISLANDS = 5;
/**
 * The cap on how far an archipelago spreads. sqrt(N) is area-preserving — N
 * islands want N times a single island's area, so sqrt(N) times its width — but
 * for Totto Land's 35 that is ~5.9x, which swallows a hemisphere. 3.5 spreads the
 * ~22 rendering islands into a clear cluster (~12deg for Totto) that reads as an
 * archipelago at dive zoom without dominating the map. It is a LOOK, capped on
 * purpose; the whole scale is `visual_fit`, not canon. Eyeball it on the contact
 * sheet and move this number, not the geometry.
 */
export const ARCHIPELAGO_MAX_SPREAD = 3.5;

/** The spread multiplier for a model's fit footprint. 1 for a single place. */
export function archipelagoSpread(a: RuntimeAsset): number {
  const n = islandComponentCount(a);
  if (n < ARCHIPELAGO_MIN_ISLANDS) return 1;
  return Math.min(Math.sqrt(n), ARCHIPELAGO_MAX_SPREAD);
}

/**
 * Metres-per-unit for a fitted model: cover the island's own silhouette, times a
 * spread factor for archipelagos (see archipelagoSpread — Totto Land's 35 islands
 * must not share one island's footprint). `footprintDeg` is the silhouette's
 * larger horizontal span, in degrees.
 */
export function visualFit(a: RuntimeAsset, footprintDeg: number): number | null {
  const b = a.bounds_blender;
  if (!b) return null;
  const spanX = b.max[0] - b.min[0];
  const spanY = b.max[1] - b.min[1]; // Blender Y == glTF Z; both are ground-plane
  const span = Math.max(spanX, spanY);
  if (!(span > 0)) return null;
  return (footprintDeg * archipelagoSpread(a) * M_PER_DEG) / span;
}

/**
 * Build the table. `footprintFor` returns an island's silhouette span in degrees
 * for a given anchor, or null when the anchor is not an island the atlas draws.
 */
export function buildModels(
  assets: RuntimeAsset[],
  footprintFor: (lngLat: [number, number]) => number | null,
  globeProven: (id: string) => boolean,
  getChapter: () => number,
): RuntimeModel[] {
  const out: RuntimeModel[] = [];
  for (const a of assets) {
    const skip = (why: string): void => {
      out.push({
        id: a.id, glb: a.glb, lngLat: a.anchor ?? [0, 0], metersPerUnit: NaN,
        scaleMode: "visual_fit", spread: 1, reveal: Infinity, perNode: false,
        projections: [], skipped: why,
      });
    };
    if (!a.anchor) { skip("no anchor"); continue; }
    // The asset track's own words on Wano: "proposed; exact waterfall climb beats
    // need human verification". Asset-ready is not gate-known.
    if (a.gate_unverified) { skip("gate_unverified — its own manifest calls the beats proposed"); continue; }

    const perNode = needsPerNode(a);
    const reveal = gateChapter(a, perNode);
    if (reveal === null) { skip("no base_reveal or safe_full_scene — no chapter to gate on"); continue; }

    const bespoke = BESPOKE[a.id];
    let metersPerUnit: number;
    let scaleMode: ScaleMode;
    if (bespoke && Number.isFinite(bespoke.metersPerUnit)) {
      metersPerUnit = bespoke.metersPerUnit;
      scaleMode = bespoke.mode;
    } else if (bespoke) {
      skip("bespoke scale owned by its own module"); continue;
    } else {
      const foot = footprintFor(a.anchor);
      if (foot === null) { skip("visual_fit needs a silhouette and its anchor is not an island"); continue; }
      const fit = visualFit(a, foot);
      if (fit === null) { skip("no bounds_blender to fit"); continue; }
      metersPerUnit = fit;
      scaleMode = "visual_fit";
    }

    // `projection_support` is DATA and the manifest is the boundary. The override
    // is app-owned, named, and evidenced — see config/projection-overrides.ts.
    const declared = a.projection_support ?? [];
    const mercator = declared.length === 0 || declared.some((p) => p.startsWith("mercator"));
    const globe = declared.length === 0 || globeProven(a.id);
    const projections: ("globe" | "mercator")[] = [];
    if (globe) projections.push("globe");
    if (mercator) projections.push("mercator");
    if (!projections.length) { skip(`no supported projection (declared: ${declared.join(",") || "none"})`); continue; }

    const spread = scaleMode === "visual_fit" ? archipelagoSpread(a) : 1;
    out.push({
      id: a.id, glb: a.glb, lngLat: a.anchor, metersPerUnit, scaleMode,
      spread, reveal, perNode, projections,
      nodeVisible: perNode ? makeNodeVisible(a, getChapter) : undefined,
      // Only a spread archipelago drops its ocean-stage plate onto the map's sea.
      hideNode: spread > 1 ? (name: string) => BACKDROP_PLATE.test(name) : undefined,
      skipped: null,
    });
  }
  return out;
}
