/**
 * lib/sim-audio-bridge.ts — the seam between the scene clock and scene sound.
 *
 * A LEAF on purpose: imported by components/sim-models.ts (the clock owner)
 * and by lib/simulation-audio-player.ts (the listener) without creating a
 * cycle, and without either side knowing the other exists. sim-models calls
 * the sink if one is installed; with no sink installed the four call sites
 * are four null checks and the visual runtime is byte-for-byte unaffected.
 *
 * THE CLOCK CONTRACT: onSceneTime receives the EXACT value the renderer's
 * getTimeMs closure is about to return, on the same frame — the audio cursor
 * samples the identical clock as the visuals, so a cue can never drift from
 * the flash it is bound to. null = frozen tableau. Under prefers-reduced-motion
 * the renderer never calls getTimeMs, so the sink is structurally silent.
 */

import type { SimScene } from "@/lib/simulation";

export type SimAudioSink = {
  /** Scene mounted and its clock created — the preload window opens. */
  onSceneMount(sceneId: string, scene: SimScene, ctx: { reducedMotion: boolean }): void;
  /** The renderer's clock value for this frame; null = held tableau. */
  onSceneTime(sceneId: string, tMs: number | null): void;
  /** Layer unmounted (gate closed, pack switch, teardown) — fade and release. */
  onSceneEnd(sceneId: string): void;
};

let sink: SimAudioSink | null = null;

export function setSimAudioSink(next: SimAudioSink | null): void {
  sink = next;
}

export function getSimAudioSink(): SimAudioSink | null {
  return sink;
}
