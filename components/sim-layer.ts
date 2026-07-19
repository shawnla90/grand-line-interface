/**
 * components/sim-layer.ts — draw one 2.5D story simulation at a real coordinate.
 *
 * The sibling of glb-layer.ts, and deliberately the same shape: a MapLibre
 * CustomLayerInterface hosting three.js on the map's own GL context, with
 * `getMatrixForModel(lngLat)` on the stage group and
 * `defaultProjectionData.mainMatrix` on the camera — the recipe that works
 * under BOTH mercator and globe (the long why lives in glb-layer.ts's header;
 * it is not repeated here because it is the same two lines of code).
 *
 * What is DIFFERENT from glb-layer, and why this is its own file rather than
 * an option on that one: a GLB is one object with one lifecycle; a simulation
 * is N billboarded actor planes + per-frame scene time + step-selected atlas
 * cells + an FX registry + play/hold/reset semantics. Grafting that onto the
 * GLB loader would tangle two clean lifecycles into one confusing one.
 *
 * Still a pure module: no React, no chapter logic, no clocks. The caller
 * (sim-models) owns time via `getTimeMs()` — this layer only asks. That is how
 * play-once, backward-scrub reset, visibility pause and reduced motion all
 * stay OUTSIDE the renderer, in one host, testable without a GPU:
 *   getTimeMs() => number  — evaluate the scene at that local time
 *   getTimeMs() => null    — static mode: hold the authored final frame
 */

import type { CustomLayerInterface, CustomRenderMethodInput, Map as MlMap } from "maplibre-gl";
import type * as THREE from "three";
import {
  createFxCursor, evaluateActor, poseUv, visualTreatmentAt,
  type FxCursor, type SimAsset, type SimScene,
} from "@/lib/simulation";
import { createFxInstance, type FxInstance } from "@/components/sim-fx";

export type SimLayerOptions = {
  id: string;
  /** Where the stage's origin (x=0, ground plane) sits. From the anchor table. */
  lngLat: [number, number];
  scene: SimScene;
  /** asset_id -> SimAsset for every actor this scene casts. */
  assets: Record<string, SimAsset>;
  /**
   * The stage's half-width in metres: actor x = ±1 lands ±stageSpanMeters/2
   * from the anchor. Like the GLB models' visual_fit this is a MAP-SCALE
   * theatre, not a canon measurement — nobody claims Mihawk is kilometres
   * tall; at zoom 4.6+ the alternative is an invisible speck.
   */
  stageSpanMeters: number;
  /** Local scene time in ms, or null to hold the final authored frame. */
  getTimeMs: () => number | null;
  /** 0..1, read every frame — the caller's fade in/out. */
  opacity: () => number;
  /** Static safe pose, no FX — the contract's reduced_motion policy. */
  reducedMotion: boolean;
  /** Fired once every atlas is on the GPU (the honest-crossfade hook). */
  onReady?: () => void;
};

type ActorRig = {
  actorIdx: number;
  mesh: THREE.Mesh;
  material: THREE.MeshBasicMaterial;
  /** Per-actor CLONE of the cached base texture (shared-atlas rule). */
  texture: THREE.Texture;
  frames: SimAsset["frames"];
  mapHeight: number;
  /** The pose currently on the UVs, so we only touch offsets on change. */
  pose: string | null;
  gammaUniform: { value: number };
  gainUniform: { value: number };
};

type Loaded = {
  three: typeof THREE;
  renderer: THREE.WebGLRenderer;
  scene3: THREE.Scene;
  camera: THREE.Camera;
  stage: THREE.Group;
  rigs: ActorRig[];
  baseTextures: THREE.Texture[];
  fxLive: Map<number, FxInstance>;
};

export type SimLayer = CustomLayerInterface & {
  ready: () => boolean;
};

export function createSimLayer(opts: SimLayerOptions): SimLayer {
  let map: MlMap | null = null;
  let g: Loaded | null = null;
  let disposed = false;
  const cursor: FxCursor = createFxCursor(opts.scene);
  const half = opts.stageSpanMeters / 2;

  return {
    id: opts.id,
    type: "custom",
    renderingMode: "3d",

    ready: () => !!g,

    onAdd(m: MlMap, gl: WebGLRenderingContext | WebGL2RenderingContext) {
      map = m;
      // Same deferred-import rule as glb-layer: three.js is only requested once
      // a chapter gate has actually opened. A chapter-1 reader never pays for it.
      void (async () => {
        const three = await import("three");
        if (disposed) return;

        const renderer = new three.WebGLRenderer({ canvas: m.getCanvas(), context: gl, antialias: true });
        renderer.autoClear = false;

        const scene3 = new three.Scene();
        const camera = new three.Camera();
        const stage = new three.Group();
        stage.matrixAutoUpdate = false;
        scene3.add(stage);
        // Billboarding is applied to THIS child, not the matrix-driven stage —
        // the stage matrix comes verbatim from getMatrixForModel every frame.
        const yaw = new three.Group();
        stage.add(yaw);

        // One base texture per atlas URL, cloned per actor. The clone is not
        // optional politeness: repeat/offset live ON the texture, so two actors
        // sharing one atlas would fight over which pose is visible.
        const loader = new three.TextureLoader();
        const baseByUrl = new Map<string, THREE.Texture>();
        const baseTextures: THREE.Texture[] = [];
        const rigs: ActorRig[] = [];

        await Promise.all(
          opts.scene.actors.map(async (actor, actorIdx) => {
            const asset = opts.assets[actor.asset_id];
            let base = baseByUrl.get(asset.url);
            if (!base) {
              base = await loader.loadAsync(asset.url);
              base.colorSpace = three.SRGBColorSpace;
              baseByUrl.set(asset.url, base);
              baseTextures.push(base);
            }
            if (disposed) return;
            const texture = base.clone();
            texture.needsUpdate = true;
            const material = new three.MeshBasicMaterial({
              map: texture,
              transparent: true,
              alphaTest: 0.05,
              depthWrite: false,
              side: three.DoubleSide,
            });
            // The user's Sabaody reference review exposed why a whole-frame
            // color grade looks wrong on the globe. Apply the optional authored
            // gamma/gain response to this isolated actor texture only. Uniforms
            // remain live after compilation and are sampled from absolute scene
            // time, so contact brightness is deterministic across frame rates.
            const gammaUniform = { value: 1 };
            const gainUniform = { value: 1 };
            material.onBeforeCompile = (shader) => {
              shader.uniforms.uSimActorGamma = gammaUniform;
              shader.uniforms.uSimActorGain = gainUniform;
              shader.fragmentShader = shader.fragmentShader.replace(
                "#include <map_fragment>",
                `#include <map_fragment>
                 diffuseColor.rgb = pow(max(diffuseColor.rgb, vec3(0.00001)), vec3(uSimActorGamma)) * uSimActorGain;`,
              );
              shader.fragmentShader = shader.fragmentShader.replace(
                "void main() {",
                `uniform float uSimActorGamma;
                 uniform float uSimActorGain;
                 void main() {`,
              );
            };
            material.customProgramCacheKey = () => "sim-actor-gamma-v1";
            // Unit plane; real size comes from map_height × keyframe scale at
            // render time. The pivot shift puts the authored anchor point (the
            // feet, pivot.y≈0.96 measured from the cell's top) at local origin,
            // so y=0 in stage space is the ground the contract promises.
            const first = actor.keyframes[0];
            const pivot = asset.frames[first.pose].pivot;
            const geo = new three.PlaneGeometry(1, 1);
            geo.translate(0.5 - pivot.x, pivot.y - 0.5, 0);
            const mesh = new three.Mesh(geo, material);
            // Authored z is paint order within the stage, not depth: the
            // planes are coplanar billboards, so depth-test ties go to
            // renderOrder and we disable depth entirely between actors.
            mesh.renderOrder = actor.z;
            yaw.add(mesh);
            rigs[actorIdx] = {
              actorIdx, mesh, material, texture,
              frames: asset.frames, mapHeight: asset.map_height, pose: null,
              gammaUniform, gainUniform,
            };
          }),
        );
        if (disposed) {
          for (const t of baseTextures) t.dispose();
          return;
        }

        g = { three, renderer, scene3, camera, stage, rigs, baseTextures, fxLive: new Map() };
        // Dev-only, beside window.__glbScenes: what the Playwright audit reads
        // to prove pose steps land at their authored millisecond.
        if (process.env.NODE_ENV !== "production") {
          const w = window as unknown as { __simScenes?: Record<string, unknown> };
          // The hook reports what is RENDERED, so under reduced motion it says
          // "final frame, no FX" — the audit asserts against these numbers and
          // a hook that reported the suppressed clock would be a hook lying.
          const effT = () => (opts.reducedMotion ? null : opts.getTimeMs()) ?? opts.scene.duration_ms;
          (w.__simScenes ??= {})[opts.id] = {
            get timeMs() { return opts.reducedMotion ? null : opts.getTimeMs(); },
            get reducedMotion() { return opts.reducedMotion; },
            get actors() {
              const t = effT();
              return opts.scene.actors.map((a) => ({ id: a.id, ...evaluateActor(a, t) }));
            },
            get firedFx() {
              if (opts.reducedMotion) return [];
              return createFxCursor(opts.scene).sample(effT()).map((f) => ({ type: f.type, age: f.age, active: f.active }));
            },
            get rigs() {
              return (g?.rigs ?? []).filter(Boolean).map((r) => ({
                pose: r.pose,
                scale: [r.mesh.scale.x, r.mesh.scale.y],
                pos: [r.mesh.position.x, r.mesh.position.y],
                hasImage: !!r.texture.image,
                imageSize: r.texture.image
                  ? [(r.texture.image as HTMLImageElement).width, (r.texture.image as HTMLImageElement).height]
                  : null,
                repeat: [r.texture.repeat.x, r.texture.repeat.y],
                offset: [r.texture.offset.x, r.texture.offset.y],
                opacity: r.material.opacity,
                gamma: r.gammaUniform.value,
                gain: r.gainUniform.value,
                mapIsClone: r.material.map === r.texture,
              }));
            },
          };
        }
        opts.onReady?.();
        m.triggerRepaint();
      })();
    },

    render(_gl: WebGLRenderingContext | WebGL2RenderingContext, args: CustomRenderMethodInput) {
      if (!g || !map) return;
      const layerOpacity = opts.opacity();
      if (layerOpacity <= 0) return;

      // Reduced motion = the final safe pose, statically, FX suppressed — the
      // contract's own policy, enforced at the render boundary so no caller
      // can forget it.
      const rawT = opts.reducedMotion ? null : opts.getTimeMs();
      const tMs = rawT === null ? opts.scene.duration_ms : Math.min(rawT, opts.scene.duration_ms);
      const treatment = visualTreatmentAt(opts.scene, tMs);

      const yaw = g.stage.children[0] as THREE.Group;
      for (const rig of g.rigs) {
        if (!rig) continue; // a texture that never resolved — actor stays absent
        const actor = opts.scene.actors[rig.actorIdx];
        const s = evaluateActor(actor, tMs);
        if (s.pose !== rig.pose) {
          const uv = poseUv(rig.frames, s.pose);
          rig.texture.repeat.set(uv.repeatX, uv.repeatY);
          rig.texture.offset.set(uv.offsetX, uv.offsetY);
          rig.pose = s.pose;
        }
        const h = rig.mapHeight * s.scale * half;
        rig.mesh.scale.set(h, h, 1);
        rig.mesh.position.set(s.x * half, s.y * half, 0);
        rig.mesh.rotation.z = (-s.rotation * Math.PI) / 180;
        rig.material.opacity = s.opacity * layerOpacity;
        rig.gammaUniform.value = treatment.gamma;
        rig.gainUniform.value = treatment.gain;
      }

      // FX: the cursor answers "what has fired by tMs" (rebuilding on backward
      // motion); we diff that against the live instances.
      if (!opts.reducedMotion) {
        const fired = cursor.sample(tMs);
        const activeIdx = new Set<number>();
        for (const fx of fired) {
          if (!fx.active) continue;
          const key = fx.t * 100 + opts.scene.events.findIndex((e) => e.t === fx.t && e.type === fx.type);
          activeIdx.add(key);
          let inst = g.fxLive.get(key);
          if (!inst) {
            inst = createFxInstance(g.three, yaw, fx, half);
            g.fxLive.set(key, inst);
          }
          inst.update(fx.age);
        }
        for (const [key, inst] of g.fxLive) {
          if (!activeIdx.has(key)) {
            inst.dispose();
            g.fxLive.delete(key);
          }
        }
      }

      // Face the camera about local up: the stage matrix orients local Y along
      // the sphere normal, so undoing the map bearing on the child group keeps
      // the plates fronting the viewer at every azimuth. (Yaw-only on purpose —
      // pitch-billboarding would lie the actors down at high pitch.)
      yaw.rotation.y = (-map.getBearing() * Math.PI) / 180;

      const transform = (map as unknown as { transform: { getMatrixForModel(l: [number, number], a?: number): number[] } }).transform;
      g.stage.matrix.fromArray(transform.getMatrixForModel(opts.lngLat, 0));
      g.camera.projectionMatrix.fromArray(args.defaultProjectionData.mainMatrix as unknown as number[]);

      const cp = args.defaultProjectionData.clippingPlane;
      if (cp && args.defaultProjectionData.projectionTransition > 0) {
        g.renderer.clippingPlanes = [new g.three.Plane(new g.three.Vector3(cp[0], cp[1], cp[2]), cp[3])];
      } else {
        g.renderer.clippingPlanes = [];
      }

      g.renderer.resetState();
      g.renderer.render(g.scene3, g.camera);

      // A playing scene needs the next frame; a held one does not. Asking only
      // while time is running keeps the map idle once the tableau freezes.
      if (rawT !== null && rawT < opts.scene.duration_ms) map.triggerRepaint();
    },

    onRemove() {
      disposed = true;
      if (!g) return;
      for (const [, inst] of g.fxLive) inst.dispose();
      g.fxLive.clear();
      for (const rig of g.rigs) {
        if (!rig) continue;
        rig.mesh.geometry.dispose();
        rig.material.dispose();
        rig.texture.dispose();
      }
      for (const t of g.baseTextures) t.dispose();
      if (process.env.NODE_ENV !== "production") {
        const w = window as unknown as { __simScenes?: Record<string, unknown> };
        if (w.__simScenes) delete w.__simScenes[opts.id];
      }
      // NOT renderer.dispose() — the context is MapLibre's (glb-layer's rule).
      g = null;
      map = null;
    },
  };
}
