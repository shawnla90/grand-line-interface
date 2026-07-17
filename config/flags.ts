/**
 * config/flags.ts — build-time feature flags.
 *
 * A LITERAL CONST, not an env var and not a URL param, and that is the whole
 * design. "The map is unchanged while the flag is off" should be a FACT you can
 * check, not a promise you make. A literal `false` lets the bundler prove it:
 *
 *   if (!FLAGS.narrativeScenes) return null;
 *
 * dead-code-eliminates, so the registry, the scene data and every string in it
 * never enter the client bundle at all. The proof is grep-able —
 *
 *   npm run build && grep -r "zunesha\|yarukiman\|puffing-tom" .next/static/
 *
 * — and scripts/check_scenes.py runs exactly that. An env var could not be
 * eliminated (its value is unknowable at build time), so the bundle would carry
 * the feature and we would be back to trusting a boolean at runtime. A URL param
 * would be worse: it hands an unfinished feature a public surface.
 *
 * Flipping one of these is a one-line code change and a rebuild. For a feature
 * whose entire brief is "data-only first, wire nothing", that friction is the
 * point rather than a cost.
 */

export const FLAGS = {
  /**
   * The narrative scene registry (the Blender track's 11 v2 contracts).
   *
   * OFF, and it would change nothing if it were on: all 11 resolve to
   * `asset_not_ready` because zero are `integration_ready` in the asset queue
   * and both existing blockouts are `runtime_export: false`. Two independent
   * locks, neither of them ours to open. See lib/scenes.ts.
   */
  narrativeScenes: false,
} as const;
