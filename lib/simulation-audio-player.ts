/**
 * lib/simulation-audio-player.ts — scene sound, driven by the scene clock.
 *
 * Implements the SimAudioSink seam: sim-models feeds it the renderer's own
 * clock value each frame, and this player advances a deterministic cursor
 * over the scene's COMPILED audio bindings (absolute at_ms — the compiler
 * resolved every event reference; nothing is re-derived here) and fires
 * one-shots through the AudioDirector.
 *
 * Loaded ONLY by the sim host's dynamic-import chain — flags off, none of
 * this (nor its JSON) reaches the bundle. Locked or muted, every call is a
 * cheap no-op: a scene that plays before the reader opts into sound is a
 * silent scene, and its cues do NOT retro-fire on unlock (the cursor keeps
 * advancing; determinism over completeness).
 *
 * HOT PATH: onSceneTime runs inside the renderer's frame. No allocation on
 * the quiet path — the cursor returns early with a shared empty sample.
 */

import { AudioDirector } from "@/lib/audio-director";
import { getSimAudioSink, setSimAudioSink } from "@/lib/sim-audio-bridge";
import {
  createAudioEventCursor,
  loadSimulationAudioRegistry,
  type AudioEventCursor,
  type SimulationAudioCue,
} from "@/lib/simulation-audio";
import { loadScenePlayback, type ScenePlaybackRow } from "@/lib/scene-playback";

const DUCK_LEVEL = 0.28;
const DUCK_ATTACK_MS = 150;
const DUCK_RELEASE_MS = 400;
const END_FADE_MS = 160;
const REWIND_FADE_MS = 30;
const TABLEAU_FADE_MS = 300;

type SceneAudioState = {
  cursor: AudioEventCursor;
  row: ScenePlaybackRow;
  /** cue ids this scene binds — the preload set and eviction keep-set. */
  cueIds: Set<string>;
  preloadStarted: boolean;
  tableau: boolean;
};

type FiredRecord = { sceneId: string; bindingId: string; atMs: number; firedAtT: number };

export class SimulationAudioPlayer {
  private scenes = new Map<string, SceneAudioState>();
  private cues: Map<string, SimulationAudioCue>;
  private rows: Map<string, ScenePlaybackRow>;
  private director: AudioDirector;
  /** Dev-only fired-cue log, read by the audits via window.__simAudio. */
  readonly firedLog: FiredRecord[] = [];

  constructor(cues: SimulationAudioCue[], rows: ScenePlaybackRow[]) {
    this.director = AudioDirector.get();
    this.cues = new Map(cues.filter((c) => c.enabled).map((c) => [c.id, c]));
    this.rows = new Map(rows.map((r) => [r.scene_id, r]));
  }

  onSceneMount(sceneId: string, _scene: unknown, ctx: { reducedMotion: boolean }): void {
    // Reduced motion renders the static tableau and never runs the clock;
    // the sink is never fed there anyway (sim-layer skips getTimeMs) — this
    // guard is defense in depth, keeping even preload traffic at zero.
    if (ctx.reducedMotion) return;
    const row = this.rows.get(sceneId);
    if (!row || row.audio.length === 0) return;
    const cueIds = new Set(row.audio.map((b) => b.cue_id).filter((id) => this.cues.has(id)));
    this.scenes.set(sceneId, {
      cursor: createAudioEventCursor(row.audio),
      row,
      cueIds,
      preloadStarted: false,
      tableau: false,
    });
    this.preload(sceneId);
  }

  onSceneTime(sceneId: string, tMs: number | null): void {
    const state = this.scenes.get(sceneId);
    if (!state) return;

    if (tMs === null) {
      // Held tableau: loops off, tails may finish, nothing ever fires.
      if (!state.tableau) {
        state.tableau = true;
        this.director.stopOwner(sceneId, TABLEAU_FADE_MS);
        this.settleDuck();
      }
      return;
    }
    state.tableau = false;

    // The reader may unlock sound mid-scene — start decoding then.
    if (!state.preloadStarted && this.director.unlocked) this.preload(sceneId);

    const { fired, rewound } = state.cursor.sample(tMs);
    if (rewound) {
      // Backward scrub silences NOW — the visual layer's instant-unmount rule.
      this.director.stopOwner(sceneId, REWIND_FADE_MS);
      this.settleDuck();
      return;
    }
    if (fired.length === 0) return;

    for (const binding of fired) {
      const cue = this.cues.get(binding.cue_id);
      if (!cue) continue;
      this.director.play({
        cueId: cue.id,
        src: cue.src,
        bus: cue.bus,
        family: cue.family,
        gain: binding.gain,
        pan: binding.pan,
        playbackRate: binding.playback_rate,
        loop: cue.loop,
        ownerId: sceneId,
        maxVoices: cue.max_voices,
      });
      if (process.env.NODE_ENV !== "production") {
        this.firedLog.push({ sceneId, bindingId: binding.id, atMs: binding.at_ms, firedAtT: tMs });
      }
    }
    if (this.director.unlocked && !this.director.isMuted) {
      this.director.duckScore(DUCK_LEVEL, DUCK_ATTACK_MS);
    }
  }

  onSceneEnd(sceneId: string): void {
    const state = this.scenes.get(sceneId);
    if (!state) return;
    this.scenes.delete(sceneId);
    this.director.stopOwner(sceneId, END_FADE_MS);
    // Keep only the still-mounted scenes' buffers decoded.
    const keep = new Set<string>();
    for (const remaining of this.scenes.values()) {
      for (const id of remaining.cueIds) keep.add(id);
    }
    this.director.evictExcept(keep);
    this.settleDuck();
  }

  private preload(sceneId: string): void {
    const state = this.scenes.get(sceneId);
    if (!state || state.preloadStarted || !this.director.unlocked) return;
    state.preloadStarted = true;
    for (const cueId of state.cueIds) {
      const cue = this.cues.get(cueId);
      if (cue) void this.director.preload(cue.id, cue.src);
    }
  }

  /** Restore the score once no scene voice remains live. */
  private settleDuck(): void {
    if (this.director.liveVoiceCount === 0) this.director.duckScore(1, DUCK_RELEASE_MS);
  }
}

let installed = false;

/**
 * Install the player as THE sim audio sink. Called from the sim host's own
 * dynamic-import chain (sim-models), so flags-off bundles never see it.
 * Loads the cue registry and the compiled playback artifact once.
 */
export async function installSimulationAudio(): Promise<void> {
  if (installed || typeof window === "undefined") return;
  installed = true;
  const [cuesRaw, playbackRaw] = await Promise.all([
    import("@/data/simulation-audio-cues.json"),
    import("@/data/generated/story_scene_playback.json"),
  ]);
  const registry = loadSimulationAudioRegistry(cuesRaw.default);
  const playback = loadScenePlayback(playbackRaw.default);
  const player = new SimulationAudioPlayer(registry.cues, playback.scenes);
  setSimAudioSink(player);

  if (process.env.NODE_ENV !== "production") {
    const director = AudioDirector.get();
    (window as Window & { __simAudio?: unknown }).__simAudio = {
      get fired() {
        return player.firedLog;
      },
      get unlocked() {
        return director.unlocked;
      },
      get muted() {
        return director.isMuted;
      },
      get liveVoices() {
        return director.liveVoiceCount;
      },
      get sink() {
        return getSimAudioSink() === player;
      },
    };
  }
}
