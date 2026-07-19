/**
 * lib/simulation.ts — the deterministic evaluator for signed 2.5D story packs,
 * and the only sanctioned way to read data/generated story simulations.
 *
 * Pure module: no React, no three.js, no map, no chapter logic. It takes a
 * scene and a local time in milliseconds and answers "where is every actor,
 * in what pose, at what opacity, and which FX have fired". Every gate lives in
 * the caller (sim-models), same boundary glb-layer.ts draws: an evaluator that
 * knows about chapters is an evaluator you cannot reuse for the next saga.
 *
 * THE CONTRACT IS THE ASSET TRACK'S, VERBATIM (blender-assets/handoffs/
 * CLAUDE_CODE_EAST_BLUE_2D.md "Deterministic evaluation"):
 *   - pose is STEP-selected: the last keyframe whose t <= localTime. Poses are
 *     atlas cells; blending two illustrations is how you get nightmare fuel.
 *   - numeric fields (x, y, scale, rotation, opacity) interpolate linearly to
 *     the next keyframe, with the authored ease applied to the segment.
 *   - an FX event fires ONCE when local time crosses its t going forward, and
 *     the fired set is rebuilt from zero whenever time moves backward. Backward
 *     scrub is the direction that leaks state if you only ever accumulate.
 *
 * Determinism is the whole point: evaluate(scene, 3400) is the same answer on
 * every machine, every run, every scrub direction. Nothing in here reads a
 * clock, and nothing in here mutates a scene.
 */

import { z } from "zod";

/* ── schema ──────────────────────────────────────────────────────────────────
 * Validates the sync artifact at import time, same posture as lib/schema.ts
 * for canon.json: an artifact that does not parse must not become pixels.
 * The zod shapes mirror what scripts/sync_east_blue_2d.py already enforced
 * against the signed manifest — this is the TypeScript side of the same wall.
 */

export const SimEase = z.enum(["linear", "smooth", "accelerate", "decelerate"]);

export const SimKeyframe = z.object({
  t: z.number().int().nonnegative(),
  x: z.number(),
  y: z.number(),
  scale: z.number().positive(),
  rotation: z.number(),
  opacity: z.number().min(0).max(1),
  pose: z.string().min(1),
  ease: SimEase.optional(),
});

export const SimActor = z.object({
  id: z.string().min(1),
  asset_id: z.string().min(1),
  z: z.number(),
  keyframes: z.array(SimKeyframe).nonempty(),
});

export const SimFxEvent = z.object({
  t: z.number().int().nonnegative(),
  type: z.string().min(1),
  duration_ms: z.number().int().positive(),
  intensity: z.number().min(0).max(1),
});

export const SimChapterGate = z.object({
  start: z.number().int().min(1),
  end: z.number().int().min(1),
  verification: z.literal("verified"),
  source_url: z.string().min(1),
});

/** Resolved at sync time from canon/east_blue_scene_anchors.json + canon.json —
 * the scene's map position, sharing the event/island's own coordinate so the
 * simulation and the /event page can never point at two different seas. */
export const SimAnchor = z.object({
  kind: z.enum(["event", "island", "literal"]),
  ref: z.string().nullable(),
  lng: z.number(),
  lat: z.number(),
  note: z.string().optional(),
});

export const SimScene = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  arc_id: z.string().min(1),
  type: z.enum(["tableau", "encounter", "transition"]),
  priority: z.enum(["anchor", "supporting"]),
  chapter_gate: SimChapterGate,
  place: z.object({ id: z.string(), landmark: z.string(), arena: z.string() }),
  duration_ms: z.number().int().positive(),
  actors: z.array(SimActor).nonempty(),
  events: z.array(SimFxEvent),
  anchor: SimAnchor,
});

export const SimFrame = z.object({
  col: z.number().int().min(0).max(2),
  row: z.number().int().min(0).max(1),
  pivot: z.object({ x: z.number(), y: z.number() }),
});

export const SimAsset = z.object({
  url: z.string().refine(
    (url) => url.startsWith("/art/east-blue-2d/") || url.startsWith("/art/story-simulations/"),
    "simulation atlases must live under a signed public art prefix",
  ),
  sha256: z.string().length(64),
  kind: z.enum(["character", "tableau"]),
  variant: z.string(),
  map_height: z.number().positive(),
  grid: z.object({ columns: z.literal(3), rows: z.literal(2), cell_px: z.literal(384) }),
  frames: z.record(z.string(), SimFrame),
  runtime_rules: z.record(z.string(), z.unknown()),
});

export const StorySimulationPack = z.object({
  _meta: z.object({
    generator: z.string(),
    schema_version: z.literal(1),
    pack_id: z.string(),
    chapter_span: z.object({ start: z.number(), end: z.number() }),
    source_manifest_sha256: z.string().length(64),
    integration_ready: z.boolean(),
    feature_flag: z.string(),
    note: z.string(),
    counts: z.object({ scenes: z.number(), refused: z.number(), assets: z.number() }),
  }),
  arcs: z.array(z.object({ id: z.string(), label: z.string(), chapters: z.tuple([z.number(), z.number()]) })),
  runtime_policy: z.record(z.string(), z.unknown()),
  scenes: z.array(SimScene),
  refused: z.array(
    z.object({
      id: z.string(),
      readiness: z.string(),
      why: z.string(),
      missing_assets: z.array(z.string()),
    }),
  ),
  assets: z.record(z.string(), SimAsset),
  supersedes_visible_art: z.array(z.string()),
});

/** Backward-compatible value alias for existing East Blue imports. */
export const EastBlueSimulations = StorySimulationPack;

export type SimEase = z.infer<typeof SimEase>;
export type SimAnchor = z.infer<typeof SimAnchor>;
export type SimKeyframe = z.infer<typeof SimKeyframe>;
export type SimActor = z.infer<typeof SimActor>;
export type SimFxEvent = z.infer<typeof SimFxEvent>;
export type SimScene = z.infer<typeof SimScene>;
export type SimFrame = z.infer<typeof SimFrame>;
export type SimAsset = z.infer<typeof SimAsset>;
export type StorySimulationPack = z.infer<typeof StorySimulationPack>;
export type EastBlueSimulations = StorySimulationPack;

/* ── ready-gated scene clock ────────────────────────────────────────────────
 * Kept beside the pure evaluator so the browser host and a headless audit use
 * the exact same clock math. A scene exists before its atlases do; `ready`
 * makes that loading interval an authored t=0 hold rather than lost runtime.
 */

export type ReadyGatedSceneClock = {
  /** Absolute host timestamp corresponding to authored t=0. */
  startedAt: number;
  /** Absolute timestamp at which the clock was paused, if any. */
  pausedAt: number | null;
  /** Fade-in origin. Reset when the required textures become renderable. */
  mountedAt: number;
  /** False until every required texture has loaded and reached the layer. */
  ready: boolean;
};

export function createReadyGatedSceneClock(nowMs: number): ReadyGatedSceneClock {
  return { startedAt: nowMs, pausedAt: null, mountedAt: nowMs, ready: false };
}

/** Open the clock exactly once. Loading in a hidden tab starts paused. */
export function markSceneClockReady(
  clock: ReadyGatedSceneClock,
  nowMs: number,
  hidden: boolean,
): void {
  if (clock.ready) return;
  clock.ready = true;
  clock.startedAt = nowMs;
  clock.mountedAt = nowMs;
  clock.pausedAt = hidden ? nowMs : null;
}

export function pauseSceneClock(clock: ReadyGatedSceneClock, nowMs: number): void {
  if (clock.ready && clock.pausedAt === null) clock.pausedAt = nowMs;
}

export function resumeSceneClock(clock: ReadyGatedSceneClock, nowMs: number): void {
  if (!clock.ready || clock.pausedAt === null) return;
  clock.startedAt += nowMs - clock.pausedAt;
  clock.pausedAt = null;
}

/** Authored local time. Before readiness, every caller receives exactly zero. */
export function sceneClockElapsedMs(clock: ReadyGatedSceneClock, nowMs: number): number {
  if (!clock.ready) return 0;
  return Math.max(0, (clock.pausedAt ?? nowMs) - clock.startedAt);
}

/**
 * Absolute displacement for a streak at `ageMs`.
 *
 * The old renderer added 0.015 units on every frame, making a 120 Hz device
 * move twice as far as a 60 Hz one. This is the analytic integral of that
 * intended 60 Hz velocity curve, so the look is preserved while frame history
 * and refresh rate disappear from the result.
 */
export function streakDisplacementAtAge(
  ageMs: number,
  durationMs: number,
  size: number,
  direction: 1 | -1,
): number {
  const safeDuration = Math.max(1, durationMs);
  const u = Math.min(1, Math.max(0, ageMs / safeDuration));
  const intendedUnitsPerMs = 0.015 * 60 / 1000;
  return direction * intendedUnitsPerMs * safeDuration * (u - 0.5 * u * u) * size;
}

/** Parse-or-throw, the lib/schema.ts posture. Callers dynamic-import the JSON
 * and hand it here; the throw happens before anything reaches a GPU. */
export function loadSimulations(raw: unknown): StorySimulationPack {
  return StorySimulationPack.parse(raw);
}

/* ── easing ──────────────────────────────────────────────────────────────────
 * Applied to the SEGMENT's normalized progress only — the contract's
 * "linear-or-authored-ease". The ease named on a keyframe governs the segment
 * ARRIVING at it, matching how the contract authors read their own data
 * (an "accelerate" on Buggy's launch keyframe is the launch accelerating away).
 */

const EASES: Record<SimEase, (u: number) => number> = {
  linear: (u) => u,
  // smoothstep: gentle in and out, the contract's "smooth".
  smooth: (u) => u * u * (3 - 2 * u),
  accelerate: (u) => u * u,
  decelerate: (u) => 1 - (1 - u) * (1 - u),
};

/* ── evaluation ─────────────────────────────────────────────────────────── */

export type ActorState = {
  /** Normalized stage coords, -1..1 left→right; y rises from the ground plane. */
  x: number;
  y: number;
  scale: number;
  /** Degrees, as authored. */
  rotation: number;
  opacity: number;
  /** Atlas frame name — STEP-selected, never blended. */
  pose: string;
};

/**
 * Where an actor is at local time tMs. Clamped at both ends: before the first
 * keyframe the actor holds it (an actor whose track starts at t=5600 with
 * opacity 0 is simply not there yet, which is how the contract stages late
 * entrances); after the last keyframe it holds the final frame forever — the
 * "play once, hold the authored final frame" policy falls out of the math.
 */
export function evaluateActor(actor: SimActor, tMs: number): ActorState {
  const kfs = actor.keyframes;
  let prev = kfs[0];
  let next: SimKeyframe | null = null;
  for (const kf of kfs) {
    if (kf.t <= tMs) {
      prev = kf;
    } else {
      next = kf;
      break;
    }
  }
  // Before the first keyframe, or at/after the last: hold.
  if (tMs < kfs[0].t || !next) {
    const hold = tMs < kfs[0].t ? kfs[0] : prev;
    return { x: hold.x, y: hold.y, scale: hold.scale, rotation: hold.rotation, opacity: hold.opacity, pose: hold.pose };
  }
  const span = next.t - prev.t;
  const u = span > 0 ? (tMs - prev.t) / span : 1;
  const eased = EASES[next.ease ?? "linear"](Math.min(1, Math.max(0, u)));
  const lerp = (a: number, b: number) => a + (b - a) * eased;
  return {
    x: lerp(prev.x, next.x),
    y: lerp(prev.y, next.y),
    scale: lerp(prev.scale, next.scale),
    rotation: lerp(prev.rotation, next.rotation),
    opacity: lerp(prev.opacity, next.opacity),
    // Pose is the STEP: prev's cell until the exact authored moment.
    pose: prev.pose,
  };
}

/* ── FX cursor ───────────────────────────────────────────────────────────────
 * Fire-once semantics with deterministic backward reset. The cursor is the ONE
 * stateful object in this module, and its state is a pure function of the
 * time sequence fed to it: sample(3400) after sample(5000) rebuilds from zero,
 * so scrubbing 51→49→51 replays the fight identically.
 */

export type FiredFx = SimFxEvent & {
  /** Local ms since this event fired; 0 at the firing instant. */
  age: number;
  /** True while age < duration_ms — the window a renderer draws in. */
  active: boolean;
};

export type FxCursor = {
  /** Advance (or rewind) to tMs; returns every event fired by tMs, with ages. */
  sample(tMs: number): FiredFx[];
  /** Forget everything, as if the scene never played. */
  reset(): void;
};

export function createFxCursor(scene: SimScene): FxCursor {
  // Sorted once; the contract authors in order but the guarantee is ours.
  const events = [...scene.events].sort((a, b) => a.t - b.t);
  let lastT = -1;

  return {
    sample(tMs: number): FiredFx[] {
      // Backward means rebuild — comparing against lastT is the entire
      // scrub-safety mechanism, so it stays explicit rather than clever.
      if (tMs < lastT) lastT = -1;
      lastT = Math.max(lastT, tMs);
      const fired: FiredFx[] = [];
      for (const ev of events) {
        if (ev.t > tMs) break;
        const age = tMs - ev.t;
        fired.push({ ...ev, age, active: age < ev.duration_ms });
      }
      return fired;
    },
    reset() {
      lastT = -1;
    },
  };
}

/* ── atlas UV ────────────────────────────────────────────────────────────────
 * The handoff's exact math for a 3×2 top-left-indexed atlas under three.js's
 * bottom-left texture coords:
 *   repeat = (1/3, 1/2);  offset = (col/3, 1 - (row+1)/2)
 * Returned as plain numbers so this module stays three-free; sim-layer feeds
 * them to texture.repeat/.offset on a PER-ACTOR CLONE of the base texture —
 * two actors sharing an atlas would otherwise overwrite each other's pose.
 */

export type PoseUv = { repeatX: number; repeatY: number; offsetX: number; offsetY: number };

/** Cells are packed edge-to-edge, so exact-cell UVs let linear filtering sample
 * a sliver of the NEIGHBOURING pose at the border (measured: a spare pair of
 * legs floating beside Luffy at Loguetown). A 2px inset per edge trades four
 * invisible pixels for clean card edges. */
const ATLAS_W = 1152;
const ATLAS_H = 768;
const INSET_PX = 2;

export function poseUv(frames: Record<string, SimFrame>, pose: string): PoseUv {
  const f = frames[pose];
  if (!f) throw new Error(`pose ${pose} is not in this atlas — check_simulations should have caught this`);
  const ix = INSET_PX / ATLAS_W;
  const iy = INSET_PX / ATLAS_H;
  return {
    repeatX: 1 / 3 - 2 * ix,
    repeatY: 1 / 2 - 2 * iy,
    offsetX: f.col / 3 + ix,
    offsetY: 1 - (f.row + 1) / 2 + iy,
  };
}

/** The chapter/readiness filter, verbatim from the handoff's pseudo-code.
 * Readiness and gate verification were enforced at sync; re-checking here costs
 * one boolean and means a hand-edited artifact still can't leak. */
export function sceneEligible(scene: SimScene, chapter: number, flagOn: boolean): boolean {
  return flagOn && scene.chapter_gate.verification === "verified" && chapter >= scene.chapter_gate.start;
}

/** Inside the active window the scene PLAYS; after it, the final frame HOLDS. */
export function sceneInActiveWindow(scene: SimScene, chapter: number): boolean {
  return chapter <= scene.chapter_gate.end;
}
