/**
 * config/journey-stops.ts — everything the cinematic journey stops for.
 *
 * Two families, one mechanism (the JourneyMoment dwell):
 *   - SCENE stops: 2.5D story simulations. Which scenes are stops, how long
 *     each dwell holds, and its camera live in the compiled playback artifact
 *     (canon/story_scene_playback.json → data/generated/story_scene_playback.json)
 *     — data, not code. A scene enters the journey only when its pack is
 *     allowlisted AND its row says journey.enabled. Labels and facts still
 *     resolve from live canon events at build time, never from the manifest.
 *   - MODEL spotlights: 3D models whose anchors the voyage line never
 *     touches, so the waypoint-keyed deep list structurally cannot visit
 *     them — Marineford has existed on this chart since the world-government
 *     triangle shipped, and the journey simply never looked at it. These ride
 *     the RUNTIME_3D flag and use the directory-dive camera with orbit.
 *
 * Chapters are chosen so every component the camera sees is already revealed
 * (the GLB's own node gates keep withholding the rest): Enies Lobby reveals
 * ch358 and the Gates ch376, so the ch430 visit shows the judicial island era;
 * Impel Down (525) and the tarai current (522) complete the triangle by the
 * ch552 war visit. Spoiler math is enforced by scripts/audit_journey.py.
 */

import type { JourneyMoment } from "@/lib/journey";
import { ANY_STORY_SIMULATIONS_ON, ENABLED_STORY_PACKS, type StoryPackId } from "@/config/story-simulations";
import { loadScenePlayback } from "@/lib/scene-playback";
import playbackRaw from "@/data/generated/story_scene_playback.json";

const RUNTIME_3D_ON = process.env.NEXT_PUBLIC_RUNTIME_3D_ASSETS === "1";

/** True when the journey carries story/model stops at all — the 150s cut. */
export const STORY_JOURNEY_ON = ANY_STORY_SIMULATIONS_ON || RUNTIME_3D_ON;

/** Anchors come from data/generated/runtime_assets.json (the models' own
 * declared positions) — hand-carried here because this file must stay tiny
 * and the artifact is 60KB. If a model's anchor moves, move it here too. */
const MODEL_SPOTLIGHTS: JourneyMoment[] = [
  { chapter: 102, kind: "model", label: "First contact — an unidentified giant whale", fact: "The Grand Line entrance is blocked by something larger than the ship.", focus: [-179, -2], holdMs: 7600 },
  { chapter: 103, kind: "model", label: "Twin Cape — Laboon and Crocus", fact: "Inside the whale, the crew meets the lighthouse keeper and learns Laboon's story.", focus: [-179, -2], holdMs: 7000 },
  { chapter: 104, kind: "model", label: "The promise to Laboon", fact: "Luffy promises a rematch after the crew circles the Grand Line.", focus: [-179, -2], holdMs: 6800 },
  { chapter: 105, kind: "model", label: "Log Pose — departure for Whisky Peak", fact: "Crocus points the crew toward its first Grand Line route.", focus: [-179, -2], holdMs: 7200 },
  { chapter: 105, kind: "model", label: "Whisky Peak", fact: "The first Grand Line welcome — too warm to be true.", focus: [-121.5765, -5.8639] },
  { chapter: 430, kind: "model", label: "Enies Lobby & the Gates of Justice", fact: "The judicial island, where the world's law meets the sea.", focus: [-92.4053, 11.8445] },
  { chapter: 490, kind: "model", label: "Mary Geoise — the Red Line's summit", fact: "The holy land above the world, where the Celestial Dragons rule.", focus: [-2.7363, -9.3782] },
  { chapter: 516, kind: "model", label: "Amazon Lily", fact: "Kuja island — the empress's home sea.", focus: [165.1452, 12.0706] },
  { chapter: 552, kind: "model", label: "Marineford", fact: "The Navy's fortress, where the war for the era was fought.", focus: [-92.4053, 11.8445] },
  // Endgame geography uses the complete replacement systems, not Wano's old
  // waterfall-card study. These anchors and safe chapters are the signed
  // runtime contracts; holding here makes the new islands part of Journey and
  // ordinary Play instead of discoverable only through the asset directory.
  { chapter: 978, kind: "model", label: "Wano & Onigashima — the skull fortress", fact: "The raid reaches the fortress island off Wano's coast.", focus: [118.2306, 7.5751] },
  { chapter: 997, kind: "model", label: "Onigashima takes flight", fact: "The fortress island rises and begins moving toward the Flower Capital.", focus: [118.2306, 7.5751] },
  { chapter: 1066, kind: "model", label: "Egghead — island of the future", fact: "The voyage reaches Vegapunk's vertically layered research island.", focus: [149.0991, -0.4304] },
  { chapter: 1125, kind: "model", label: "Elbaph — beneath Treasure Tree Adam", fact: "The voyage reaches the land of the giants beneath the world tree.", focus: [154.2701, -7.171] },
];

/** The events shape the stops builder reads — duck-typed on the fields it
 * touches so this stays importable without lib/canon (the old
 * buildEastBlueMoments posture, kept). */
type WorldEvents = {
  events: { slug: string; name: string; outcome: string; lng: number; lat: number; occurredChapter: number }[];
};

/** The compiled treatment, parsed once at module load. The artifact is a few
 * KB of scene ids and dwell numbers — the same spoiler surface as the
 * spotlight table above; the packs' atlases stay behind their dynamic import. */
const PLAYBACK = loadScenePlayback(playbackRaw);

/** Scene moments from the playback manifest, in the world the reader has. */
function buildStoryMoments(world: WorldEvents): JourneyMoment[] {
  const bySlug = new Map(world.events.map((e) => [e.slug, e]));
  const moments: JourneyMoment[] = [];
  for (const row of PLAYBACK.scenes) {
    if (!row.journey.enabled) continue;
    if (!ENABLED_STORY_PACKS.has(row.pack_id as StoryPackId)) continue;
    const ev = row.event ? bySlug.get(row.event) : undefined;
    // A missing event row means the canon layer changed under us — skip the
    // moment rather than caption with nothing; the journey still runs. An
    // event AFTER the scene's chapter would caption a spoiler; same skip
    // (the compiler hard-fails this, the runtime guard is defense in depth).
    if (!ev || ev.occurredChapter > row.chapter) continue;
    moments.push({
      chapter: row.chapter,
      kind: "scene",
      label: row.label_override ?? ev.name,
      fact: ev.outcome,
      // The stage is where the dwell looks — the signed pack's own anchor,
      // not the event's coordinate (the Conomi/vows receipts, generalized).
      focus: [row.anchor.lng, row.anchor.lat],
      simId: row.scene_id,
      holdMs: row.journey.hold_ms,
      zoom: row.journey.zoom,
      pitch: row.journey.pitch,
      ...(row.journey.camera
        ? {
            camera: {
              ...(row.journey.camera.zoom_to != null ? { zoomTo: row.journey.camera.zoom_to } : {}),
              ...(row.journey.camera.pitch_to != null ? { pitchTo: row.journey.camera.pitch_to } : {}),
              atMs: row.journey.camera.at_ms,
              durationMs: row.journey.camera.duration_ms,
            },
          }
        : {}),
    });
  }
  return moments;
}

/** All the stops the journey should make, in the world the reader has. */
export function buildJourneyStops(world: WorldEvents): JourneyMoment[] {
  const stops: JourneyMoment[] = [];
  if (ANY_STORY_SIMULATIONS_ON) stops.push(...buildStoryMoments(world));
  if (RUNTIME_3D_ON) stops.push(...MODEL_SPOTLIGHTS);
  return stops.sort((a, b) => a.chapter - b.chapter);
}

/**
 * The ?cut=short roster — the whole voyage in ~90 seconds, for a phone-length
 * recording. One hero fight per saga (curated, not derived — art direction):
 * their authored holds sum to ~69s, and with 3D dwells and transits skipped
 * the journey's own weight math lands the run at ~90s without any per-scene
 * squeezing — scenes still play their full authored cut, there are just
 * fewer of them. Enabled-pack and spoiler gates still apply: a pack that is
 * off simply drops its stop from the short cut too.
 */
export const SHORT_CUT_SIM_IDS = new Set<string>([
  "baratie-zoro-vs-mihawk",
  "ace-fire-fist-destroys-billions-fleet",
  "arabasta-luffy-vs-crocodile-final",
  "skypiea-luffy-vs-enel",
  "enies-lobby-luffy-vs-rob-lucci",
]);
