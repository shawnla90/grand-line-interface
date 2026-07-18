/**
 * lib/simulation-audio.ts — the cue registry's runtime shape and the
 * deterministic audio-event cursor. PURE, no React, no Web Audio.
 *
 * The cursor is createFxCursor's sibling (lib/simulation.ts) with one
 * deliberate divergence: visuals retro-draw a late-joined FX faded by age;
 * audio must never retro-FIRE a batch — three impacts at once because a
 * cursor joined mid-scene is a blast, not a scene. A cursor whose first
 * sample lands past the join grace simply arms at that time and fires only
 * genuinely-forward crossings from there.
 */

import { z } from "zod";
import type { SceneAudioBinding } from "@/lib/scene-playback";

/* ── the cue registry (data/simulation-audio-cues.json) ─────────────────── */

export const AudioBusName = z.enum(["score", "voice", "ambience", "sfx"]);

export const SimulationAudioCue = z.object({
  id: z.string().min(1),
  /** Master filename — the provenance join key into the owning manifest
   * (simulations masters, or the frozen epic-journey OP library). */
  source_file: z.string().min(1),
  /** Browser derivative under public/. Two legal homes: cues prepared by
   * this pipeline, or the frozen epic-journey derivatives (the OP voice
   * library serves both the Epic beds and the scene clocks). */
  src: z.string().refine(
    (value) => value.startsWith("/audio/simulations/") || value.startsWith("/audio/epic-journey/"),
    { message: "src must live under /audio/simulations/ or /audio/epic-journey/" },
  ),
  kind: z.enum(["sfx", "music", "voice", "ambience"]),
  bus: AudioBusName,
  /** Concurrency family — caps simultaneous voices of a texture. */
  family: z.string().min(1),
  duration_ms: z.number().int().positive(),
  sample_rate: z.literal(48000),
  channels: z.union([z.literal(1), z.literal(2)]),
  source: z.string().min(1),
  license: z.string().min(1),
  rights_status: z.enum(["cleared", "attribution_required", "local_prototype_only", "blocked"]),
  /** Path to the provenance/rights receipt for this master. */
  receipt: z.string().min(1).nullable(),
  attribution: z.string().min(1).nullable(),
  max_voices: z.number().int().min(1).max(8),
  loop: z.boolean(),
  enabled: z.boolean(),
});

export const SimulationAudioRegistry = z.object({
  version: z.literal(1),
  default_rights_status: z.string(),
  cues: z.array(SimulationAudioCue),
});

export type AudioBusName = z.infer<typeof AudioBusName>;
export type SimulationAudioCue = z.infer<typeof SimulationAudioCue>;
export type SimulationAudioRegistry = z.infer<typeof SimulationAudioRegistry>;

/** Parse-or-throw, the lib/simulation.ts posture. */
export function loadSimulationAudioRegistry(raw: unknown): SimulationAudioRegistry {
  return SimulationAudioRegistry.parse(raw);
}

/* ── the deterministic audio-event cursor ───────────────────────────────── */

/** A first sample past this is a late join (cursor created mid-scene): arm
 * without firing. Clocks start at 0 on mount, so a normal first frame lands
 * well inside the grace and cue-at-0 ambience still fires. */
const LATE_JOIN_GRACE_MS = 250;

export type AudioCursorSample = {
  /** Bindings whose at_ms was crossed going FORWARD this frame — fire these. */
  fired: SceneAudioBinding[];
  /** True when time moved backward: the caller must silence NOW (the visual
   * unmount rule — backward scrub re-fogs instantly, sound follows). */
  rewound: boolean;
};

export type AudioEventCursor = {
  sample(tMs: number): AudioCursorSample;
  reset(): void;
};

export function createAudioEventCursor(bindings: SceneAudioBinding[]): AudioEventCursor {
  const sorted = [...bindings].sort((a, b) => a.at_ms - b.at_ms);
  let lastT = -1;
  let primed = false;

  return {
    sample(tMs: number): AudioCursorSample {
      if (!primed) {
        primed = true;
        if (tMs > LATE_JOIN_GRACE_MS) {
          lastT = tMs;
          return { fired: [], rewound: false };
        }
      }
      if (tMs < lastT) {
        // Backward: mirror createFxCursor's reset. Everything re-arms and
        // fires again only on the next genuinely-forward crossing.
        lastT = -1;
        return { fired: [], rewound: true };
      }
      const fired: SceneAudioBinding[] = [];
      for (const binding of sorted) {
        if (binding.at_ms > lastT && binding.at_ms <= tMs) fired.push(binding);
        else if (binding.at_ms > tMs) break;
      }
      lastT = tMs;
      return { fired, rewound: false };
    },
    reset() {
      lastT = -1;
      primed = false;
    },
  };
}
