/**
 * lib/audio-director.ts — the ONE audio authority. PURE, no React, no map.
 *
 * Every sound the app makes routes through this graph or obeys its state:
 *
 *   voice: AudioBufferSourceNode → GainNode → StereoPannerNode
 *     └→ busGain (score | voice | ambience | sfx) → masterGain
 *          └→ DynamicsCompressorNode (conservative limiter) → destination
 *
 * The Epic player's long-form tracks stay HTMLAudioElement-based (measured,
 * working, 26 tracks) — they follow the director's mute and read its score
 * duck level rather than joining the graph; migrating them to
 * MediaElementAudioSourceNode is deliberately deferred.
 *
 * UNLOCK IS A GESTURE. The AudioContext is created/resumed only inside
 * unlock(), which callers invoke from a click handler (the Journey button, the
 * sound chip). Cold load is silent; nothing here ever attempts autoplay.
 * play() before unlock is a deliberate no-op, not an error — a scene that
 * runs before the reader opts into sound is simply a silent scene.
 *
 * DETERMINISM: no randomness, no wall-clock decisions. Gain/pan/rate are
 * authored values from the compiled playback artifact; the only time source
 * is the AudioContext's own clock for ramps.
 */

export type AudioBus = "score" | "voice" | "ambience" | "sfx";

export type PlayOpts = {
  cueId: string;
  src: string;
  bus: AudioBus;
  /** Concurrency family (e.g. "impact-heavy") — caps simultaneous voices. */
  family: string;
  gain: number;
  pan: number;
  playbackRate: number;
  loop?: boolean;
  /** Teardown key — the scene id that owns this voice. */
  ownerId: string;
  /** Max simultaneous voices in this family (from the cue registry). */
  maxVoices: number;
};

type LiveVoice = {
  source: AudioBufferSourceNode;
  gain: GainNode;
  ownerId: string;
  family: string;
  startedAt: number;
  loop: boolean;
};

const BUSES: AudioBus[] = ["score", "voice", "ambience", "sfx"];
const STORAGE_KEY = "dr:audio:v1";
/** Decoded-buffer cache cap. Scene cue sets are ~6-10 short buffers; two
 * scenes plus ambience fit with room to spare. */
const BUFFER_CACHE_MAX = 24;
const VOICE_FADE_S = 0.02;

type Persisted = { muted: boolean; busGains: Partial<Record<AudioBus, number>> };

function readPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as Persisted;
  } catch {
    /* storage unavailable (SSR guard lives in callers; private mode) */
  }
  return { muted: false, busGains: {} };
}

export class AudioDirector {
  private static instance: AudioDirector | null = null;

  static get(): AudioDirector {
    if (!AudioDirector.instance) AudioDirector.instance = new AudioDirector();
    return AudioDirector.instance;
  }

  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private limiter: DynamicsCompressorNode | null = null;
  private busGains = new Map<AudioBus, GainNode>();
  private voices = new Set<LiveVoice>();
  private buffers = new Map<string, AudioBuffer>();
  private bufferOrder: string[] = []; // LRU: oldest first
  private decoding = new Map<string, Promise<AudioBuffer | null>>();

  private muted: boolean;
  private busLevels: Record<AudioBus, number>;
  /** 1 = full score; scene SFX duck it toward e.g. 0.28. Read by the Epic
   * player (element-based) so both worlds duck as one. */
  private scoreDuck = 1;
  private mutedListeners = new Set<(muted: boolean) => void>();

  private constructor() {
    const persisted = typeof window === "undefined" ? { muted: false, busGains: {} } : readPersisted();
    this.muted = persisted.muted;
    this.busLevels = { score: 1, voice: 1, ambience: 1, sfx: 1 };
    for (const bus of BUSES) {
      const level = persisted.busGains[bus];
      if (typeof level === "number" && level >= 0 && level <= 1) this.busLevels[bus] = level;
    }
  }

  /** True once unlock() has run inside a user gesture. */
  get unlocked(): boolean {
    return this.ctx !== null && this.ctx.state === "running";
  }

  /**
   * Create/resume the AudioContext. MUST be called from a user-gesture
   * handler; returns whether the context is running. Safe to call repeatedly.
   */
  unlock(): boolean {
    if (typeof window === "undefined") return false;
    if (!this.ctx) {
      const Ctor = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return false;
      this.ctx = new Ctor();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.muted ? 0 : 1;
      // Conservative limiter: inaudible at authored levels, catches a pileup.
      this.limiter = this.ctx.createDynamicsCompressor();
      this.limiter.threshold.value = -6;
      this.limiter.knee.value = 6;
      this.limiter.ratio.value = 12;
      this.limiter.attack.value = 0.003;
      this.limiter.release.value = 0.25;
      this.master.connect(this.limiter);
      this.limiter.connect(this.ctx.destination);
      for (const bus of BUSES) {
        const g = this.ctx.createGain();
        g.gain.value = this.busLevels[bus];
        g.connect(this.master);
        this.busGains.set(bus, g);
      }
    }
    if (this.ctx.state === "suspended") void this.ctx.resume();
    return this.ctx.state === "running";
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
    if (this.master && this.ctx) {
      this.master.gain.setTargetAtTime(muted ? 0 : 1, this.ctx.currentTime, 0.02);
    }
    this.persist();
    for (const listener of this.mutedListeners) listener(muted);
  }

  get isMuted(): boolean {
    return this.muted;
  }

  /** Subscribe to mute changes (the Epic player and UI chips both follow). */
  onMutedChange(listener: (muted: boolean) => void): () => void {
    this.mutedListeners.add(listener);
    return () => this.mutedListeners.delete(listener);
  }

  setBusGain(bus: AudioBus, level: number): void {
    const clamped = Math.max(0, Math.min(1, level));
    this.busLevels[bus] = clamped;
    const g = this.busGains.get(bus);
    if (g && this.ctx) g.gain.setTargetAtTime(clamped, this.ctx.currentTime, 0.02);
    this.persist();
  }

  /**
   * Duck the score bus toward `level` (0..1 of its set gain) over ~rampMs.
   * The element-based Epic beds multiply their own volume by scoreDuckLevel,
   * so one duck state governs both audio worlds.
   */
  duckScore(level: number, rampMs: number): void {
    const clamped = Math.max(0, Math.min(1, level));
    this.scoreDuck = clamped;
    const g = this.busGains.get("score");
    if (g && this.ctx) {
      g.gain.setTargetAtTime(this.busLevels.score * clamped, this.ctx.currentTime, Math.max(0.01, rampMs / 1000 / 3));
    }
  }

  get scoreDuckLevel(): number {
    return this.scoreDuck;
  }

  /** Decode into the LRU cache. Resolves null (never throws) on fetch/decode
   * failure — a missing sound must never take the scene down with it. */
  async preload(cueId: string, src: string): Promise<AudioBuffer | null> {
    if (!this.ctx) return null;
    const cached = this.buffers.get(cueId);
    if (cached) {
      this.touch(cueId);
      return cached;
    }
    const inFlight = this.decoding.get(cueId);
    if (inFlight) return inFlight;
    const job = (async () => {
      try {
        const res = await fetch(src);
        if (!res.ok) return null;
        const buffer = await this.ctx!.decodeAudioData(await res.arrayBuffer());
        this.buffers.set(cueId, buffer);
        this.touch(cueId);
        this.evictOverflow();
        return buffer;
      } catch {
        return null;
      } finally {
        this.decoding.delete(cueId);
      }
    })();
    this.decoding.set(cueId, job);
    return job;
  }

  /**
   * Fire one voice. No-op when locked, muted, or the buffer never decoded.
   * Enforces the family voice cap by fading the OLDEST family voice out.
   */
  play(opts: PlayOpts): void {
    if (!this.ctx || !this.unlocked || this.muted) return;
    const buffer = this.buffers.get(opts.cueId);
    if (!buffer) return;
    const familyVoices = [...this.voices].filter((v) => v.family === opts.family);
    if (familyVoices.length >= Math.max(1, opts.maxVoices)) {
      const oldest = familyVoices.reduce((a, b) => (a.startedAt <= b.startedAt ? a : b));
      this.release(oldest, VOICE_FADE_S);
    }
    const bus = this.busGains.get(opts.bus);
    if (!bus) return;
    const source = this.ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = Boolean(opts.loop);
    source.playbackRate.value = opts.playbackRate;
    const gain = this.ctx.createGain();
    gain.gain.value = opts.gain;
    const pan = this.ctx.createStereoPanner();
    pan.pan.value = opts.pan;
    source.connect(gain);
    gain.connect(pan);
    pan.connect(bus);
    const voice: LiveVoice = { source, gain, ownerId: opts.ownerId, family: opts.family, startedAt: this.ctx.currentTime, loop: Boolean(opts.loop) };
    this.voices.add(voice);
    source.onended = () => {
      this.voices.delete(voice);
      try {
        source.disconnect();
        gain.disconnect();
        pan.disconnect();
      } catch {
        /* already gone */
      }
    };
    source.start();
  }

  /** Fade out and release voices a scene owns (unmount, scrub, teardown).
   * `onlyLoops` is the tableau case: ambience/fire loops stop with the
   * animation, but a one-shot mid-tail (a voice line, a collapse) finishes —
   * cutting a sentence at the final frame is worse than a short overhang. */
  stopOwner(ownerId: string, fadeMs: number, opts?: { onlyLoops?: boolean }): void {
    for (const voice of [...this.voices]) {
      if (voice.ownerId !== ownerId) continue;
      if (opts?.onlyLoops && !voice.loop) continue;
      this.release(voice, Math.max(0.005, fadeMs / 1000));
    }
    if (![...this.voices].some((v) => v.ownerId !== ownerId)) this.duckScore(1, fadeMs);
  }

  /** Live voice count — the dev hook and audits read this. */
  get liveVoiceCount(): number {
    return this.voices.size;
  }

  /** Drop decoded buffers not in `keep` (pack switch, scene change). */
  evictExcept(keep: Set<string>): void {
    for (const cueId of [...this.buffers.keys()]) {
      if (!keep.has(cueId)) {
        this.buffers.delete(cueId);
        this.bufferOrder = this.bufferOrder.filter((id) => id !== cueId);
      }
    }
  }

  private release(voice: LiveVoice, fadeS: number): void {
    if (!this.ctx) return;
    this.voices.delete(voice);
    try {
      voice.gain.gain.setTargetAtTime(0, this.ctx.currentTime, fadeS / 3);
      voice.source.stop(this.ctx.currentTime + fadeS);
    } catch {
      /* stopping a finished source throws; it is already silent */
    }
  }

  private touch(cueId: string): void {
    this.bufferOrder = this.bufferOrder.filter((id) => id !== cueId);
    this.bufferOrder.push(cueId);
  }

  private evictOverflow(): void {
    while (this.bufferOrder.length > BUFFER_CACHE_MAX) {
      const oldest = this.bufferOrder.shift();
      if (oldest) this.buffers.delete(oldest);
    }
  }

  private persist(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ muted: this.muted, busGains: this.busLevels }));
    } catch {
      /* private mode / SSR — persistence is a nicety, not a contract */
    }
  }
}
