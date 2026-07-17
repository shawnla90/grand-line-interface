/**
 * lib/scenes.ts — the narrative scene registry. DATA ONLY.
 *
 * It loads no asset, fetches nothing, and renders nothing. It answers one
 * question — "should this scene be visible, and if not, why not" — and that was
 * deliberately the whole of it: the Blender track's handoff said to build the
 * data model and stop before wiring a blockout, because none of the 11 had
 * reached `integration_ready`.
 *
 * ALL 11 HAVE NOW. Codex's a7de84d flipped every queue state to
 * `integration_ready` and every blockout to `runtime_export: true`, so this file
 * answers "visible: true, no reasons" for all of them at ch1185 — and still
 * nothing renders a narrative scene, because the reader-facing surface was never
 * built (see config/flags.ts). The registry is ready and unwired. That is a fine
 * place to be, and a dangerous one to be quiet about: the first component that
 * imports sceneVisibilityAt and believes it puts eleven scenes on the map.
 *
 * The Blender MODELS that do render are a different system — the runtime-3D track,
 * components/runtime-models.ts + components/glb-layer.ts. Do not confuse the two:
 * these 11 v2 contracts describe scenes; those 16 GLBs are assets.
 *
 * ============================================================================
 * MIRROR THE CONTRACT. INVENT NOTHING.
 * ============================================================================
 * Every field name here exists in blender-assets/contracts/*.visual.json. The
 * ones that DON'T exist and must never be invented: `integration_ready` on a
 * scene (it is a QUEUE state, joined in sync_scenes.py), `moving_anchor`
 * (derived from entity_type), `derived_schematic` in data (an instruction to
 * us — see routeGeometryPolicy), `grove_count` (Sabaody's 79 groves are ONE
 * component; the number lives only in prose), `parts`, `layers`, `subregions`,
 * `landmarks`, `status` (the index says `state`), `station_type`.
 *
 * TOLERANT WHERE THE SCHEMA IS. The contract's JSON Schema has no
 * additionalProperties:false, and every real file carries `priority`, `topology`
 * and `api_coverage`, which its `properties` never mentions. So: looseObject.
 * `role` (73 distinct values) and `relationships[].type` (35) are free-form
 * strings — enumerating them would be inventing a taxonomy the asset track did
 * not agree to.
 *
 * EDGES RESOLVE LENIENTLY. An endpoint is NOT guaranteed to be a component id:
 * `made_of -> "island_cloud"` is a MATERIAL, and `disrupts ->
 * "water-7-sea-train-network"` is the contract's own id. Resolution returns
 * nulls rather than throwing, because the graph is a description, not a foreign
 * key constraint.
 */

import { z } from "zod";

/* -------------------------------------------------------------------------- */
/* the contract, mirrored                                                     */
/* -------------------------------------------------------------------------- */

export const SceneEntityType = z.enum([
  "nested_landmark_compound", "kingdom_region_system", "island_town_system",
  "island_bridge_system", "moving_world_entity", "mountain_city_system",
  "vertical_political_world_structure", "mangrove_grove_network",
  "sky_archipelago_system", "city_landmark_event_system", "sea_train_route_network",
]);
export type SceneEntityType = z.infer<typeof SceneEntityType>;

export const Verification = z.enum(["verified", "chapter_to_verify"]);
export type Verification = z.infer<typeof Verification>;

const AtlasAnchor = z.looseObject({
  lng: z.number(),
  lat: z.number(),
  confidence: z.string(),
  source_ref: z.string(),
  /** Always "scene_entry_anchor_only" — a camera position, never a claim. */
  usage: z.string(),
  warning: z.string(),
});

export const SceneComponent = z.looseObject({
  id: z.string(),
  name: z.string(),
  /** Free-form: 73 distinct values across the corpus. Do NOT enum. */
  role: z.string().optional(),
  debut_chapter: z.number().int().nullable().optional(),
  canon_status: z.string().optional(),
  canon_confidence: z.string().optional(),
  source_ref: z.string().optional(),
  record_origin: z.enum(["generated_wiki_record", "cited_manual_topology_node"]).optional(),
  atlas_anchor: AtlasAnchor.nullable().optional(),
});
export type SceneComponent = z.infer<typeof SceneComponent>;

export const SceneRelationship = z.looseObject({
  from: z.string(),
  /** Free-form: 35 distinct values. Do NOT enum. */
  type: z.string(),
  to: z.string(),
  confidence: z.enum(["canon", "cited_summary", "unresolved"]).optional(),
});
export type SceneRelationship = z.infer<typeof SceneRelationship>;

export const SceneVariant = z.looseObject({
  id: z.string(),
  reveal_chapter: z.number().int().nullable(),
  /** Prose. The asset track describes states in sentences, not enums. */
  state: z.string(),
  verification: Verification.optional(),
});
export type SceneVariant = z.infer<typeof SceneVariant>;

export const SceneEvent = z.looseObject({
  id: z.string(),
  importance: z.number().int().min(1).max(3),
  reveal_chapter: z.number().int().nullable(),
  /** A component id. */
  landmark: z.string(),
  state_delta: z.string(),
  verification: Verification.optional(),
  camera_cue: z.string().optional(),
  fx: z.array(z.string()).optional(),
});
export type SceneEvent = z.infer<typeof SceneEvent>;

export const NarrativeScene = z.looseObject({
  id: z.string().regex(/^[a-z0-9-]+$/),
  label: z.string(),
  entity_type: SceneEntityType,
  contract_status: z.string(),
  priority: z.number().int().nullable().optional(),
  /** The index's key is `state`, never `status`. */
  index_state: z.string(),
  identity: z.looseObject({
    anchor: z.looseObject({}),
    components: z.array(SceneComponent),
  }),
  relationships: z.array(SceneRelationship),
  chapter_logic: z.looseObject({
    base_reveal_chapter: z.number().int().nullable(),
    temporal_variants: z.array(SceneVariant),
    event_scenes: z.array(SceneEvent),
    default_rule: z.string().optional(),
    unknown_gate_rule: z.string().optional(),
  }),
  route_network: z.looseObject({}).nullable().optional(),
  topology: z.looseObject({}).nullable().optional(),
  unresolved: z.array(z.string()).default([]),
  visual_program: z.looseObject({}),
  evidence: z.array(z.looseObject({ path: z.string(), sha256: z.string(), ownership: z.string() })),
  /** Joined from queue/asset-requests.json — never a field on a contract. */
  queue: z.looseObject({
    state: z.string().nullable(),
    kind: z.string().nullable().optional(),
    next: z.string().nullable().optional(),
    replaced_as_integration_unit_by: z.string().nullable().optional(),
  }),
  blockout: z.looseObject({
    exists: z.boolean(),
    runtime_export: z.boolean(),
    maturity: z.string().nullable().optional(),
  }),
  source_ref: z.string(),
});
export type NarrativeScene = z.infer<typeof NarrativeScene>;

export const NarrativeScenes = z.looseObject({
  _meta: z.looseObject({ warnings: z.array(z.string()).default([]) }),
  scenes: z.array(NarrativeScene),
});
export type NarrativeScenes = z.infer<typeof NarrativeScenes>;

/* -------------------------------------------------------------------------- */
/* visibility                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * Why a scene is not on screen.
 *
 * These five are not invented — the asset track already wrote them, in
 * manifests/runtime-3d.json: `enable_glb_when: "feature flag on, close zoom,
 * supported projection, chapter gate open"`. close zoom -> distance_lod,
 * supported projection -> projection_unsupported, chapter gate -> chapter_locked;
 * plus asset_not_ready (the queue) and gate_unverified (an unconfirmed beat).
 * So one model answers for both asset classes.
 */
export type SceneHiddenReason =
  | "chapter_locked"
  | "gate_unverified"
  | "asset_not_ready"
  /** APP-DEFINED. No contract field; from WORKFLOW's runtime policy. */
  | "projection_unsupported"
  /** APP-DEFINED. Same. */
  | "distance_lod";

export type SceneContext = {
  chapter: number;
  projection?: "globe" | "mercator";
  distanceLod?: "near" | "far";
};

export type SceneVisibility = {
  visible: boolean;
  reasons: SceneHiddenReason[];
  /** The latest verified state at or before this chapter. */
  state: SceneVariant | null;
  events: SceneEvent[];
  suppressed: {
    variants: { id: string; reason: SceneHiddenReason }[];
    events: { id: string; reason: SceneHiddenReason }[];
  };
  /** DERIVED from entity_type — there is no moving_anchor field to read. */
  movingAnchor: boolean;
};

export function sceneVisibilityAt(scene: NarrativeScene, ctx: SceneContext): SceneVisibility {
  const reasons: SceneHiddenReason[] = [];
  const cl = scene.chapter_logic;
  const base = cl.base_reveal_chapter;

  // The SCENE's own gate. Note it is not necessarily <= its earliest variant:
  // water-7-sea-train-network has base 323 and a variant at 322. base gates the
  // place, variants gate its state; the later of the two wins, which is the safe
  // direction. Do NOT "fix" this by taking the min.
  if (base !== null && base > ctx.chapter) reasons.push("chapter_locked");

  const suppressedVariants: { id: string; reason: SceneHiddenReason }[] = [];
  const candidates: SceneVariant[] = [];
  for (const v of cl.temporal_variants) {
    // The unknown_gate_rule, verbatim from every contract: "Do not render a
    // chapter_to_verify state until its exact gate is confirmed."
    if (v.verification === "chapter_to_verify" || v.reveal_chapter === null) {
      suppressedVariants.push({ id: v.id, reason: "gate_unverified" });
      continue;
    }
    if (v.reveal_chapter > ctx.chapter) {
      suppressedVariants.push({ id: v.id, reason: "chapter_locked" });
      continue;
    }
    candidates.push(v);
  }

  // "Render the latest verified state whose reveal chapter is <= the reader
  // chapter" — the default_rule, also verbatim. It is AMBIGUOUS by chapter
  // alone: three scenes have two verified variants at the same chapter
  // (skypiea 239/239, zou 795/795, loguetown 1/1). Array order is the tiebreak,
  // so `>=` here resolves a tie to the LAST authored variant — the asset track
  // wrote them in order and the later one is the more specific state.
  let state: SceneVariant | null = null;
  for (const v of candidates) {
    if (state === null || (v.reveal_chapter as number) >= (state.reveal_chapter as number)) {
      state = v;
    }
  }
  if (state === null && !reasons.includes("chapter_locked")) reasons.push("gate_unverified");

  const suppressedEvents: { id: string; reason: SceneHiddenReason }[] = [];
  const events: SceneEvent[] = [];
  for (const e of cl.event_scenes) {
    if (e.verification === "chapter_to_verify" || e.reveal_chapter === null) {
      suppressedEvents.push({ id: e.id, reason: "gate_unverified" });
    } else if (e.reveal_chapter > ctx.chapter) {
      suppressedEvents.push({ id: e.id, reason: "chapter_locked" });
    } else {
      events.push(e);
    }
  }

  // THE ASSET GATE. Two independent locks: the queue's own workflow state and
  // the blockout manifest's runtime_export.
  //
  // This comment used to end "which the asset track's verifier HARD-ASSERTS to
  // false. Today this fires for all 11, always, which is the correct answer and
  // not a bug." Codex's a7de84d opened both locks at once, so `asset_not_ready`
  // is now UNREACHABLE — every scene is integration_ready and exports, and all 11
  // resolve visible:true at ch1185 with no reasons at all. The branch stays
  // because the locks can shut again (a withdrawn asset, a half-open gate that
  // check_scenes::both_locks_agree now watches for), but nothing produces it
  // today. If you are debugging why a scene is visible, it is not this.
  if (scene.queue.state !== "integration_ready" || !scene.blockout.runtime_export) {
    reasons.push("asset_not_ready");
  }

  // App-defined, from WORKFLOW's runtime policy: "Globe/orbit/lower-end devices
  // use the transparent PNG fallback."
  if (ctx.projection === "globe") reasons.push("projection_unsupported");
  if (ctx.distanceLod === "far") reasons.push("distance_lod");

  return {
    visible: reasons.length === 0,
    reasons,
    state,
    events,
    suppressed: { variants: suppressedVariants, events: suppressedEvents },
    movingAnchor: scene.entity_type === "moving_world_entity",
  };
}

/* -------------------------------------------------------------------------- */
/* the graph                                                                  */
/* -------------------------------------------------------------------------- */

export type ResolvedEdge = {
  from: SceneComponent | null;
  to: SceneComponent | null;
  raw: SceneRelationship;
};

/**
 * The hierarchy (place -> subregion -> landmark) is NOT nested in the data — it
 * is a flat component table plus typed edges, and this reads it that way.
 * Unresolved endpoints are normal: `made_of -> "island_cloud"` names a material,
 * `disrupts -> "water-7-sea-train-network"` names the contract itself.
 */
export function resolveEdges(scene: NarrativeScene): ResolvedEdge[] {
  const byId = new Map(scene.identity.components.map((c) => [c.id, c]));
  return scene.relationships.map((r) => ({
    from: byId.get(r.from) ?? null,
    to: byId.get(r.to) ?? null,
    raw: r,
  }));
}

export type RouteGeometryPolicy = {
  derivedSchematic: true;
  label: "derived_schematic";
  /** The contract's own words, verbatim. Rule 4 applies here too. */
  note: string;
};

/**
 * `derived_schematic` DOES NOT EXIST IN ANY CONTRACT. It is an instruction to
 * this app (CLAUDE_CODE_NARRATIVE_SYSTEMS.md): any temporary globe line we
 * synthesise for a route must be labelled derived_schematic in data AND in UI,
 * and its branch bearings must never be presented as canon.
 *
 * So the label is produced HERE, at the point of use, and it carries the
 * contract's own sentence with it — "curved local great-circle approximations
 * are integration scaffolds, not canon cartography". No line is drawn yet; the
 * rule exists before the temptation does.
 */
export function routeGeometryPolicy(scene: NarrativeScene): RouteGeometryPolicy | null {
  const rn = scene.route_network as { edge_geometry?: string } | null | undefined;
  if (!rn) return null;
  return {
    derivedSchematic: true,
    label: "derived_schematic",
    note: rn.edge_geometry ?? "Synthesised geometry. Not canon cartography.",
  };
}
