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
 * A model goes in when scripts/shoot_models.py has photographed it rendering on a
 * globe frame AND that frame differs from the same frame with the model removed —
 * because a layer that is present but draws nothing would otherwise pass. The list
 * grows by running the shoot and pasting what it prints.
 *
 * The reverse also matters: if a future model genuinely cannot do globe — a
 * screen-space sprite, say, like wano-waterfall-ascent — it must NOT be listed,
 * and the manifest's restriction stands unchallenged. This file overrides one
 * specific false premise, not the field.
 */

/** Models photographed rendering on the globe. Evidence in data/review/glb/. */
export const GLOBE_PROVEN: ReadonlySet<string> = new Set<string>([
  // Every id here was PHOTOGRAPHED rendering on a globe frame by
  // scripts/shoot_models.py: layer present, and the frame differs from the
  // same frame with the model removed. Evidence: data/review/glb/<id>--globe.png
  // and the contact sheet at data/review/glb/index.html.
  //
  // Regenerate rather than edit: run the shoot and paste what it prints. A
  // model typed in here by hand has not been proven, and this file is only
  // worth having if that stays true.
  "amazon-lily",
  "cactus-island-whisky-peak",
  "conomi-arlong-park",
  "dressrosa-green-bit",
  "fish-man-island",
  "loguetown-roger-execution",
  "mary-geoise-red-line",
  "sabaody-grove-network",
  "skypiea-knock-up-stream",
  "totto-land",
  "world-government-tarai-system",
  "zou-zunesha",
]);

/**
 * THE BOOTSTRAP, and it needs saying out loud because it is a circle.
 *
 * A model earns GLOBE_PROVEN by being photographed rendering on the globe. But a
 * model that is not in GLOBE_PROVEN never renders on the globe, so it can never
 * be photographed. Left alone, the list could only ever be populated by someone
 * typing into it — which is the exact failure this file was written to avoid.
 *
 * So scripts/shoot_models.py sets this, shoots every model on a globe frame, and
 * prints the ids that actually put pixels down. Those go in the list above. The
 * evidence comes first and the entry second, which is the whole point.
 *
 * NEXT_PUBLIC_, so it is inlined at build time and a production build without it
 * cannot be talked into forcing anything at runtime. It is a darkroom door, not a
 * setting.
 */
const FORCE_GLOBE = process.env.NEXT_PUBLIC_FORCE_GLOBE === "1";

/** Is this model allowed on the globe despite declaring mercator-only? */
export function globeProven(id: string): boolean {
  return FORCE_GLOBE || GLOBE_PROVEN.has(id);
}
