import type { EpicCuePlayback } from "@/lib/epic-journey";
import { AudioDirector } from "@/lib/audio-director";

type LiveTrack = {
  audio: HTMLAudioElement;
  generation: number;
  duckGain: number;
};

const FADE_IN_MS = 70;
const FADE_OUT_MS = 160;

function envelope(elapsedMs: number, durationMs: number): number {
  const fadeIn = Math.min(1, Math.max(0, elapsedMs / FADE_IN_MS));
  const fadeOut = Math.min(1, Math.max(0, (durationMs - elapsedMs) / FADE_OUT_MS));
  return Math.min(fadeIn, fadeOut);
}

/**
 * Keeps every active Epic audio lane synchronized to the pure timeline.
 * Tracks fade at their real media boundaries and are released only after the
 * replacement lane has entered, avoiding the old pause/remove/load hard cut.
 */
export class EpicAudioPlayer {
  private readonly tracks = new Map<string, LiveTrack>();
  private muted = false;
  private generation = 0;

  constructor(private readonly onError?: (message: string) => void) {}

  setMuted(muted: boolean) {
    this.muted = muted;
    for (const { audio } of this.tracks.values()) audio.muted = muted;
  }

  sync(playbacks: EpicCuePlayback[]) {
    const activeIds = new Set(playbacks.map(({ cue }) => cue.id));
    const hasForeground = playbacks.some(({ cue }) => cue.lane !== "bed");
    for (const [cueId, track] of this.tracks) {
      if (activeIds.has(cueId)) continue;
      this.release(cueId, track);
    }

    for (const playback of playbacks) {
      const { cue, cueElapsedMs } = playback;
      let live = this.tracks.get(cue.id);
      if (!live) {
        const generation = ++this.generation;
        const audio = new Audio(cue.src);
        audio.preload = "auto";
        audio.muted = this.muted;
        live = { audio, generation, duckGain: cue.lane === "bed" && hasForeground ? 0.28 : 1 };
        this.tracks.set(cue.id, live);

        const targetSeconds = Math.max(0, cueElapsedMs / 1000);
        const seekToTimeline = () => {
          const current = this.tracks.get(cue.id);
          if (current?.generation !== generation || current.audio !== audio) return;
          if (targetSeconds < audio.duration) audio.currentTime = targetSeconds;
        };
        if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) seekToTimeline();
        else audio.addEventListener("loadedmetadata", seekToTimeline, { once: true });

        void audio.play().catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") return;
          const message = error instanceof Error ? error.message : "The browser blocked audio playback.";
          this.onError?.(message);
        });
      }

      const targetSeconds = Math.max(0, cueElapsedMs / 1000);
      if (
        targetSeconds < cue.durationMs / 1000
        && live.audio.readyState >= HTMLMediaElement.HAVE_METADATA
        && Math.abs(live.audio.currentTime - targetSeconds) > 0.45
      ) {
        live.audio.currentTime = targetSeconds;
      }
      // Keep the long score audible, but make room for chapter dialogue and
      // attacks instead of stacking two full-volume files on top of each other.
      const targetDuckGain = cue.lane === "bed" && hasForeground ? 0.28 : 1;
      // Ramp the bed under and back out of dialogue; an instantaneous 1→.28
      // volume jump is itself another audible cut.
      live.duckGain += (targetDuckGain - live.duckGain) * 0.18;
      // ONE duck state across both audio worlds: a scene's Web Audio SFX
      // burst ducks the director's score bus, and the element-based beds
      // follow the same level so the OST makes room for the fight too.
      const sceneDuck = cue.lane === "bed" ? AudioDirector.get().scoreDuckLevel : 1;
      live.audio.volume = Math.max(
        0,
        Math.min(1, cue.gain * live.duckGain * sceneDuck * envelope(cueElapsedMs, cue.durationMs)),
      );
    }
  }

  stop() {
    this.generation += 1;
    for (const [cueId, track] of this.tracks) this.release(cueId, track);
  }

  private release(cueId: string, track: LiveTrack) {
    track.audio.pause();
    track.audio.removeAttribute("src");
    track.audio.load();
    this.tracks.delete(cueId);
  }
}
