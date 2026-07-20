/**
 * components/sim-models.ts — the shared registry + host for 2.5D story packs.
 *
 * The runtime-models.ts posture applied to simulations: one pure table built
 * from the sync artifact, one host that owns every gate, and a renderer
 * (sim-layer) that knows nothing about chapters. Adding the next saga's scenes
 * is a data change — the Codex handoff's "through data, not per-scene
 * components" rule, enforced by there being nowhere to put a per-scene component.
 *
 * THE HOST OWNS TIME, and that is the whole trick. sim-layer asks
 * `getTimeMs()` every frame; this file answers from per-scene clock state:
 *   - gate opens + zoom close enough  -> clock starts at 0, plays once
 *   - clock passes duration           -> answer clamps: final frame, forever
 *   - chapter falls below gate.start  -> layer REMOVED, clock deleted;
 *                                        re-entering restarts at 0 (scrub rule)
 *   - chapter passes gate.end         -> answer becomes null: static tableau,
 *                                        the "what happened here" mark
 *   - document hidden                 -> clock pauses, resumes without a jump
 *   - prefers-reduced-motion          -> layer told once; it holds the safe
 *                                        pose and never animates
 *
 * SINGLE-ACTIVE RULE (contract: max_active_close_scenes = 1): among scenes
 * whose clock is still running, only the one nearest the camera centre
 * animates; the rest hold at t=0 until they are the nearest. Held/finished
 * tableaus are cheap static planes and may coexist.
 *
 * OVERLAPPING ANCHORS: three Baratie scenes share one sea point and both
 * scaffold scenes share the platform. Stacked tableaus would be soup, so per
 * anchor point only the LATEST-gated eligible scene mounts — the place shows
 * its newest story state (at ch 99 the scaffold shows Buggy's blade, not
 * Roger's morning; Roger's own page still lives at /event/rogers-execution).
 *
 * WIRING (the entire WorldMap patch, kept to two calls so the camera session's
 * in-flight journey fix never collides with this file):
 *   import { EAST_BLUE_2D_ON } from "@/config/east-blue-simulations";
 *   // wherever chapter changes (beside the existing syncModels call):
 *   if (EAST_BLUE_2D_ON) void import("@/components/sim-models").then((s) => s.syncSimulations(map, ch));
 * The host self-registers its zoom/move listeners on first call; repeated
 * calls are cheap. The dynamic import keeps zod + the artifact out of every
 * flag-off bundle, same pattern as WorldMap's runtime_assets.json import.
 */

import maplibregl, { type Map as MlMap, type Marker } from "maplibre-gl";
import {
  createReadyGatedSceneClock, loadSimulations, markSceneClockReady,
  pauseSceneClock, resumeSceneClock, sceneClockElapsedMs, sceneEligible,
  sceneInActiveWindow, type ReadyGatedSceneClock, type StorySimulationPack,
  type SimScene,
} from "@/lib/simulation";
import { createSimLayer, type SimLayer } from "@/components/sim-layer";
import { SIM_FADE_IN_MS, SIM_FADE_OUT_MS, SIM_MIN_ZOOM, STAGE_SPAN_M } from "@/config/east-blue-simulations";
import { selectStoryPack, type StoryPackId } from "@/config/story-simulations";
import { GENERATED_PACKS } from "@/config/story-packs.generated";
import { getSimAudioSink } from "@/lib/sim-audio-bridge";
import { getJourneySimulationOverride } from "@/lib/simulation-journey-bridge";

type HostState = {
  map: MlMap;
  packId: StoryPackId;
  sims: StorySimulationPack;
  layers: Map<string, SimLayer>;
  clocks: Map<string, ReadyGatedSceneClock>;
  /** Scenes leaving by camera, mid-fade-out: id → performance.now() at fade
   * start. The clock freezes so the pose holds while the stage dissolves. */
  dying: Map<string, number>;
  /** Wide-zoom story beacons — "a story just happened here, click to see it". */
  beacons: Map<string, { marker: Marker; el: HTMLDivElement }>;
  chapter: number;
  reducedMotion: boolean;
  listenersOn: boolean;
};

/** How long after a scene's window a beacon keeps pulsing on the wide map.
 * The frozen tableau stays discoverable forever by zooming; the BEACON is a
 * nudge about recent story, so it fades from the chart after ~an arc. */
const BEACON_AFTERGLOW_CH = 15;

let host: HostState | null = null;

/** The pure part: which scenes should be MOUNTED at (chapter, zoom, bounds). */
export function visibleScenes(
  sims: StorySimulationPack,
  chapter: number,
  zoom: number,
  inView: (lng: number, lat: number) => boolean,
): SimScene[] {
  if (zoom < SIM_MIN_ZOOM) return [];
  const eligible = sims.scenes.filter(
    (s) => sceneEligible(s, chapter, true) && inView(s.anchor.lng, s.anchor.lat),
  );
  // Newest story state wins per anchor point (see header).
  const byPoint = new Map<string, SimScene>();
  for (const s of eligible) {
    const key = `${s.anchor.lng},${s.anchor.lat}`;
    const held = byPoint.get(key);
    if (!held || s.chapter_gate.start > held.chapter_gate.start) byPoint.set(key, s);
  }
  return [...byPoint.values()];
}

function now(): number {
  return performance.now();
}

function sceneTimeMs(state: HostState, scene: SimScene): number | null {
  // Past the window: the frozen tableau. (Never null DURING the window — the
  // reader who arrives at ch 51 sees the duel play.)
  if (!sceneInActiveWindow(scene, state.chapter)) return null;
  const journeyOverride = getJourneySimulationOverride();
  if (journeyOverride?.sceneId === scene.id) {
    return Math.min(scene.duration_ms, Math.max(0, journeyOverride.timeMs));
  }
  const clock = state.clocks.get(scene.id);
  if (!clock) return 0;
  return sceneClockElapsedMs(clock, now());
}

/** Among still-running clocks, only the nearest to centre animates. */
function nearestRunningId(state: HostState): string | null {
  const c = state.map.getCenter();
  let best: string | null = null;
  let bestD = Infinity;
  for (const [id] of state.clocks) {
    if (state.dying.has(id)) continue; // a dissolving stage yields the floor
    const scene = state.sims.scenes.find((s) => s.id === id);
    if (!scene) continue;
    const t = sceneTimeMs(state, scene);
    if (t === null || t >= scene.duration_ms) continue;
    const d = (scene.anchor.lng - c.lng) ** 2 + (scene.anchor.lat - c.lat) ** 2;
    if (d < bestD) {
      bestD = d;
      best = id;
    }
  }
  return best;
}

function makeBeaconElement(label: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "simBeacon";
  el.title = `${label} — click to watch`;
  el.style.cssText = "width:18px;height:18px;cursor:pointer;position:relative;";
  el.innerHTML = `
    <span style="position:absolute;inset:0;border-radius:50%;border:2px solid rgba(245,199,106,0.9);
      animation:gliBeacon 1.6s ease-out infinite;"></span>
    <span style="position:absolute;inset:5px;border-radius:50%;background:rgba(245,199,106,0.95);
      box-shadow:0 0 6px rgba(245,199,106,0.8);"></span>`;
  if (!document.getElementById("gli-beacon-style")) {
    const style = document.createElement("style");
    style.id = "gli-beacon-style";
    style.textContent = "@keyframes gliBeacon{0%{transform:scale(1);opacity:.9}100%{transform:scale(2.4);opacity:0}}";
    document.head.appendChild(style);
  }
  return el;
}

/** Scenes worth a wide-map nudge at this chapter: recently played (window →
 * afterglow), regardless of zoom — the beacon only SHOWS when zoomed out. */
function beaconScenes(sims: StorySimulationPack, chapter: number): SimScene[] {
  return sims.scenes.filter(
    (s) => chapter >= s.chapter_gate.start && chapter <= s.chapter_gate.end + BEACON_AFTERGLOW_CH,
  );
}

function syncBeacons(state: HostState): void {
  const zoom = state.map.getZoom();
  const wanted = zoom < SIM_MIN_ZOOM ? beaconScenes(state.sims, state.chapter) : [];
  const wantedIds = new Set(wanted.map((s) => s.id));
  for (const [id, b] of state.beacons) {
    if (!wantedIds.has(id)) {
      b.marker.remove();
      state.beacons.delete(id);
    }
  }
  for (const scene of wanted) {
    if (state.beacons.has(scene.id)) continue;
    const el = makeBeaconElement(scene.label);
    // The click is the manual reader's dive: the directory camera, on the
    // stage. The scene then mounts and plays through the ordinary gates.
    el.addEventListener("click", () => {
      state.map.easeTo({
        center: [scene.anchor.lng, scene.anchor.lat],
        zoom: 6.4,
        pitch: 48,
        duration: 1300,
      });
    });
    const marker = new maplibregl.Marker({ element: el })
      .setLngLat([scene.anchor.lng, scene.anchor.lat])
      .addTo(state.map);
    state.beacons.set(scene.id, { marker, el });
  }
}

function applySync(state: HostState): void {
  syncBeacons(state);
  const zoom = state.map.getZoom();
  const bounds = state.map.getBounds();
  const wanted = visibleScenes(state.sims, state.chapter, zoom, (lng, lat) =>
    bounds.contains([lng, lat]),
  );
  const wantedIds = new Set(wanted.map((s) => s.id));

  // Unmount: gate closed (backward scrub!), zoom out, left the viewport, or
  // superseded by a newer scene on the same anchor. Removal disposes GPU
  // memory AND deletes the clock — re-entry restarts at 0, which is the
  // contract's backward-scrub rule falling out of the lifecycle.
  //
  // Two exits, on purpose: gate-closed and supersede remove INSTANTLY (re-fog
  // now — the audited contract); camera exits (zoom-out / viewport) dissolve
  // over SIM_FADE_OUT_MS with the pose frozen, because a stage popping off
  // mid-swing was one of the measured "rough cut" causes.
  const removeNow = (sceneId: string) => {
    // The map id carries the sim- prefix; the host maps are keyed by scene id.
    // removeLayer fires the layer's own onRemove, which disposes the GPU side.
    const layerId = `sim-${sceneId}`;
    if (state.map.getLayer(layerId)) state.map.removeLayer(layerId);
    state.layers.delete(sceneId);
    state.clocks.delete(sceneId);
    state.dying.delete(sceneId);
  };
  for (const [sceneId] of state.layers) {
    if (wantedIds.has(sceneId)) continue;
    const scene = state.sims.scenes.find((s) => s.id === sceneId);
    const gateClosed = !scene || !sceneEligible(scene, state.chapter, true);
    const superseded =
      !gateClosed &&
      wanted.some((w) => w.anchor.lng === scene.anchor.lng && w.anchor.lat === scene.anchor.lat);
    if (gateClosed || superseded || state.reducedMotion) {
      removeNow(sceneId);
      getSimAudioSink()?.onSceneEnd(sceneId);
      continue;
    }
    if (state.dying.has(sceneId)) continue; // its ticker owns the removal
    // Camera exit: freeze the pose, silence the scene now, dissolve, THEN
    // dispose. The ticker keeps the map repainting through the fade (nothing
    // else forces frames once the camera settles).
    state.dying.set(sceneId, now());
    const clock = state.clocks.get(sceneId);
    if (clock) pauseSceneClock(clock, now());
    getSimAudioSink()?.onSceneEnd(sceneId);
    const tick = () => {
      const dyingAt = state.dying.get(sceneId);
      if (dyingAt === undefined || !state.layers.has(sceneId)) return; // revived or disposed
      if (now() - dyingAt >= SIM_FADE_OUT_MS) {
        removeNow(sceneId);
        return;
      }
      state.map.triggerRepaint();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  for (const scene of wanted) {
    const id = `sim-${scene.id}`;
    if (state.layers.has(scene.id)) {
      // Wanted again mid-fade (moveend jitter): cancel the dissolve, resume
      // the clock, and hand the scene back to the audio player.
      if (state.dying.delete(scene.id)) {
        const clock = state.clocks.get(scene.id);
        if (clock && !document.hidden) resumeSceneClock(clock, now());
        getSimAudioSink()?.onSceneMount(scene.id, scene, { reducedMotion: state.reducedMotion });
      }
      continue;
    }
    const clock = createReadyGatedSceneClock(now());
    // The single-active rule: a scene mounting while another is mid-fight
    // waits at t=0 (its startedAt keeps sliding until it is the nearest).
    state.clocks.set(scene.id, clock);
    getSimAudioSink()?.onSceneMount(scene.id, scene, { reducedMotion: state.reducedMotion });
    const layer = createSimLayer({
      id,
      lngLat: [scene.anchor.lng, scene.anchor.lat],
      scene,
      assets: state.sims.assets,
      stageSpanMeters: STAGE_SPAN_M,
      reducedMotion: state.reducedMotion,
      // Texture loading time is not story time. Open both the authored clock
      // and the fade only when every required atlas is on the GPU.
      onReady: () => {
        if (state.clocks.get(scene.id) !== clock || state.dying.has(scene.id)) return;
        markSceneClockReady(clock, now(), document.hidden);
      },
      opacity: () => {
        const fadeIn = Math.min(1, (now() - clock.mountedAt) / SIM_FADE_IN_MS);
        const dyingAt = state.dying.get(scene.id);
        if (dyingAt === undefined) return fadeIn;
        return fadeIn * Math.max(0, 1 - (now() - dyingAt) / SIM_FADE_OUT_MS);
      },
      // The audio sink samples the EXACT value the renderer receives, on the
      // same frame — one clock, two cursors (see lib/sim-audio-bridge.ts).
      getTimeMs: () => {
        const t = sceneTimeMs(state, scene);
        if (t === null) {
          getSimAudioSink()?.onSceneTime(scene.id, null);
          return null;
        }
        // Not the nearest running scene -> hold at 0 and keep the clock
        // pinned so it plays fresh when its turn comes.
        if (t < scene.duration_ms) {
          const active = nearestRunningId(state);
          if (active !== null && active !== scene.id) {
            clock.startedAt = (clock.pausedAt ?? now());
            getSimAudioSink()?.onSceneTime(scene.id, 0);
            return 0;
          }
        }
        getSimAudioSink()?.onSceneTime(scene.id, t);
        return t;
      },
    });
    state.map.addLayer(layer);
    state.layers.set(scene.id, layer);
  }
}

function onVisibility(): void {
  if (!host) return;
  const t = now();
  for (const [, clock] of host.clocks) {
    if (document.hidden) {
      pauseSceneClock(clock, t);
    } else {
      resumeSceneClock(clock, t);
    }
  }
  host.map.triggerRepaint();
}

/**
 * The one entry point. Call on chapter change (and initial map load); the host
 * wires its own zoom/move/visibility listeners on first call.
 *
 * `force` exists for exactly one caller: the dev-only /dev/sim-proof harness,
 * which must exercise this real host on a sandbox map while the production
 * flag stays off. Nothing reader-facing may pass it — the flag is the law.
 */
async function loadStoryPack(packId: StoryPackId): Promise<StorySimulationPack> {
  // The literal import() thunks live in the generated registry, so Next still
  // emits one optional chunk per signed pack — and a new pack needs no edit here.
  const pack = GENERATED_PACKS.find((entry) => entry.id === packId);
  if (!pack) throw new Error(`unknown story pack ${packId}`);
  return loadSimulations((await pack.load()).default);
}

function clearRenderedState(state: HostState): void {
  for (const [sceneId] of state.layers) {
    const layerId = `sim-${sceneId}`;
    if (state.map.getLayer(layerId)) state.map.removeLayer(layerId);
    getSimAudioSink()?.onSceneEnd(sceneId);
  }
  state.layers.clear();
  state.clocks.clear();
  state.dying.clear();
  for (const [, beacon] of state.beacons) beacon.marker.remove();
  state.beacons.clear();
}

let loadSerial = 0;
let audioInstallTask: Promise<void> | null = null;

/** Install before any scene can mount, while retaining the flag-off split. */
function ensureSimulationAudioInstalled(): Promise<void> {
  if (!audioInstallTask) {
    audioInstallTask = import("@/lib/simulation-audio-player")
      .then((m) => m.installSimulationAudio())
      .catch((error) => {
        // Audio is enhancement-only: a registry/load failure must not erase
        // the visual story, but it must be visible and retryable on next sync.
        audioInstallTask = null;
        console.error("simulation audio install failed", error);
      });
  }
  return audioInstallTask;
}

export async function syncSimulations(
  map: MlMap,
  chapter: number,
  force = false,
  requestedPack?: StoryPackId,
): Promise<void> {
  const packId = selectStoryPack(
    chapter,
    force ? (requestedPack ?? "east-blue-saga-2d") : undefined,
  );
  if (!packId) return;

  // Scene sound rides the same dynamic-import chain as the host itself, but
  // applySync MUST wait for it: otherwise the first onSceneMount vanishes into
  // the bridge's null sink and that scene never receives an audio cursor.
  const audioReady = ensureSimulationAudioInstalled();

  if (!host || host.map !== map || host.packId !== packId) {
    const serial = ++loadSerial;
    const [sims] = await Promise.all([loadStoryPack(packId), audioReady]);
    if (serial !== loadSerial) return;

    if (host?.map === map) {
      clearRenderedState(host);
      host.packId = packId;
      host.sims = sims;
      host.chapter = chapter;
    } else {
      host = {
        map,
        packId,
        sims,
        layers: new Map(),
        clocks: new Map(),
        dying: new Map(),
        beacons: new Map(),
        chapter,
        reducedMotion:
          typeof window !== "undefined" &&
          window.matchMedia("(prefers-reduced-motion: reduce)").matches,
        listenersOn: false,
      };
    }
  } else {
    await audioReady;
  }
  host.chapter = chapter;
  if (!host.listenersOn) {
    host.listenersOn = true;
    const ownedMap = host.map;
    const resync = () => {
      if (host?.map === ownedMap) applySync(host);
    };
    host.map.on("zoomend", resync);
    host.map.on("moveend", resync);
    document.addEventListener("visibilitychange", onVisibility);
    host.map.on("remove", () => {
      document.removeEventListener("visibilitychange", onVisibility);
      if (host?.map === ownedMap) host = null;
    });
  }
  applySync(host);
}
