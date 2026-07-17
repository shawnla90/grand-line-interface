/**
 * config/projection-overrides.ts — the one place the app overrules the manifest.
 *
 * DELETE THIS FILE the day the asset track widens `projection_support`. It exists
 * to be temporary, and if it is still here in a month somebody forgot to send the
 * message.
 *
 * ── WHY IT EXISTS ──────────────────────────────────────────────────────────
 *
 * Every model in the runtime batch declares:
 *
 *   "projection_support": ["mercator_closeup"]
 *   "globe_policy": "transparent fallback; do not apply a NAIVE mercator model
 *                    matrix on globe"
 *
 * The policy is right and the restriction follows from it — for a naive loader.
 * MapLibre's own docs say the same thing: a matrix-only custom layer is
 * "sufficient for simple custom layers that ALSO ONLY SUPPORT MERCATOR
 * PROJECTION", because globe projection happens in its vertex shaders and three.js
 * brings its own. A loader that takes the obvious path really is mercator-only.
 *
 * Ours does not take the obvious path. components/glb-layer.ts draws through
 * `map.transform.getMatrixForModel(lngLat, altitude)`, whose GLOBE implementation
 * maps model metres onto the unit sphere — precisely the space `mainMatrix`
 * consumes. No naive mercator matrix is ever applied to anything, on any
 * projection. The asset track's acceptance list says "Globe projection never
 * receives a naive mercator-only model matrix"; we satisfy that clause exactly,
 * which is the clause that carries the intent.
 *
 * So the premise behind `["mercator_closeup"]` is false for this app. That does
 * not make the field wrong to have written, and it does not make it ours to edit:
 * `blender-assets/` is read-only to us, and a track that quietly discards the
 * other track's data is a track the other one cannot trust. Hence an override
 * that is app-owned, named per model, evidenced, versioned, and reviewable — and
 * that a reader can find in one grep.
 *
 * ── WHAT EARNS A MODEL A PLACE HERE ────────────────────────────────────────
 *
 * Pixels. Not reasoning, not "the loader is projection-aware", not this comment.
 * A model goes in when scripts/audit_glb.py has photographed it rendering on the
 * globe and the frame differs from the same frame without it. That is why the
 * list is short and why it grows by running the audit rather than by typing.
 *
 * The reverse also matters: if a future model genuinely cannot do globe — a
 * screen-space sprite, say, like wano-waterfall-ascent — it must NOT be listed,
 * and the manifest's restriction stands unchallenged. This file overrides one
 * specific false premise, not the field.
 */

/**
 * Models proven to render correctly on the globe, with the evidence.
 *
 * evidence: data/review/glb/globe-ch236-z6.png (skypiea-knock-up-stream)
 *           audit_glb 13/13, "ch236 z6 GLOBE: the model puts PIXELS on the canvas"
 */
export const GLOBE_PROVEN: ReadonlySet<string> = new Set<string>([
  // The pilot. Photographed standing on the globe at ch236, zoom 6, pitch 60 —
  // a 987km column of water with the Going Merry riding it. Its manifest predates
  // `projection_support` and declares none, so this entry changes nothing today;
  // it is here because it is the model the proof was made on.
  "skypiea-knock-up-stream",
]);

/** Is this model allowed on the globe despite declaring mercator-only? */
export function globeProven(id: string): boolean {
  return GLOBE_PROVEN.has(id);
}
