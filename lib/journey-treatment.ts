import type { EpicAudioCue } from "@/config/epic-audio-cues";
import type { EpicCuePlayback } from "@/lib/epic-journey";
import type { CamTarget } from "@/lib/journey";

/** One exportable treatment: exactly 90 seconds, chapter 1 through the horizon. */
export const JOURNEY_DURATION_MS = 90_000;

export type JourneyShipTarget = {
  lngLat: [number, number];
  groundLngLat: [number, number];
  liftPx: number;
};

export type JourneyMediaPlayback = {
  src: string;
  poster: string;
  title: string;
  sourceStartS: number;
  sourceEndS: number;
  elapsedMs: number;
};

export type JourneyShot = {
  id: string;
  fromMs: number;
  toMs: number;
  fromChapter: number;
  toChapter: number;
  label: string;
  fact: string;
  fromCam: CamTarget;
  toCam: CamTarget;
  focus?: [number, number];
  ship?: "onigashima-approach" | "onigashima-lift" | "onigashima-land";
  media?: Omit<JourneyMediaPlayback, "elapsedMs">;
};

const WANO: [number, number] = [118.2306, 7.5751];
const EGGHEAD: [number, number] = [149.0991, -0.4304];
const ELBAPH: [number, number] = [154.2701, -7.171];
const SKYPIEA: [number, number] = [-91.1362, 17.0745];
const ALUBARNA: [number, number] = [-120.1992, -0.7873];
const ENIES_LOBBY: [number, number] = [-68.3696, -7.1283];
const ROGER_EXECUTION: [number, number] = [-174, -20];
const BARATIE_DUEL: [number, number] = [-165, -40];
const ARLONG_PARK: [number, number] = [-168, -33.2];

const sea = (zoom = 3.25): CamTarget => ({ zoom, pitch: 18, orbitDegPerSec: 0 });
const stage = (zoom = 6.35, pitch = 50, orbitDegPerSec = 0): CamTarget => ({
  zoom,
  pitch,
  orbitDegPerSec,
});

/**
 * The edit, in wall-clock order. Adjacent shots may jump chapters on purpose:
 * the 654 -> 700 cut is the explicit Punk Hazard skip, not a fast fly-through.
 */
export const JOURNEY_SHOTS: JourneyShot[] = [
  { id: "roger-to-barrel", fromMs: 0, toMs: 3_000, fromChapter: 1, toChapter: 1.8, label: "The voyage begins", fact: "Roger lights the fuse; the camera moves before the first cut.", fromCam: stage(5.8, 50), toCam: stage(6.25, 55), focus: ROGER_EXECUTION },
  { id: "east-blue-launch", fromMs: 3_000, toMs: 5_000, fromChapter: 2, toChapter: 43, label: "East Blue", fact: "A barrel, a promise, and the first crew.", fromCam: stage(5.2, 38), toCam: sea(3.35) },
  { id: "mihawk", fromMs: 5_000, toMs: 8_000, fromChapter: 51, toChapter: 51.8, label: "Baratie — the world's greatest swordsman", fact: "The Zoro beat stays with Mihawk, where it belongs.", fromCam: stage(5.8, 50), toCam: stage(6.25, 55), focus: BARATIE_DUEL },
  { id: "arlong", fromMs: 8_000, toMs: 10_000, fromChapter: 93, toChapter: 93.8, label: "Arlong Park", fact: "The crew walks together and East Blue opens behind them.", fromCam: stage(5.8, 48), toCam: stage(6.25, 54), focus: ARLONG_PARK },
  { id: "reverse-mountain", fromMs: 10_000, toMs: 15_000, fromChapter: 94, toChapter: 102.9, label: "Reverse Mountain", fact: "The current carries the ship into the Grand Line.", fromCam: sea(3.5), toCam: stage(6.2, 58, 3) },
  { id: "arabasta-crossing", fromMs: 15_000, toMs: 18_000, fromChapter: 103, toChapter: 203, label: "Arabasta", fact: "The route races across the desert kingdom toward Alubarna.", fromCam: sea(3.35), toCam: stage(5.9, 50), focus: ALUBARNA },
  { id: "crocodile", fromMs: 18_000, toMs: 21_000, fromChapter: 203, toChapter: 203.8, label: "Luffy vs. Crocodile", fact: "The underground final gets a real stage, not a fly-by.", fromCam: stage(5.9, 50), toCam: stage(6.4, 55), focus: ALUBARNA },
  { id: "jaya", fromMs: 21_000, toMs: 24_000, fromChapter: 204, toChapter: 235, label: "Jaya — aim for the sky", fact: "The camera reaches the stream before the climb begins.", fromCam: stage(5.4, 42), toCam: stage(5.2, 54) },
  { id: "knock-up", fromMs: 24_000, toMs: 29_000, fromChapter: 235, toChapter: 237, label: "Riding the Knock-Up Stream", fact: "Five full seconds on the two chapters that actually carry the ascent.", fromCam: stage(5.2, 56), toCam: stage(5.7, 63) },
  { id: "bell", fromMs: 29_000, toMs: 31_000, fromChapter: 278.8, toChapter: 304, label: "Skypiea — ring the bell", fact: "The city of gold answers from above the White Sea.", fromCam: stage(5.8, 52), toCam: stage(6.25, 55), focus: SKYPIEA },
  { id: "water-seven", fromMs: 31_000, toMs: 34_000, fromChapter: 305, toChapter: 388, label: "Water 7", fact: "The sea train pulls the route toward Enies Lobby.", fromCam: sea(3.4), toCam: stage(5.7, 45) },
  { id: "enies-lobby", fromMs: 34_000, toMs: 39_000, fromChapter: 388, toChapter: 441, label: "Enies Lobby", fact: "The crew declares war and punches through the gates.", fromCam: stage(5.7, 48), toCam: stage(6.35, 54), focus: ENIES_LOBBY },
  { id: "war", fromMs: 39_000, toMs: 45_000, fromChapter: 442, toChapter: 580, label: "Sabaody to Marineford", fact: "The world breaks apart, then the war redraws it.", fromCam: sea(3.5), toCam: stage(5.8, 48, 2) },
  { id: "fishman", fromMs: 45_000, toMs: 50_000, fromChapter: 601, toChapter: 653.9, label: "Beneath the Red Line", fact: "The ship dives instead of teleporting to Fish-Man Island.", fromCam: stage(5.3, 55), toCam: stage(5.8, 62) },
  { id: "new-world", fromMs: 50_000, toMs: 55_000, fromChapter: 700, toChapter: 902, label: "Dressrosa · Zou · Whole Cake", fact: "Punk Hazard is deliberately cut; the route resumes beyond it.", fromCam: sea(3.25), toCam: sea(3.65) },
  { id: "wano-approach", fromMs: 55_000, toMs: 58_000, fromChapter: 903, toChapter: 978, label: "Wano rises ahead", fact: "The camera reaches the country before Onigashima starts to move.", fromCam: sea(3.7), toCam: stage(6.2, 50, 3), focus: WANO, ship: "onigashima-approach" },
  { id: "onigashima-lift", fromMs: 58_000, toMs: 66_000, fromChapter: 978, toChapter: 1039, label: "Onigashima lifts", fact: "The ship rides with the island as the geographic-shift clip advances.", fromCam: stage(6.2, 50, 3), toCam: stage(6.6, 58, 5), focus: WANO, ship: "onigashima-lift" },
  { id: "onigashima-land", fromMs: 66_000, toMs: 70_000, fromChapter: 1039, toChapter: 1109, label: "Back into Wano", fact: "Onigashima settles into the country before the journey moves on.", fromCam: stage(6.6, 58, 5), toCam: stage(6.15, 48, 2), focus: WANO, ship: "onigashima-land" },
  { id: "egghead", fromMs: 70_000, toMs: 76_000, fromChapter: 1109, toChapter: 1131.9, label: "Egghead", fact: "The Future Island loads as a close 3D stage.", fromCam: sea(3.7), toCam: stage(6.45, 50, 4), focus: EGGHEAD },
  { id: "elbaph-1188", fromMs: 76_000, toMs: 86_000, fromChapter: 1132, toChapter: 1188, label: "Elbaph — Chapter 1188", fact: "The verified VOHU breakdown plays over the living Elbaph model.", fromCam: stage(5.9, 45), toCam: stage(6.5, 54, 4), focus: ELBAPH, media: { src: "/art/breakdowns/1188/op1188.mp4", poster: "/art/breakdowns/1188/poster.jpg", title: "Chapter 1188 — VOHU", sourceStartS: 8.27, sourceEndS: 18.27 } },
  { id: "horizon", fromMs: 86_000, toMs: 90_000, fromChapter: 1188, toChapter: 1188, label: "The horizon is still moving", fact: "Ninety seconds. One route. The next chapter remains uncharted.", fromCam: stage(6.1, 48, 2), toCam: { zoom: 2.15, pitch: 12, orbitDegPerSec: 0 } },
];

const AUDIO_WINDOWS = [
  { id: "luffy-pirate-king", atMs: 0 },
  { id: "city-of-gold-bell", atMs: 23_000 },
  { id: "gear-second", atMs: 33_000 },
  { id: "robin-live", atMs: 34_900 },
  { id: "brook-laugh", atMs: 39_000 },
  { id: "law-room", atMs: 42_100 },
  { id: "kuma-scattering", atMs: 44_700 },
  { id: "big-mom-laugh", atMs: 50_000 },
  { id: "wano-theme", atMs: 55_000 },
  { id: "kaido-laugh", atMs: 60_200 },
] as const;

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};
const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

function shipAt(shot: JourneyShot, t: number): JourneyShipTarget | null {
  if (!shot.ship) return null;
  if (shot.ship === "onigashima-approach") {
    return {
      lngLat: [lerp(114.8, WANO[0], t), lerp(5.4, WANO[1], t)],
      groundLngLat: WANO,
      liftPx: 0,
    };
  }
  if (shot.ship === "onigashima-lift") {
    return {
      lngLat: [WANO[0], WANO[1]],
      groundLngLat: WANO,
      liftPx: lerp(8, 104, smooth(t)),
    };
  }
  return {
    lngLat: [WANO[0], WANO[1]],
    groundLngLat: WANO,
    liftPx: lerp(104, 0, smooth(t)),
  };
}

export type JourneyTreatmentSample = {
  chapter: number;
  cam: CamTarget;
  focus: [number, number] | null;
  ship: JourneyShipTarget | null;
  media: JourneyMediaPlayback | null;
  audio: EpicCuePlayback[];
  label: string;
  fact: string;
  shotId: string;
  done: boolean;
};

export function sampleJourneyTreatment(
  elapsedMs: number,
  cues: EpicAudioCue[],
): JourneyTreatmentSample {
  const elapsed = Math.max(0, Math.min(JOURNEY_DURATION_MS, elapsedMs));
  const shot = JOURNEY_SHOTS.find((candidate) => elapsed < candidate.toMs) ?? JOURNEY_SHOTS.at(-1)!;
  const t = smooth((elapsed - shot.fromMs) / Math.max(1, shot.toMs - shot.fromMs));
  const cueById = new Map(cues.map((cue) => [cue.id, cue]));
  const audio = AUDIO_WINDOWS.flatMap(({ id, atMs }) => {
    const cue = cueById.get(id);
    if (!cue || elapsed < atMs || elapsed >= atMs + cue.durationMs) return [];
    return [{ cue, cueElapsedMs: elapsed - atMs }];
  });
  return {
    chapter: lerp(shot.fromChapter, shot.toChapter, t),
    cam: {
      zoom: lerp(shot.fromCam.zoom, shot.toCam.zoom, t),
      pitch: lerp(shot.fromCam.pitch, shot.toCam.pitch, t),
      orbitDegPerSec: lerp(shot.fromCam.orbitDegPerSec, shot.toCam.orbitDegPerSec, t),
    },
    focus: shot.focus ?? null,
    ship: shipAt(shot, t),
    media: shot.media
      ? { ...shot.media, elapsedMs: Math.max(0, elapsed - shot.fromMs) }
      : null,
    audio,
    label: shot.label,
    fact: shot.fact,
    shotId: shot.id,
    done: elapsed >= JOURNEY_DURATION_MS,
  };
}

/** Warm only the small late-island GLBs; the 46 MB 1188 video stays range-loaded. */
export const JOURNEY_PRELOAD_URLS = [
  "/art/runtime/skypiea-knock-up-stream.glb",
  "/art/runtime/wano-onigashima-country-system.glb",
  "/art/runtime/egghead-future-island-system.glb",
  "/art/runtime/elbaph-adam-world-system.glb",
] as const;
