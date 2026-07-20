import type { EpicAudioCue } from "@/config/epic-audio-cues";
import type { EpicCuePlayback } from "@/lib/epic-journey";
import type { CamTarget } from "@/lib/journey";

/** The single exportable trailer cut: chapter 1 through the present horizon. */
export const JOURNEY_DURATION_MS = 90_000;

export type JourneyScenePlayback = {
  sceneId: string;
  timeMs: number;
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
  /** Editorial time-remap: show the authored scene's complete action inside its trailer slot. */
  scene?: { id: string; durationMs: number };
  /** The map-marker ship must not impersonate a vessel attached to a 3D island. */
  hideShip?: boolean;
};

const ROGER_EXECUTION: [number, number] = [-174, -20];
const ALVIDA: [number, number] = [-136, -56];
const ORANGE_TOWN: [number, number] = [-152, -45];
const SYRUP_VILLAGE: [number, number] = [-160, -52];
const BARATIE_DUEL: [number, number] = [-165, -40];
const NAMI_HELP: [number, number] = [-167.6, -32.4];
const ARLONG_PARK: [number, number] = [-168, -33.2];
const REVERSE_MOUNTAIN: [number, number] = [-179, -2];
const ALUBARNA: [number, number] = [-120.1992, -0.7873];
const SKYPIEA: [number, number] = [-91.1362, 17.0745];
const ENIES_LOBBY: [number, number] = [-68.3696, -7.1283];
const SABAODY: [number, number] = [-51.2008, 6.2035];
const MARINEFORD: [number, number] = [-92.4053, 11.8445];
const FISHMAN_DESCENT: [number, number] = [-48.2843, 2.9];
const PUNK_HAZARD: [number, number] = [18.7035, -5.2418];
const DRESSROSA: [number, number] = [42.463, 7.6766];
const ZOU: [number, number] = [53.1494, -4.3461];
const WHOLE_CAKE: [number, number] = [72.2778, -2.819];
const WANO: [number, number] = [118.2306, 7.5751];
const EGGHEAD: [number, number] = [149.0991, -0.4304];
const ELBAPH: [number, number] = [154.2701, -7.171];

const stage = (zoom = 6.35, pitch = 50, orbitDegPerSec = 0): CamTarget => ({
  zoom,
  pitch,
  orbitDegPerSec,
});

const scene = (
  id: string,
  fromMs: number,
  toMs: number,
  chapter: number,
  label: string,
  fact: string,
  focus: [number, number],
  durationMs: number,
  zoom = 6.35,
): JourneyShot => ({
  id,
  fromMs,
  toMs,
  fromChapter: chapter,
  toChapter: chapter,
  label,
  fact,
  fromCam: stage(zoom - 0.25, 48),
  toCam: stage(zoom, 55, 2),
  focus,
  scene: { id, durationMs },
});

/**
 * A trailer edit, not a chapter counter. Every authored scene is held on its
 * actual gate and time-remapped through its complete animation; every large
 * geographic model gets its own readable shot instead of being crossed in a
 * multi-hundred-chapter blur.
 */
export const JOURNEY_SHOTS: JourneyShot[] = [
  scene("roger-execution-prologue", 0, 3_500, 1, "Gold Roger — the age begins", "The execution opens the route, then the cut leaves Loguetown.", ROGER_EXECUTION, 8_000, 6.4),
  scene("luffy-punches-alvida", 3_500, 6_000, 2, "A barrel in East Blue", "Luffy arrives, makes the promise, and throws the first punch.", ALVIDA, 7_000, 6.35),
  scene("orange-town-luffy-vs-buggy", 6_000, 8_500, 20, "Orange Town", "The first pirate showdown plays through instead of becoming a fly-by.", ORANGE_TOWN, 8_000),
  scene("syrup-village-luffy-vs-kuro", 8_500, 11_000, 40, "Syrup Village", "Kuro's final rush gets a complete visual beat.", SYRUP_VILLAGE, 8_000),
  scene("baratie-zoro-vs-mihawk", 11_000, 14_500, 51, "Baratie — Zoro vs. Mihawk", "Zoro's supplied line stays on the duel it belongs to.", BARATIE_DUEL, 8_000, 6.45),
  scene("nami-asks-for-help", 14_500, 17_000, 81, "Nami asks for help", "The quiet turn lands before the crew answers.", NAMI_HELP, 8_500),
  scene("arlong-park-final-clash", 17_000, 20_500, 93, "Arlong Park", "East Blue closes on the authored final clash.", ARLONG_PARK, 8_500, 6.45),
  { id: "reverse-mountain", fromMs: 20_500, toMs: 24_500, fromChapter: 101, toChapter: 102, label: "Reverse Mountain", fact: "The current carries the Going Merry up and into the Grand Line.", fromCam: stage(6.2, 54), toCam: stage(6.7, 62, 3), focus: REVERSE_MOUNTAIN },
  scene("arabasta-luffy-vs-crocodile-final", 24_500, 28_500, 203, "Arabasta — the final round", "The Alubarna battle advances through the complete authored action.", ALUBARNA, 11_500, 6.5),
  { id: "jaya-approach", fromMs: 28_500, toMs: 31_000, fromChapter: 204, toChapter: 235, label: "Jaya — aim for the sky", fact: "The camera reaches the stream before the climb begins.", fromCam: stage(5.1, 42), toCam: stage(5.5, 54) },
  { id: "knock-up-stream", fromMs: 31_000, toMs: 36_000, fromChapter: 235, toChapter: 237, label: "Riding the Knock-Up Stream", fact: "Five full seconds climb the route; this is not a chapter jump.", fromCam: stage(5.5, 56), toCam: stage(6.15, 64, 3) },
  scene("skypiea-luffy-vs-enel", 36_000, 40_000, 279, "Skypiea — ring the bell", "The bell cue lands inside the Enel sequence above the White Sea.", SKYPIEA, 11_200, 6.45),
  scene("enies-lobby-luffy-vs-rob-lucci", 40_000, 44_000, 418, "Enies Lobby", "The Lucci sequence gets a full editorial pass through its authored action.", ENIES_LOBBY, 12_800, 6.5),
  scene("sabaody-luffy-punches-charloss", 44_000, 47_000, 502, "Sabaody", "The auction-house impact reads before the world breaks apart.", SABAODY, 9_800, 6.45),
  { id: "marineford", fromMs: 47_000, toMs: 50_000, fromChapter: 522, toChapter: 525, label: "Marineford", fact: "The government sea system receives a dedicated war-stage shot.", fromCam: stage(6.1, 48), toCam: stage(6.7, 57, 3), focus: MARINEFORD },
  { id: "fishman-descent", fromMs: 50_000, toMs: 54_000, fromChapter: 602, toChapter: 607, label: "Beneath the Red Line", fact: "The Sunny dives through the actual descent rather than teleporting.", fromCam: stage(5.5, 54), toCam: stage(6.5, 64, 2), focus: FISHMAN_DESCENT },
  { id: "punk-hazard", fromMs: 54_000, toMs: 59_000, fromChapter: 655, toChapter: 664, label: "Punk Hazard", fact: "Five seconds reveal the split fire-and-ice island all the way to its safe full scene.", fromCam: stage(6.2, 50), toCam: stage(7.0, 58, 4), focus: PUNK_HAZARD },
  { id: "dressrosa", fromMs: 59_000, toMs: 62_000, fromChapter: 682, toChapter: 738, label: "Dressrosa · Green Bit", fact: "The living geography gets its own close pass.", fromCam: stage(6.1, 48), toCam: stage(6.75, 56, 3), focus: DRESSROSA },
  { id: "zou", fromMs: 62_000, toMs: 65_000, fromChapter: 795, toChapter: 804, label: "Zou", fact: "Zunesha fills the frame before the route moves on.", fromCam: stage(6.0, 48), toCam: stage(6.75, 57, 3), focus: ZOU },
  { id: "whole-cake", fromMs: 65_000, toMs: 68_000, fromChapter: 824, toChapter: 831, label: "Totto Land", fact: "Whole Cake's food geography receives a readable stage.", fromCam: stage(6.0, 48), toCam: stage(6.7, 56, 3), focus: WHOLE_CAKE },
  { id: "wano-approach", fromMs: 68_000, toMs: 72_000, fromChapter: 903, toChapter: 978, label: "Wano rises ahead", fact: "The whole country establishes before Onigashima moves.", fromCam: stage(5.8, 46), toCam: stage(6.65, 54, 2), focus: WANO },
  { id: "onigashima-flight", fromMs: 72_000, toMs: 80_000, fromChapter: 997, toChapter: 1109, label: "Onigashima takes flight", fact: "The clean Wano frame holds while the real geographic-shift clip lifts and settles the skull island.", fromCam: stage(7.1, 56, 1), toCam: stage(7.2, 58, 1), focus: WANO, hideShip: true },
  { id: "onigashima-landing", fromMs: 80_000, toMs: 83_000, fromChapter: 1109, toChapter: 1109, label: "Onigashima returns to Wano", fact: "The country, not a reversed DOM boat, resolves the landing.", fromCam: stage(7.35, 58, 2), toCam: stage(6.7, 52, 1), focus: WANO, hideShip: true },
  { id: "egghead", fromMs: 83_000, toMs: 86_000, fromChapter: 1110, toChapter: 1131, label: "Egghead", fact: "Future Island loads as a close 3D stage.", fromCam: stage(6.0, 46), toCam: stage(6.8, 55, 3), focus: EGGHEAD },
  { id: "elbaph", fromMs: 86_000, toMs: 89_000, fromChapter: 1132, toChapter: 1188, label: "Elbaph", fact: "The living Adam-world model closes the voyage—without a vertical video pasted over it.", fromCam: stage(6.0, 46), toCam: stage(6.8, 56, 3), focus: ELBAPH },
  { id: "horizon", fromMs: 89_000, toMs: 90_000, fromChapter: 1188, toChapter: 1188, label: "The horizon is still moving", fact: "Ninety seconds. One route. The next chapter remains uncharted.", fromCam: stage(6.2, 48), toCam: { zoom: 3.2, pitch: 18, orbitDegPerSec: 0 }, focus: ELBAPH },
];

const AUDIO_WINDOWS = [
  { id: "luffy-pirate-king", atMs: 0 },
  { id: "city-of-gold-bell", atMs: 31_000 },
  { id: "gear-second", atMs: 40_000 },
  { id: "robin-live", atMs: 41_800 },
  { id: "kuma-scattering", atMs: 44_500 },
  { id: "big-mom-laugh", atMs: 65_000 },
  { id: "wano-theme", atMs: 68_000 },
  { id: "kaido-laugh", atMs: 72_000 },
] as const;

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};
const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

export type JourneyTreatmentSample = {
  chapter: number;
  cam: CamTarget;
  focus: [number, number] | null;
  hideShip: boolean;
  scene: JourneyScenePlayback | null;
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
  const rawT = clamp01((elapsed - shot.fromMs) / Math.max(1, shot.toMs - shot.fromMs));
  const cameraT = smooth(rawT);
  const cueById = new Map(cues.map((cue) => [cue.id, cue]));
  const audio = AUDIO_WINDOWS.flatMap(({ id, atMs }) => {
    const cue = cueById.get(id);
    if (!cue || elapsed < atMs || elapsed >= atMs + cue.durationMs) return [];
    return [{ cue, cueElapsedMs: elapsed - atMs }];
  });
  return {
    chapter: lerp(shot.fromChapter, shot.toChapter, cameraT),
    cam: {
      zoom: lerp(shot.fromCam.zoom, shot.toCam.zoom, cameraT),
      pitch: lerp(shot.fromCam.pitch, shot.toCam.pitch, cameraT),
      orbitDegPerSec: lerp(shot.fromCam.orbitDegPerSec, shot.toCam.orbitDegPerSec, cameraT),
    },
    focus: shot.focus ?? null,
    hideShip: Boolean(shot.hideShip),
    scene: shot.scene
      ? { sceneId: shot.scene.id, timeMs: Math.min(shot.scene.durationMs, rawT * shot.scene.durationMs) }
      : null,
    audio,
    label: shot.label,
    fact: shot.fact,
    shotId: shot.id,
    done: elapsed >= JOURNEY_DURATION_MS,
  };
}

/** Warm the geographic stages that the camera must reveal on a fixed clock. */
export const JOURNEY_PRELOAD_URLS = [
  "/art/east-blue-2d/alvida/atlas.png",
  "/art/east-blue-2d/arlong/atlas.png",
  "/art/east-blue-2d/buggy/atlas.png",
  "/art/east-blue-2d/captain-kuro/atlas.png",
  "/art/east-blue-2d/dracule-mihawk/atlas.png",
  "/art/east-blue-2d/gol-d-roger/atlas.png",
  "/art/east-blue-2d/monkey-d-luffy/atlas.png",
  "/art/east-blue-2d/nami/atlas.png",
  "/art/east-blue-2d/roronoa-zoro/atlas.png",
  "/art/east-blue-2d/sanji/atlas.png",
  "/art/east-blue-2d/usopp/atlas.png",
  "/art/story-simulations/arabasta-saga-2d-v1/crocodile-arabasta-final/atlas.png",
  "/art/story-simulations/arabasta-saga-2d-v1/monkey-d-luffy-crocodile-final/atlas.png",
  "/art/story-simulations/skypiea-saga-2d-v1/enel-skypiea/atlas.png",
  "/art/story-simulations/skypiea-saga-2d-v1/monkey-d-luffy-skypiea-enel/atlas.png",
  "/art/story-simulations/enies-lobby-saga-2d-v1/monkey-d-luffy-enies-lobby-lucci/atlas.png",
  "/art/story-simulations/enies-lobby-saga-2d-v1/rob-lucci-enies-lobby/atlas.png",
  "/art/story-simulations/sabaody-saga-2d-v1/monkey-d-luffy-sabaody-auction/atlas.png",
  "/art/story-simulations/sabaody-saga-2d-v1/octy-sabaody-auction/atlas.png",
  "/art/story-simulations/sabaody-saga-2d-v1/saint-charloss-sabaody-auction/atlas.png",
  "/art/runtime/reverse-mountain-twin-cape-voyage.glb",
  "/art/runtime/skypiea-knock-up-stream.glb",
  "/art/runtime/world-government-tarai-system.glb",
  "/art/runtime/fish-man-red-line-descent.glb",
  "/art/runtime/punk-hazard-geographic-system.glb",
  "/art/runtime/dressrosa-green-bit.glb",
  "/art/runtime/zou-zunesha.glb",
  "/art/runtime/totto-land-food-geography.glb",
  "/art/runtime/wano-onigashima-country-system.glb",
  "/art/runtime/egghead-future-island-system.glb",
  "/art/runtime/elbaph-adam-world-system.glb",
] as const;
