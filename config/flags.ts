/**
 * config/flags.ts — build-time feature flags.
 *
 * ── A CORRECTION, KEPT RATHER THAN QUIETLY DELETED ─────────────────────────
 *
 * This file used to make two claims. Both were false, and one of them was the
 * argument for its own existence.
 *
 * It said all 11 narrative scenes resolve `asset_not_ready` "because zero are
 * integration_ready and both blockouts are runtime_export: false. Two independent
 * locks, neither of them ours to open." Codex's a7de84d opened both. All 11 are
 * `integration_ready`, all 11 blockouts export, and `asset_not_ready` is now
 * UNREACHABLE — no code path in lib/scenes.ts can produce it. Every scene
 * resolves `visible: true` at ch1185 with zero reasons.
 *
 * It also said: "The proof is grep-able — `npm run build && grep -r
 * "zunesha\|yarukiman\|puffing-tom" .next/static/` — and scripts/check_scenes.py
 * runs exactly that." It does not. That script has no build step and no bundle
 * grep; its only subprocess call re-runs sync_scenes.py for the reproducibility
 * check. The dead-code-elimination guarantee this file's whole design rested on
 * was never enforced by anything.
 *
 * ── WHAT IS ACTUALLY TRUE ──────────────────────────────────────────────────
 *
 * `narrativeScenes` guards NOTHING, because the reader-facing surface it was
 * written to guard was never built. Grep it: every hit is a comment. No file
 * imports this module. The `if (!FLAGS.narrativeScenes) return null;` below is
 * illustrative prose in a docstring, not a call site — which is why the bundler
 * has nothing to eliminate and the grep-able proof has nothing to prove.
 *
 * The only consumer of the narrative registry is /admin/scenes, and it ignores
 * this flag deliberately and says so: "the flag governs what a READER sees, and
 * this page has no readers." It gates on NODE_ENV instead.
 *
 * So the flag is vestigial. It is kept, rather than deleted, for one reason that
 * is not sentiment: the registry now reports every scene as visible, so the first
 * component that imports `sceneVisibilityAt` and believes it puts eleven
 * unrendered scenes on the map. This constant is the thing that import should
 * check, and the comment it needs to read is this one. If the registry is still
 * unwired a month from now, delete both.
 *
 * ── WHY A LITERAL, WHEN IT DOES BECOME REAL ────────────────────────────────
 *
 * A literal `false` lets the bundler prove "the map is unchanged while the flag
 * is off" as a FACT rather than a promise: the branch, the registry, and every
 * scene string leave the client bundle entirely. An env var cannot — its value is
 * unknowable at build time, so the feature ships and we are back to trusting a
 * boolean at runtime. That difference is real and measured: the runtime-3D env
 * flags DO ship ~1KB of dead branch each, and `knockup3d` is greppable in
 * .next/static with the flag off. They are env vars because the asset track names
 * them and wants them toggled without a code change. This one has no such
 * constraint.
 *
 * The claim and its enforcement have to ship together. When something imports
 * this, the same commit adds the bundle grep to check_scenes.py — otherwise the
 * comment is just this file's old mistake in a new coat.
 */

export const FLAGS = {
  /**
   * The narrative scene registry (the Blender track's 11 v2 contracts).
   *
   * OFF, and — read the header — currently inert: nothing imports it. The 11
   * scenes are `integration_ready` with `runtime_export: true` and resolve
   * `visible: true`, so the data is ready and the renderer is not. The models
   * that DO render (components/runtime-models.ts) are a different system on a
   * different track, gated by the asset track's own env flags.
   */
  narrativeScenes: false,
} as const;
