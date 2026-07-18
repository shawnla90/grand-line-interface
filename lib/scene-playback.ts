/**
 * lib/scene-playback.ts — the compiled scene-playback artifact's runtime shape.
 *
 * data/generated/story_scene_playback.json is the app-owned journey/sound
 * treatment for the signed story scenes: which scenes are journey stops, how
 * long each dwell holds, and every audio cue binding ALREADY RESOLVED to an
 * absolute scene-local millisecond by scripts/compile_scene_playback.py. The
 * runtime never re-derives timing — the compiler proved it once.
 *
 * PURE schema + parse-or-throw loader, the lib/simulation.ts posture. Callers
 * dynamic-import the JSON so none of this reaches a flags-off bundle.
 */

import { z } from "zod";

export const SceneAudioBinding = z.object({
  id: z.string().min(1),
  cue_id: z.string().min(1),
  /** Absolute scene-local ms — compiler-resolved, inside [0, duration_ms]. */
  at_ms: z.number().int().nonnegative(),
  gain: z.number().min(0).max(1),
  pan: z.number().min(-1).max(1),
  playback_rate: z.number().min(0.5).max(2),
});

export const ScenePlaybackRow = z.object({
  scene_id: z.string().min(1),
  pack_id: z.string().min(1),
  /** Canon events slug the journey caption resolves from; null on rows that
   * never enter the journey. */
  event: z.string().min(1).nullable(),
  label_override: z.string().min(1).nullish(),
  chapter: z.number().int().min(1),
  duration_ms: z.number().int().positive(),
  anchor: z.object({ lng: z.number(), lat: z.number() }),
  journey: z.object({
    enabled: z.boolean(),
    hold_ms: z.number().int().positive(),
    zoom: z.number(),
    pitch: z.number(),
  }),
  audio: z.array(SceneAudioBinding),
});

export const ScenePlayback = z.object({
  _meta: z.object({
    generator: z.string(),
    schema_version: z.literal(1),
    counts: z.object({
      scenes: z.number().int(),
      journey_enabled: z.number().int(),
      audio_bindings: z.number().int(),
    }),
  }),
  scenes: z.array(ScenePlaybackRow),
});

export type SceneAudioBinding = z.infer<typeof SceneAudioBinding>;
export type ScenePlaybackRow = z.infer<typeof ScenePlaybackRow>;
export type ScenePlayback = z.infer<typeof ScenePlayback>;

/** Parse-or-throw: a malformed artifact fails loudly before any stop builds. */
export function loadScenePlayback(raw: unknown): ScenePlayback {
  return ScenePlayback.parse(raw);
}
