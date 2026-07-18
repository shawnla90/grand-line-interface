import type { EpicAudioCue } from "@/config/epic-audio-cues";

/** One streaming element, switched only when the pure epic timeline changes cue. */
export class EpicAudioPlayer {
  private audio: HTMLAudioElement | null = null;
  private cueId: string | null = null;
  private muted = false;
  private generation = 0;

  constructor(private readonly onError?: (message: string) => void) {}

  setMuted(muted: boolean) {
    this.muted = muted;
    if (this.audio) this.audio.muted = muted;
  }

  sync(cue: EpicAudioCue | null, cueElapsedMs: number) {
    if (!cue) {
      this.release();
      return;
    }

    const targetSeconds = Math.max(0, cueElapsedMs / 1000);
    if (cue.id === this.cueId && this.audio) {
      if (
        targetSeconds < cue.durationMs / 1000 &&
        this.audio.readyState >= HTMLMediaElement.HAVE_METADATA &&
        Math.abs(this.audio.currentTime - targetSeconds) > 0.45
      ) {
        this.audio.currentTime = targetSeconds;
      }
      return;
    }

    this.release();
    this.cueId = cue.id;
    const generation = ++this.generation;
    const audio = new Audio(cue.src);
    audio.preload = "auto";
    audio.volume = Math.max(0, Math.min(1, cue.gain));
    audio.muted = this.muted;
    this.audio = audio;

    const seekToTimeline = () => {
      if (generation !== this.generation || this.audio !== audio) return;
      if (targetSeconds < audio.duration) audio.currentTime = targetSeconds;
    };

    if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) seekToTimeline();
    else audio.addEventListener("loadedmetadata", seekToTimeline, { once: true });

    // Call play immediately. For the first cue this method runs inside the
    // user's click handler, satisfying browser autoplay policy even if media
    // metadata arrives on a later task.
    void audio.play().catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message = error instanceof Error ? error.message : "The browser blocked audio playback.";
      this.onError?.(message);
    });
  }

  stop() {
    this.generation += 1;
    this.release();
  }

  private release() {
    this.cueId = null;
    if (!this.audio) return;
    this.audio.pause();
    this.audio.removeAttribute("src");
    this.audio.load();
    this.audio = null;
  }
}
