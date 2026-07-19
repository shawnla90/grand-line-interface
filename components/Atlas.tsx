"use client";

/**
 * components/Atlas.tsx — the instrument.
 *
 * ONE PIECE OF STATE: `chapter`. Everything on screen — the map's fog, the crew
 * roster, the arc, the saga, the episode number, the voyage strip, the stats — is
 * a pure derivation of it via worldAtChapter(). Nothing else is stored, because
 * anything else stored is something else that can disagree.
 *
 * THE SWEEP. `chapter` is the target; `swept` eases toward it. Small changes
 * (dragging the slider) snap, so dragging stays 1:1. Big changes (typing 1044,
 * clicking a preset, landing on a shared link) tween over about a second, and
 * because the map re-evaluates its fog against the fractional value every frame,
 * the islands do not blink on — they chart themselves one at a time, west to
 * east, in voyage order. That is the whole demo.
 *
 * THE URL IS THE SHARE MECHANIC. ?ch=1044 is written with history.replaceState,
 * not the Next router: the router would round-trip the server on every slider
 * tick and the instrument would feel like a form. The server still reads the
 * param on a cold load, so a shared link renders correctly on first paint.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  worldAtChapter,
  chapterForEpisode,
  episodeForChapter,
  clampChapter,
  presenceWindowAt,
  type World,
  type Axis,
} from "@/lib/canon";
import { BRAND } from "@/config/brand";
import { focusKey, type Focus, type PresenceLens } from "@/lib/lenses";
import type { BuildLog } from "@/lib/buildlog";
import type { Art } from "@/lib/art";
import { buildJourney, type CamTarget, type JourneyMoment } from "@/lib/journey";
import { buildJourneyStops, SHORT_CUT_SIM_IDS, STORY_JOURNEY_ON } from "@/config/journey-stops";
import {
  ACTIVE_EPIC_AUDIO_CUES,
  EPIC_CROSSFADE_MS,
  EPIC_TRAVEL_BUDGET_MS,
} from "@/config/epic-audio-cues";
import { buildEpicJourneyTimeline } from "@/lib/epic-journey";
import { EpicAudioPlayer } from "@/lib/epic-audio-player";
import { AudioDirector } from "@/lib/audio-director";
import { ANY_STORY_SIMULATIONS_ON } from "@/config/story-simulations";
import WorldMap, { type Projection } from "./WorldMap";
import { RuntimeIslandDirectory } from "./RuntimeIslandDirectory";
import SearchPalette, { type SearchHit } from "./SearchPalette";
import ChapterDock from "./ChapterDock";
import HeroPrompt from "./HeroPrompt";
import Readout from "./Readout";
import CrewRoster from "./CrewRoster";
import IslandDetail from "./IslandDetail";
import Legend from "./Legend";
import Attribution from "./Attribution";

/* -------------------------------------------------------------------------- */
/* the chapter engine — sweep tween + story playback, one rAF at a time        */
/* -------------------------------------------------------------------------- */

export const SPEEDS = [0.5, 1, 2, 4] as const;
export type Speed = (typeof SPEEDS)[number];
/** Chapters per second at 1x. 2 ch/s sails the whole story in ~10 minutes. */
const BASE_CPS = 2;
/** The cinematic journey's total run. ~90s flag-off (the original TikTok
 * cut); with the story layers on the run carries ~10 story/model dwells and
 * two vertical rides, so it stretches to 150s to keep the sea legs pacing. */
const JOURNEY_MS = STORY_JOURNEY_ON ? 150_000 : 90_000;
// The ?cut=short floor: the five-hero roster's weight math lands ~90s on its
// own; the floor only catches a future roster edit that would undershoot.
const SHORT_JOURNEY_MS = 88_000;
// Captured ONCE at module load (the ?record=1 lesson): the app rewrites the
// query string as the reader navigates, so reading location.search at click
// time would lose the flag.
const SHORT_CUT_ARMED =
  typeof window !== "undefined" &&
  new URLSearchParams(window.location.search).get("cut") === "short";

/**
 * One float position (`swept`) eased or sailed toward/through chapters.
 *
 * TWEEN (manual sets): small deltas snap 1:1 (slider drags must not lag),
 * big jumps ease out over ~a second — unchanged from the original sweep.
 *
 * PLAY ("sail the story"): the position advances at speed x BASE_CPS,
 * bypassing the tween entirely, so the reveal is perfectly continuous at any
 * speed. The integer `chapter` stays derived from the float (URL, readout,
 * roster all follow), and playback auto-pauses at the last chapter.
 */
function useChapterEngine(world: World, initial: number) {
  const [chapter, setChapterState] = useState(initial);
  const [swept, setSwept] = useState(initial);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const pos = useRef(initial); // the float truth both loops write
  const raf = useRef<number | null>(null);
  const playingRef = useRef(false);

  // Journey state must be declared before the sail-mode effect below: that
  // effect borrows the same camera channel for story dwells.
  const [journey, setJourney] = useState(false);
  const [journeyLabel, setJourneyLabel] = useState("");
  const [journeyFact, setJourneyFact] = useState("");
  const [epicJourney, setEpicJourney] = useState(false);
  const [epicElapsedMs, setEpicElapsedMs] = useState(0);
  const [epicDurationMs, setEpicDurationMs] = useState(0);
  const [epicCueLabel, setEpicCueLabel] = useState("");
  const [epicMuted, setEpicMuted] = useState(false);
  const [epicAudioError, setEpicAudioError] = useState<string | null>(null);
  const journeyCam = useRef<(CamTarget & { focus: [number, number] | null }) | null>(null);
  const journeyRaf = useRef<number | null>(null);
  const epicAudio = useRef<EpicAudioPlayer | null>(null);

  // tween toward a manually-set target (skipped while playback owns the float)
  useEffect(() => {
    if (playingRef.current) {
      pos.current = chapter; // playback wrote chapter itself; nothing to ease
      return;
    }
    if (raf.current !== null) cancelAnimationFrame(raf.current);

    const from = pos.current;
    const delta = chapter - from;
    const dist = Math.abs(delta);

    // Dragging the slider: stay 1:1 or it feels like lag, not polish.
    if (dist <= 4) {
      pos.current = chapter;
      setSwept(chapter);
      return;
    }

    const duration = Math.min(1500, 260 + dist * 1.15);
    const t0 = performance.now();

    const step = (now: number) => {
      if (playingRef.current) return; // play stole the float mid-tween
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      const v = from + delta * eased;
      pos.current = v;
      setSwept(v);
      raf.current = p < 1 ? requestAnimationFrame(step) : null;
    };

    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
    };
  }, [chapter]);

  // Sail-mode story stops: pause-and-dive at each story beat while playing.
  // Declared above the playback effect that lists it as a dependency.
  const [storyStops, setStoryStops] = useState(STORY_JOURNEY_ON);

  // Scene sound: reader opt-in, cold load ALWAYS silent. The toggle click IS
  // the unlock gesture — the AudioDirector's context is created inside it;
  // scenes that already played stay silent history (no retro-fire).
  const [sceneSound, setSceneSound] = useState(false);
  const toggleSceneSound = useCallback(() => {
    setSceneSound((current) => {
      const next = !current;
      const director = AudioDirector.get();
      if (next) {
        director.unlock();
        director.setMuted(false);
      } else {
        director.setMuted(true);
      }
      return next;
    });
  }, []);

  // playback loop — with STORY STOPS. Sailing past a story chapter shouldn't
  // fly over the story: when the sweep crosses a stop (a 2.5D scene or a 3D
  // spotlight from the same table the cinematic uses), the sail pauses, the
  // camera dives with the journey's own program, the beat plays, and the sail
  // resumes. Default on with the layers; the dock chip turns it off.
  useEffect(() => {
    playingRef.current = playing;
    if (!playing) return;
    if (raf.current !== null) cancelAnimationFrame(raf.current);

    const stops = storyStops ? buildJourneyStops(world) : [];
    let dwellUntil: number | null = null;
    let recoverUntil: number | null = null;
    let dwelling = false;
    // The authored push-in (scene stops only): while holding, the chase's
    // target eases from the base framing toward the climax framing — the
    // damped camera does the rest. Null for stops without one.
    let dwellPush: {
      start: number;
      base: { zoom: number; pitch: number };
      camera: NonNullable<JourneyMoment["camera"]>;
      focus: [number, number] | null;
    } | null = null;
    const smoothstep = (x: number) => {
      const c = Math.max(0, Math.min(1, x));
      return c * c * (3 - 2 * c);
    };

    const endDwell = () => {
      dwelling = false;
      dwellUntil = null;
      recoverUntil = null;
      dwellPush = null;
      journeyCam.current = null;
      setJourney(false);
      setJourneyLabel("");
      setJourneyFact("");
    };

    let last = performance.now();
    const step = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000); // clamp tab-switch gaps
      last = now;
      if (dwellUntil !== null) {
        // Holding at a story stop: the chapter stands, the chase (running in
        // journey mode) frames the stage, the scene plays itself.
        if (now < dwellUntil) {
          if (dwellPush) {
            const { start, base, camera, focus } = dwellPush;
            const s = smoothstep((now - start - camera.atMs) / camera.durationMs);
            journeyCam.current = {
              zoom: base.zoom + ((camera.zoomTo ?? base.zoom) - base.zoom) * s,
              pitch: base.pitch + ((camera.pitchTo ?? base.pitch) - base.pitch) * s,
              orbitDegPerSec: 0,
              focus,
            };
          }
          raf.current = requestAnimationFrame(step);
          return;
        }
        // RECOVERY: don't drop journey mode yet — hand the chase a flat
        // cruising target first, and sail on while it lays the camera back
        // down. (A one-shot easeTo dies under the chase's next jumpTo —
        // measured: the camera stayed pitched 54° into the next sea leg.)
        dwellUntil = null;
        recoverUntil = now + 1600;
        journeyCam.current = { zoom: 3.4, pitch: 0, orbitDegPerSec: 0, focus: null };
        setJourneyLabel("");
        setJourneyFact("");
      }
      if (recoverUntil !== null && now >= recoverUntil) endDwell();
      const prev = pos.current;
      const next = Math.min(world.chapterMax, prev + speed * BASE_CPS * dt);
      const stop = stops.find((s) => prev < s.chapter && s.chapter <= next);
      if (stop) {
        pos.current = stop.chapter;
        setSwept(stop.chapter);
        setChapterState((c) => (c === stop.chapter ? c : stop.chapter));
        dwelling = true;
        // Scene stops dwell for their AUTHORED hold (playback manifest) — the
        // old flat 8000 cut the 8500/9000ms scenes off mid-play.
        dwellUntil = now + (stop.kind === "model" ? 5500 : (stop.holdMs ?? 8000));
        const baseZoom = stop.kind === "model" ? 6.4 : (stop.zoom ?? 5.8);
        const basePitch = stop.kind === "model" ? 48 : (stop.pitch ?? 55);
        journeyCam.current = {
          zoom: baseZoom,
          pitch: basePitch,
          orbitDegPerSec: stop.kind === "model" ? 5 : 0,
          focus: stop.focus ?? null,
        };
        dwellPush =
          stop.kind !== "model" && stop.camera
            ? {
                start: now,
                base: { zoom: baseZoom, pitch: basePitch },
                camera: stop.camera,
                focus: stop.focus ?? null,
              }
            : null;
        // journey=true borrows the whole cinematic apparatus for the dwell:
        // helm lock, hero trail, the damped chase. The sail keeps ownership
        // of playingRef, so resuming is just this rAF continuing.
        setJourney(true);
        setJourneyLabel(stop.label);
        setJourneyFact(stop.fact ?? "");
        raf.current = requestAnimationFrame(step);
        return;
      }
      pos.current = next;
      setSwept(next);
      const fl = Math.max(world.chapterMin, Math.floor(next));
      setChapterState((c) => (c === fl ? c : fl));
      if (next >= world.chapterMax) {
        setPlaying(false);
        return;
      }
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => {
      if (raf.current !== null) cancelAnimationFrame(raf.current);
      // Pausing (or a speed change) mid-dwell must hand the helm back.
      if (dwelling) endDwell();
    };
  }, [playing, speed, storyStops, world]);

  const setChapter = useCallback(
    (ch: number) => {
      // any manual set is the reader taking the helm: playback yields first
      playingRef.current = false;
      setPlaying(false);
      setChapterState(clampChapter(world, ch));
    },
    [world],
  );

  const play = useCallback(() => {
    // sailing off the end restarts the voyage from chapter 1
    if (pos.current >= world.chapterMax) {
      pos.current = world.chapterMin;
      setSwept(world.chapterMin);
      setChapterState(world.chapterMin);
    }
    setPlaying(true);
  }, [world]);
  const pause = useCallback(() => setPlaying(false), []);

  // ─── THE CINEMATIC JOURNEY ────────────────────────────────────────────────
  // A curated ~90s flight, chapter 1 → the end, on its own time→chapter schedule
  // (the 4x speed cap tops out at ~148s, so the sweep speeds cannot reach it).
  // It drives `swept` directly, sets a target `journeyZoom` the map damps toward,
  // and names the current leg for the recording caption.
  /**
   * THE PER-FRAME CAMERA CHANNEL IS A REF, NOT STATE — measured lesson. The
   * first cut pushed zoom/focus through setState every rAF; with ~6 setters a
   * frame React's dev runtime threw "Maximum update depth exceeded" mid-run.
   * The map's chase already reads refs per frame; only the CAPTION (a string
   * that changes a handful of times a run) deserves a re-render.
   */
  const stopJourney = useCallback(() => {
    if (journeyRaf.current !== null) cancelAnimationFrame(journeyRaf.current);
    journeyRaf.current = null;
    playingRef.current = false;
    epicAudio.current?.stop();
    journeyCam.current = null;
    setJourney(false);
    setEpicJourney(false);
    setEpicElapsedMs(0);
    setEpicCueLabel("");
    setJourneyLabel("");
    setJourneyFact("");
  }, []);

  const startJourney = useCallback(() => {
    if (raf.current !== null) cancelAnimationFrame(raf.current);
    if (journeyRaf.current !== null) cancelAnimationFrame(journeyRaf.current);
    epicAudio.current?.stop();
    setPlaying(false);
    setEpicJourney(false);
    setEpicAudioError(null);
    // playingRef true makes the tween effect yield the float to us, exactly as
    // the sail loop does — we own `pos.current`/`swept` for the duration.
    playingRef.current = true;

    // ?cut=short: the phone-length recording cut — the same voyage, the five
    // hero fights only, no 3D dwells, no transits. Scenes still play their
    // full authored cut; the ♫ epic keeps its own full-length timeline.
    const shortCut = SHORT_CUT_ARMED;
    const allStops = buildJourneyStops(world);
    const plan = shortCut
      ? buildJourney(
          world.voyage.waypoints.map((w) => ({ chapter: w.chapter, slug: w.slug, label: w.label })),
          world.chapterMax,
          new Set(),
          // Tighter ocean crossings and heavier stops than the feature cut:
          // five fights carry this ride, the sea between them is connective
          // tissue. momentWeight 380 lands the whole run at ~89s (the run
          // length is 8000 x totalWeight / momentWeight — see buildJourney).
          { travelCapCh: 60, momentWeight: 380 },
          allStops.filter((m) => m.kind === "scene" && m.simId != null && SHORT_CUT_SIM_IDS.has(m.simId)),
          [],
        )
      : buildJourney(
          world.voyage.waypoints.map((w) => ({ chapter: w.chapter, slug: w.slug, label: w.label })),
          world.chapterMax,
          undefined,
          {},
          // Scene moments + model spotlights ride their own flags; both off =
          // today's 90s run, byte for byte.
          allStops,
        );

    // Weights are relative, so an authored holdMs only becomes a wall-clock
    // guarantee once the run is long enough: each moment window must span at
    // least its holdMs. Today's content still fits inside the 150s floor; a
    // future long scene stretches the run instead of silently cutting itself.
    const journeyMs = Math.max(
      shortCut ? SHORT_JOURNEY_MS : JOURNEY_MS,
      ...plan.momentSpans().map((s) => (s.moment.holdMs ?? 0) / Math.max(s.t1 - s.t0, 1e-6)),
    );
    if (process.env.NODE_ENV !== "production") {
      // Dev-only, beside window.__simScenes: the built dwell schedule is
      // otherwise unobservable from a test, and the journey audit would have
      // to infer skipped dwells from camera samples instead of asserting.
      (window as Window & { __journeySpans?: unknown }).__journeySpans = {
        journeyMs,
        spans: plan.momentSpans().map((s) => ({
          label: s.moment.label,
          chapter: s.moment.chapter,
          holdMs: s.moment.holdMs ?? null,
          t0: s.t0,
          t1: s.t1,
          wallMs: Math.round((s.t1 - s.t0) * journeyMs),
        })),
      };
    }

    pos.current = world.chapterMin;
    setSwept(world.chapterMin);
    setChapterState(world.chapterMin);
    setJourney(true);

    const t0 = performance.now();
    let lastPush = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - t0) / journeyMs);
      const ch = plan.chapterAt(t);
      pos.current = ch;
      // React pushes at ~30Hz, not per frame. The CAMERA is full-rate (the
      // chase runs on its own rAF off journeyCam); React only re-renders for
      // the trail/ship/fog, where 30Hz is indistinguishable — and on the
      // late-story legs (every layer revealed, paint at its heaviest) the
      // per-frame double-setState burst is exactly where React's dev runtime
      // still tripped "Maximum update depth exceeded" (measured: 4 times,
      // all during the Egghead leg).
      if (now - lastPush >= 33 || t >= 1) {
        lastPush = now;
        setSwept(ch);
        const fl = Math.max(world.chapterMin, Math.floor(ch));
        setChapterState((c) => (c === fl ? c : fl));
      }
      const moment = plan.momentAt(t);
      journeyCam.current = { ...plan.camAt(t), focus: moment?.focus ?? null };
      // Strings only re-render when they actually CHANGE (see journeyCam note).
      const label = plan.labelAt(t);
      setJourneyLabel((prev) => (prev === label ? prev : label));
      const fact = moment?.fact ?? "";
      setJourneyFact((prev) => (prev === fact ? prev : fact));
      if (t >= 1) {
        stopJourney();
        return;
      }
      journeyRaf.current = requestAnimationFrame(step);
    };
    journeyRaf.current = requestAnimationFrame(step);
  }, [world, stopJourney]);

  const startEpicJourney = useCallback(() => {
    if (raf.current !== null) cancelAnimationFrame(raf.current);
    if (journeyRaf.current !== null) cancelAnimationFrame(journeyRaf.current);
    epicAudio.current?.stop();
    setPlaying(false);
    playingRef.current = true;
    setEpicAudioError(null);
    // The ♫ click is a user gesture — unlock the director here so scene SFX
    // can fire during Epic dwells without a second opt-in.
    AudioDirector.get().unlock();

    const visual = buildJourney(
      world.voyage.waypoints.map((w) => ({ chapter: w.chapter, slug: w.slug, label: w.label })),
      world.chapterMax,
      undefined,
      {},
      buildJourneyStops(world),
    );
    const timeline = buildEpicJourneyTimeline(
      visual,
      ACTIVE_EPIC_AUDIO_CUES,
      EPIC_TRAVEL_BUDGET_MS,
      EPIC_CROSSFADE_MS,
    );

    const audio = new EpicAudioPlayer((message) => setEpicAudioError(message));
    audio.setMuted(epicMuted);
    epicAudio.current = audio;

    pos.current = world.chapterMin;
    setSwept(world.chapterMin);
    setChapterState(world.chapterMin);
    setJourney(true);
    setEpicJourney(true);
    setEpicElapsedMs(0);
    setEpicDurationMs(timeline.durationMs);

    // The first cue begins synchronously inside the click event, which is the
    // browser's required user gesture for audible playback.
    const first = timeline.sampleAt(0);
    audio.sync(first.audio);
    setEpicCueLabel(first.cue?.label ?? "Sailing the Grand Line");
    setJourneyLabel(first.cue?.label ?? visual.labelAt(first.progress));
    setJourneyFact(first.cue?.caption ?? "");

    const t0 = performance.now();
    const auditRate = process.env.NODE_ENV !== "production"
      ? Math.max(1, Number((window as Window & { __epicJourneyRate?: number }).__epicJourneyRate ?? 1))
      : 1;
    let lastPush = 0;
    let lastUiPush = 0;
    const step = (now: number) => {
      const elapsedMs = Math.min(timeline.durationMs, (now - t0) * auditRate);
      const sample = timeline.sampleAt(elapsedMs);
      const ch = visual.chapterAt(sample.progress);
      pos.current = ch;

      if (now - lastPush >= 33 || sample.done) {
        lastPush = now;
        setSwept(ch);
        const fl = Math.max(world.chapterMin, Math.floor(ch));
        setChapterState((current) => (current === fl ? current : fl));
      }

      const moment = visual.momentAt(sample.progress);
      journeyCam.current = { ...visual.camAt(sample.progress), focus: moment?.focus ?? null };
      audio.sync(sample.audio);

      const label = sample.cue?.label ?? visual.labelAt(sample.progress);
      const fact = sample.cue?.caption ?? moment?.fact ?? "";
      setJourneyLabel((current) => (current === label ? current : label));
      setJourneyFact((current) => (current === fact ? current : fact));
      const cueLabel = sample.cue?.label ?? "Sailing the Grand Line";
      setEpicCueLabel((current) => (current === cueLabel ? current : cueLabel));
      if (now - lastUiPush >= 250 || sample.done) {
        lastUiPush = now;
        setEpicElapsedMs(elapsedMs);
      }

      if (sample.done) {
        stopJourney();
        return;
      }
      journeyRaf.current = requestAnimationFrame(step);
    };
    journeyRaf.current = requestAnimationFrame(step);
  }, [epicMuted, stopJourney, world]);

  const toggleEpicMuted = useCallback(() => {
    setEpicMuted((current) => {
      const next = !current;
      epicAudio.current?.setMuted(next);
      // One mute truth: Epic's mute silences the scene SFX world too.
      AudioDirector.get().setMuted(next);
      return next;
    });
  }, []);

  useEffect(() => () => {
    if (journeyRaf.current !== null) cancelAnimationFrame(journeyRaf.current);
    epicAudio.current?.stop();
  }, []);

  // A manual set (or the sail play) cancels the journey — the reader took the helm.
  const setChapterJ = useCallback(
    (ch: number) => {
      stopJourney();
      setChapter(ch);
    },
    [setChapter, stopJourney],
  );

  return {
    chapter, swept, setChapter: setChapterJ, playing, speed, setSpeed, play, pause,
    journey, journeyCam, journeyLabel, journeyFact, startJourney, stopJourney,
    epicJourney, epicElapsedMs, epicDurationMs, epicCueLabel, epicMuted,
    epicAudioError, startEpicJourney, toggleEpicMuted,
    storyStops, setStoryStops,
    sceneSound, toggleSceneSound,
  };
}

/* -------------------------------------------------------------------------- */

type Props = {
  world: World;
  /** Phase 6 official art (slug -> /art/… url). Empty maps => SVG fallbacks. */
  art: Art;
  /** null = a cold visit with no ?ch= — show the hero. */
  initialChapter: number | null;
  initialAxis: Axis;
  /** The presence lens from ?lens= — "crew" on a plain load. */
  initialLens: PresenceLens;
  initialFocus?: Focus | null;
  initialIsland?: string | null;
  /** The shipwright's log — build provenance, rendered from the footer. */
  buildLog?: BuildLog;
};

const DEFAULT_CHAPTER = 1044;

export default function Atlas({
  world, art, initialChapter, initialAxis, initialLens, initialFocus = null,
  initialIsland = null, buildLog,
}: Props) {
  const engine = useChapterEngine(world, initialChapter ?? DEFAULT_CHAPTER);
  const { chapter, swept, playing, speed } = engine;

  // ─── THE RECORD BUTTON (?record=1 only) ────────────────────────────────────
  // Armed by URL because preserveDrawingBuffer must be decided at map
  // construction and costs a buffer swap every frame — never the default.
  // The export is MAP-ONLY (DOM markers, ship included, are not canvas —
  // recorder.ts states the limit); full fidelity stays the OS screen recorder.
  const [recordArmed] = useState(
    () => typeof window !== "undefined" && new URLSearchParams(window.location.search).has("record"),
  );
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<import("@/components/recorder").JourneyRecorder | null>(null);
  const captionRef = useRef({ label: "", fact: "" });
  useEffect(() => {
    captionRef.current = { label: engine.journeyLabel, fact: engine.journeyFact };
  }, [engine.journeyLabel, engine.journeyFact]);

  const startRecordedJourney = useCallback(async () => {
    const canvas = document.querySelector<HTMLCanvasElement>(".maplibregl-canvas");
    if (!canvas) return;
    const { startJourneyRecorder } = await import("@/components/recorder");
    recorderRef.current = startJourneyRecorder({ canvas, getCaption: () => captionRef.current });
    if (!recorderRef.current) return; // MediaRecorder unavailable — journey still plays
    setRecording(true);
    engine.startJourney();
  }, [engine]);

  // The journey ending (naturally or by any cancel path) closes the take.
  useEffect(() => {
    if (engine.journey || !recorderRef.current) return;
    const rec = recorderRef.current;
    recorderRef.current = null;
    void rec.stop().then(() => setRecording(false));
  }, [engine.journey]);
  const [axis, setAxis] = useState<Axis>(initialAxis);
  const [hero, setHero] = useState(initialChapter === null);
  const [projection, setProjection] = useState<Projection>("globe");
  const [offCanon, setOffCanon] = useState(false);
  // The presence lens (Phase 6A). "crew" is Phase 5's who-sails-here coloring;
  // "fruit"/"haki" recolor the same chapter-gated entities by their revealed
  // powers; "off" hides the layer. At ch. 1 every lens shows exactly nothing.
  const [lens, setLens] = useState<PresenceLens>(initialLens);
  // Seeded from ?island= (already fog-checked server-side in app/page.tsx).
  const [selected, setSelectedRaw] = useState<string | null>(initialIsland);
  const [copied, setCopied] = useState(false);
  // Follow-cam: on by default — scrubbing or sailing keeps the ship in view.
  // Selecting an island or dragging the globe is the reader looking elsewhere.
  const [follow, setFollow] = useState(true);
  // The isolate filter + the search palette (Unit: identify & filter).
  const [focus, setFocusRaw] = useState<Focus | null>(initialFocus);
  const [searchOpen, setSearchOpen] = useState(false);
  // Camera target for non-island search hits (crews have no selection slug) and
  // for directory dives (which carry a deeper zoom/pitch to reach the 3D model).
  const [flyTarget, setFlyTarget] = useState<
    { lng: number; lat: number; key: number; zoom?: number; pitch?: number } | null
  >(null);
  const flyKey = useRef(0);
  // Dive into a 3D island from the directory: land past the model's zoom gate,
  // tilted, so grab-and-spin is immediately available. Breaks follow like any
  // deliberate camera takeover.
  const diveTo = useCallback((anchor: [number, number]) => {
    setFollow(false);
    flyKey.current += 1;
    setFlyTarget({ lng: anchor[0], lat: anchor[1], key: flyKey.current, zoom: 6.4, pitch: 45 });
  }, []);

  const setSelected = useCallback((slug: string | null) => {
    setSelectedRaw(slug);
    if (slug !== null) setFollow(false);
  }, []);

  // A fruit/haki focus drags the lens with it so the orb colors MEAN the
  // focused dimension; a crew focus needs presence visible at minimum.
  const setFocus = useCallback((f: Focus | null) => {
    setFocusRaw(f);
    if (!f) return;
    // The lens decides what an orb's COLOR means, so a focus drags it to the
    // matching dimension — isolating Logia users while the orbs are painted by
    // crew would light up the right dots in the wrong language. Status and
    // affiliation have no lens of their own; they only need presence visible.
    if (f.kind === "fruit" || f.kind === "fruit-all") setLens("fruit");
    else if (f.kind === "haki") setLens("haki");
    else setLens((l) => (l === "off" ? "crew" : l));
  }, []);

  // The episode axis carries its own thumb position — see the note in
  // ChapterDock: episode -> chapter is many-to-one and would otherwise snap.
  const [episode, setEpisodeRaw] = useState(
    () => episodeForChapter(world, initialChapter ?? DEFAULT_CHAPTER) ?? world.episodeMax,
  );

  const shown = clampChapter(world, Math.round(swept));
  const at = useMemo(() => worldAtChapter(world, shown), [world, shown]);

  const setChapter = useCallback(
    (ch: number) => {
      const c = clampChapter(world, ch);
      engine.setChapter(c);
      setEpisodeRaw(episodeForChapter(world, c) ?? world.episodeMax);
    },
    [world, engine],
  );

  const setEpisode = useCallback(
    (ep: number) => {
      setEpisodeRaw(ep);
      engine.setChapter(chapterForEpisode(world, ep));
    },
    [world, engine],
  );

  // During either automated run, the episode thumb follows the story. Schedule
  // the mirror update on the next frame so this effect only synchronizes the
  // chapter truth; it never cascades a state write during effect setup.
  useEffect(() => {
    if (!playing && !engine.journey) return;
    const frame = requestAnimationFrame(() => {
      setEpisodeRaw(episodeForChapter(world, chapter) ?? world.episodeMax);
    });
    return () => cancelAnimationFrame(frame);
  }, [playing, engine.journey, chapter, world]);

  /* ------------------------------------------------------------------ url */
  useEffect(() => {
    if (hero) return;
    const t = setTimeout(() => {
      const q = new URLSearchParams();
      q.set("ch", String(chapter));
      if (axis === "episode") q.set("axis", "episode");
      if (lens !== "crew") q.set("lens", lens);
      // The isolation travels with the link: ?ch=700&focus=status:yonko is a
      // shareable claim about the world, not just a bookmark of the chapter.
      if (focus) q.set("focus", focusKey(focus));
      window.history.replaceState(null, "", `?${q.toString()}`);
    }, 180);
    return () => clearTimeout(t);
  }, [chapter, axis, lens, focus, hero]);

  /* -------------------------------------------------------------- keyboard */
  useEffect(() => {
    if (hero) return;
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      // Cmd/Ctrl+K opens search from anywhere (before the guards — it is a chord)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        return;
      }
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowLeft") setChapter(chapter - (e.shiftKey ? 25 : 1));
      else if (e.key === "ArrowRight") setChapter(chapter + (e.shiftKey ? 25 : 1));
      // a focused button owns Space (native activation) — don't double-fire
      else if (e.key === " " && !(el instanceof HTMLButtonElement)) {
        engine.stopJourney();
        (playing ? engine.pause : engine.play)();
      }
      // Esc unwinds in order: filter first, then the selection
      else if (e.key === "Escape") {
        if (focus) setFocus(null);
        else setSelected(null);
      }
      else if (e.key === "/") setSearchOpen(true);
      else if (e.key.toLowerCase() === "g") setProjection((p) => (p === "globe" ? "mercator" : "globe"));
      else if (e.key.toLowerCase() === "f") setFollow((v) => !v);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [chapter, hero, setChapter, playing, engine, focus, setFocus, setSelected]);

  const island = selected ? (world.islands.find((i) => i.slug === selected) ?? null) : null;

  // A search pick: islands select (the existing panel + easeTo); crews and
  // sailors isolate their crew and, when charted right now, fly the camera to
  // the active anchor. Any search fly is the reader looking away — follow off.
  const onSearchPick = useCallback(
    (h: SearchHit) => {
      if (h.kind === "island") {
        setSelected(h.slug);
        return;
      }
      // A stone is not a person: isolate the poneglyph layer and fly to where
      // it currently sits (the hit carries its own resolved coordinate, so a
      // stone that has been moved goes to where it is now, not where it was).
      if (h.kind === "poneglyph") {
        setFocus({ kind: "poneglyph" });
        setFollow(false);
        flyKey.current += 1;
        setFlyTarget({ lng: h.lng, lat: h.lat, key: flyKey.current });
        return;
      }
      // A warlord focuses on themselves (matchesFocus matches e.slug too);
      // a member focuses their whole crew.
      const crewSlug = h.kind === "member" ? h.crewSlug : h.slug;
      setFocus({ kind: "crew", slug: crewSlug });
      const roster = h.kind === "warlord" ? world.presence.characters : world.presence.crews;
      const entity = roster.find((c) => c.slug === crewSlug);
      const w = entity ? presenceWindowAt(entity.windows, shown) : null;
      if (w) {
        setFollow(false);
        flyKey.current += 1;
        setFlyTarget({ lng: w.lng, lat: w.lat, key: flyKey.current });
      }
    },
    [world, shown, setFocus, setSelected],
  );

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard blocked — the URL is in the address bar anyway */
    }
  };

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-abyss">
      <div className="relative min-h-0 flex-1">
        <WorldMap
          world={world}
          art={art}
          chapter={swept}
          projection={projection}
          showOffCanon={offCanon}
          lens={lens}
          selected={selected}
          onSelect={setSelected}
          follow={follow}
          onFollowBreak={() => setFollow(false)}
          focus={focus}
          flyTarget={flyTarget}
          journey={engine.journey}
          journeyCam={engine.journeyCam}
          preserveBuffer={recordArmed}
        />

        <SearchPalette
          world={world}
          shown={shown}
          offCanon={offCanon}
          open={searchOpen}
          onClose={() => setSearchOpen(false)}
          onPick={onSearchPick}
        />

        {/* The journey caption — the current leg's name, for the recording.
            During a story-moment dwell a second line carries the canon fact
            (the event's outcome), so the capture narrates itself. */}
        {engine.journey && engine.journeyLabel && (
          <div className="pointer-events-none absolute top-6 left-1/2 z-20 -translate-x-1/2">
            <div className="max-w-[min(80vw,540px)] rounded-2xl border border-rope/60 bg-ink/85 px-4 py-1.5 text-center font-document text-[13px] italic tracking-wide text-parchment/90 shadow-2xl backdrop-blur">
              <div>{engine.journeyLabel}</div>
              {engine.journeyFact && (
                <div className="mt-0.5 text-[11px] not-italic text-parchment/65">{engine.journeyFact}</div>
              )}
            </div>
          </div>
        )}

        {/* masthead */}
        <div className="pointer-events-none absolute top-0 left-0 z-10 p-5">
          <div className="pointer-events-auto">
            <div className="font-pirate text-[17px] leading-none tracking-[0.06em] text-gold/90">
              {BRAND.name}
            </div>
            <p className="font-document mt-1 max-w-[230px] text-[11px] leading-snug text-muted-2 italic">
              {BRAND.tagline}
            </p>
          </div>
        </div>

        {/* left rail */}
        {!hero && (
          <aside className="gutter dr-fade absolute top-[74px] bottom-4 left-4 z-10 w-[290px] overflow-y-auto rounded-md border border-rope/70 bg-ink/88 shadow-2xl backdrop-blur">
            <Readout at={at} world={world} />
            {island && (
              <IslandDetail
                island={island}
                world={world}
                art={art}
                chapter={at.chapter}
                onClose={() => setSelected(null)}
              />
            )}
            <CrewRoster at={at} world={world} art={art} />

            <div className="px-5 py-4">
              <div className="font-mono text-[9px] uppercase tracking-[0.22em] text-muted-2">
                What this cannot tell you
              </div>
              <ul className="mt-2 space-y-1.5 text-[10px] leading-snug text-muted-2">
                <li>
                  <span className="text-muted">Bounties are as of your chapter</span>, not
                  today&apos;s. The wiki&apos;s single current value would spoil 950 chapters, so
                  the full progression is parsed with the chapter each amount was revealed in —
                  and the ones the wiki never ties to a chapter are dropped rather than shown
                  early.
                </li>
                <li>
                  <span className="text-muted">The anime lags the manga.</span> Chapters{" "}
                  {world.lastAnimatedChapter + 1}–{world.chapterMax} have no episode yet.
                </li>
                <li>
                  <span className="text-muted">The fog is a rendering choice, not encryption.</span>{" "}
                  The dataset ships to your browser; the atlas simply refuses to read ahead for you.
                </li>
              </ul>
            </div>
          </aside>
        )}

        {/* controls + legend */}
        {!hero && (
          <div className="dr-fade absolute top-[74px] right-4 z-10 flex flex-col items-end gap-3">
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={share}
                className="rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2 backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
              >
                {copied ? "copied" : "share ch." + at.chapter}
              </button>
              <button
                type="button"
                onClick={() => setProjection((p) => (p === "globe" ? "mercator" : "globe"))}
                title="Toggle projection (G)"
                className="rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-2 backdrop-blur transition-colors hover:border-gold/60 hover:text-gold"
              >
                {projection === "globe" ? "globe" : "flat"}
              </button>
              <button
                type="button"
                onClick={() => setFollow((v) => !v)}
                title="Camera follows the ship (F)"
                className={[
                  "rounded-sm border bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] backdrop-blur transition-colors",
                  follow
                    ? "border-gold/60 text-gold"
                    : "border-rope text-muted-2 hover:border-gold/60 hover:text-gold",
                ].join(" ")}
              >
                ⌖ follow
              </button>
            </div>

            {/* The 3D-island directory. Only when the runtime assets are on —
                without them a "dive" would land on a flat island, so offering it
                would be a lie. */}
            {process.env.NEXT_PUBLIC_RUNTIME_3D_ASSETS === "1" && (
              <RuntimeIslandDirectory chapter={at.chapter} onDive={diveTo} />
            )}

            <button
              type="button"
              onClick={() => setOffCanon((v) => !v)}
              className={[
                "max-w-[254px] rounded-sm border bg-ink/90 px-2.5 py-1.5 text-left font-mono text-[9px] leading-snug tracking-[0.1em] backdrop-blur transition-colors",
                offCanon
                  ? "border-gold/60 text-gold"
                  : "border-rope text-muted-2 hover:border-rope-2 hover:text-muted",
              ].join(" ")}
            >
              {offCanon ? "◉" : "◯"} off-canon: {world.counts.islandsOffCanon} film / anime / game
              locations. No chapter — they cannot be fogged.
            </button>

            {/* The presence lens. One segmented control: "off" absorbs the old
                who-sails-here toggle; crews/fruit/haki pick what the orb colors
                MEAN. Every lens renders revealed facts only. */}
            <div className="max-w-[254px] rounded-sm border border-rope bg-ink/90 px-2.5 py-1.5 font-mono text-[9px] leading-snug tracking-[0.1em] text-muted-2 backdrop-blur">
              <div className="flex items-center gap-1">
                {(["off", "crew", "fruit", "haki"] as const).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLens(l)}
                    className={[
                      "rounded-sm border px-1.5 py-0.5 uppercase tracking-[0.14em] transition-colors",
                      lens === l
                        ? "border-gold/60 text-gold"
                        : "border-transparent text-muted-2 hover:text-muted",
                    ].join(" ")}
                  >
                    {l === "crew" ? "crews" : l}
                  </button>
                ))}
              </div>
              <div className="mt-1">
                {lens === "off" &&
                  "presence hidden — islands and the voyage only."}
                {lens === "crew" && (
                  <>
                    {/* Not "Warlords" any more, for two reasons: the standalone
                        figures are now admirals and revolutionaries too, and the
                        word itself is a ch. 69 reveal that has no business in a
                        chapter-1 reader's page. */}
                    who sails here: {world.counts.presenceCrews} crews ·{" "}
                    {world.counts.presenceCharacters} figures who sail alone. Chapter-gated,
                    like everything else.
                  </>
                )}
                {lens === "fruit" &&
                  "by devil fruit — orb colors follow the fruit's nature. Revealed fruits only; a fruit is a story reveal with its own chapter."}
                {lens === "haki" &&
                  "by haki — orb colors follow the highest revealed haki. Conqueror > Armament > Observation."}
              </div>
            </div>

            <Legend
              world={world}
              at={at}
              showOffCanon={offCanon}
              lens={lens}
              focus={focus}
              onFocus={setFocus}
            />
          </div>
        )}

        {hero && (
          <HeroPrompt
            world={world}
            axis={axis}
            onAxis={setAxis}
            onCommit={(n) => {
              if (axis === "chapter") setChapter(n);
              else setEpisode(n);
              setHero(false);
            }}
          />
        )}
      </div>

      {!hero && (
        <ChapterDock
          world={world}
          at={at}
          axis={axis}
          onAxis={setAxis}
          onChapter={setChapter}
          episode={episode}
          onEpisode={setEpisode}
          playing={playing}
          speed={speed}
          onPlayPause={() => {
            engine.stopJourney(); // sailing takes the helm from the cinematic run
            if (playing) engine.pause();
            else engine.play();
          }}
          onSpeed={engine.setSpeed}
          journey={engine.journey && !engine.epicJourney}
          onJourney={() => (engine.journey ? engine.stopJourney() : engine.startJourney())}
          epicJourney={engine.epicJourney}
          epicElapsedMs={engine.epicElapsedMs}
          epicDurationMs={engine.epicDurationMs}
          epicCueLabel={engine.epicCueLabel}
          epicMuted={engine.epicMuted}
          epicAudioError={engine.epicAudioError}
          onEpicJourney={() => (engine.epicJourney ? engine.stopJourney() : engine.startEpicJourney())}
          onEpicMuted={engine.toggleEpicMuted}
          recordArmed={recordArmed}
          recording={recording}
          onRecord={() => void startRecordedJourney()}
          storyStops={STORY_JOURNEY_ON ? engine.storyStops : undefined}
          onStoryStops={engine.setStoryStops}
          sceneSound={ANY_STORY_SIMULATIONS_ON ? engine.sceneSound : undefined}
          onSceneSound={engine.toggleSceneSound}
        />
      )}

      <Attribution world={world} buildLog={buildLog} />
    </div>
  );
}
