/**
 * components/glb-layer.ts — draw a glTF model at a real coordinate on the map.
 *
 * MapLibre has no glTF. This is the CustomLayerInterface + three.js that
 * manifests/runtime-3d.json's `enable_glb_when` has been waiting for, and it is
 * the app's ONLY 3D renderer. Pure module: no React, no canon, no chapter logic
 * — it takes a coordinate and a URL and draws. Every gate lives in the caller
 * (WorldMap), because a renderer that knows about chapters is a renderer you
 * cannot reuse for the next island.
 *
 * ── WHY THIS WORKS ON A GLOBE, which is not the obvious answer ──────────────
 *
 * MapLibre's own docs steer you away from it. `CustomRenderMethodInput` says:
 * "If you just need a projection matrix, use `defaultProjectionData.projectionMatrix`.
 * A projection matrix is sufficient for simple custom layers that ALSO ONLY
 * SUPPORT MERCATOR PROJECTION" — because globe projection happens in MapLibre's
 * VERTEX SHADER (`projectTile`/`projectTileFor3D`), and three.js brings its own
 * shaders, so there is no seam to inject it into short of rewriting every
 * material. That is a real limit, and it is exactly why `projection_unsupported`
 * is one of the five reasons in lib/scenes.ts. We wrote that reason down before
 * we knew this file would need it.
 *
 * `getMatrixForModel(lngLat, altitude)` is the way around it, and the evidence it
 * is meant for precisely this is that MAPLIBRE NEVER CALLS IT ITSELF — grep the
 * package: it appears in the transform interface and nowhere else. It exists for
 * custom layers. Read both implementations and the trick is visible:
 *
 *   mercator   scale = meterInMercatorCoordinateUnits(); translate(mercator xyz)
 *              -> maps model METRES into mercator 0..1 space
 *   globe      scale = 1/earthRadius; rotateY(lng); rotateX(-lat);
 *              translate([0, 0, 1 + altitude/earthRadius])
 *              -> maps model METRES onto the UNIT SPHERE
 *
 * and `mainMatrix` is the matrix each projection applies to exactly that space —
 * for globe it is `_globeViewProjMatrix`, which MapLibre's own clipping-plane
 * comment describes as "applied to the unit sphere generated in the vertex
 * shader". So `mainMatrix × getMatrixForModel(...)` is model→clip under BOTH
 * projections, with no shader surgery and no branch. The projection difference
 * is absorbed by MapLibre, which is what the method is for.
 *
 * Consequences, both load-bearing:
 *   - MODEL UNITS ARE METRES. Both implementations scale by a metric constant.
 *     A glTF authored in Blender units needs a real metres-per-unit or it is a
 *     speck. The caller supplies it; this file will not guess.
 *   - Y IS UP. Both implementations end with rotateX(π/2), which is the Y-up →
 *     Z-up correction. That is standard glTF (the Blender exporter converts
 *     Blender's Z-up on the way out), so a .glb is already right.
 *
 * We put the model matrix on the OBJECT and mainMatrix on the CAMERA, rather
 * than pre-multiplying both into the camera. It costs nothing and it buys the
 * globe's clipping plane: `defaultProjectionData.clippingPlane` is stated in
 * unit-sphere space, which is then the scene's world space, so three.js can use
 * it verbatim. Without it, a model on the far side of the planet draws THROUGH
 * the planet — the globe's sphere is shader-generated and does not fill the
 * depth buffer on our behalf.
 */

import type { CustomLayerInterface, CustomRenderMethodInput, Map as MlMap } from "maplibre-gl";
import type * as THREE from "three";

/** Everything the layer needs that it must not decide for itself. */
export type GlbLayerOptions = {
  id: string;
  /** Served from public/. Fetched on the FIRST render after add — never earlier. */
  url: string;
  /** Where the model's origin sits. The model's own Y=0 plane lands here. */
  lngLat: [number, number];
  /** Metres above the sphere for the model's origin. */
  altitude?: number;
  /**
   * The model's unit → metres. There is no default and there must not be one:
   * a glTF carries no real-world scale, so any number chosen here would be an
   * invention wearing a constant's clothes. See WorldMap for how ours is derived.
   */
  metersPerUnit: number;
  /** 0..1, read EVERY frame — this is how a chapter beat reaches the model. */
  opacity: () => number;
  /** Radians, applied about the up axis. Models face +Z at 0. */
  bearing?: number;
  /**
   * Fired once the bytes are on the GPU. The caller needs this to cross-fade
   * honestly: a fallback may only stand down when the thing replacing it is
   * actually drawable, never when it has merely been asked for. On a cold cache
   * that is 2.5MB away.
   */
  onReady?: () => void;
  /**
   * Permanently hide nodes at load, by name. NOT a spoiler gate — this is for
   * decorative backdrop geometry that fights the map, and it never re-evaluates.
   * The archipelago blockouts ship a big flat "ocean stage" plate under the
   * islands; on a globe that already IS the sea, that plate reads as a diorama
   * base and buries the islands. Hiding it drops the archipelago onto the map's
   * own ocean. Scoped to spread archipelagos only (see runtime-models) so an
   * event scene's meaningful backdrop is never mistaken for a throwaway plate.
   *
   * Runs on the GLTF-exported names (spaces become underscores).
   */
  hideNode?: (nodeName: string) => boolean;
  /**
   * PER-NODE GATING — the spoiler contract reaching inside the model.
   *
   * A model is not one thing. `totto-land` is 35 islands in one file, 14 of them
   * withheld because nobody has verified when they are revealed;
   * `mary-geoise-red-line` carries the Red Line's lower ports, which a
   * chapter-142 reader must not see. So the whole-model chapter gate is not
   * enough, and the asset track says so: "A GLB node is never rendered before its
   * component gate", enforced by reading `component_id`, `reveal_chapter`,
   * `gate_confidence` and `default_hidden` out of glTF node extras.
   *
   * The predicate is the CALLER'S, not ours — this file still knows nothing about
   * chapters, and that boundary is what lets it draw the next island without
   * being edited. We only walk the tree and flip `.visible`.
   *
   * Re-evaluated on every chapter change, not just at load: scrubbing backwards
   * has to re-fog, and geometry already on the GPU is exactly where a naive
   * implementation forgets that.
   *
   * Returning `true` for a node you cannot identify is how this leaks. Default to
   * hiding.
   */
  nodeVisible?: (extras: Record<string, unknown>, nodeName: string) => boolean;
  /** Absolute chapter-entry sampling supplied by the app. The renderer never
   * advances story state; it only evaluates named clips at requested progress. */
  animationState?: () => {
    clips: { name: string; progress: number; loop: boolean }[];
    animate: boolean;
    chapter: number;
    elapsedMs: number;
  } | null;
};

type Gated = { obj: THREE.Object3D; extras: Record<string, unknown>; name: string };

type Loaded = {
  three: typeof THREE;
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.Camera;
  group: THREE.Group;
  materials: THREE.Material[];
  /** Every node carrying extras, collected once so re-gating is a short loop. */
  gated: Gated[];
  mixer: THREE.AnimationMixer | null;
  actions: Map<string, THREE.AnimationAction>;
  activeActions: Set<string>;
};

export type GlbLayer = CustomLayerInterface & {
  /** True once the bytes are on the GPU. Lets the caller cross-fade honestly. */
  ready: () => boolean;
  /**
   * Re-run `nodeVisible` over every tagged node. The caller calls this when the
   * chapter moves — including BACKWARDS, which is the direction that leaks if you
   * only gate at load.
   */
  regate: () => void;
};

export function createGlbLayer(opts: GlbLayerOptions): GlbLayer {
  let map: MlMap | null = null;
  let g: Loaded | null = null;
  let disposed = false;

  /** Walk the tagged nodes and let the caller's predicate decide each one. */
  function applyGates(): void {
    if (!g || !opts.nodeVisible) return;
    for (const n of g.gated) n.obj.visible = opts.nodeVisible(n.extras, n.name);
  }

  function applyAnimation(): boolean {
    if (!g || !g.mixer || !opts.animationState) return false;
    const sample = opts.animationState();
    const wanted = new Set(sample?.clips.map((item) => item.name) ?? []);
    for (const name of g.activeActions) {
      if (!wanted.has(name)) g.actions.get(name)?.stop();
    }
    for (const item of sample?.clips ?? []) {
      const action = g.actions.get(item.name);
      if (!action) continue;
      if (!g.activeActions.has(item.name)) action.reset().play();
      action.enabled = true;
      action.paused = true;
      action.clampWhenFinished = !item.loop;
      action.setLoop(item.loop ? g.three.LoopRepeat : g.three.LoopOnce, item.loop ? Infinity : 1);
      action.time = Math.max(0, Math.min(action.getClip().duration, item.progress * action.getClip().duration));
    }
    g.activeActions = wanted;
    g.mixer.update(0);
    if (process.env.NODE_ENV !== "production" && sample) {
      const w = window as unknown as {
        __glbAnimationState?: Record<string, { chapter: number; elapsedMs: number; clips: string[]; animate: boolean }>;
      };
      (w.__glbAnimationState ??= {})[opts.id] = {
        chapter: sample.chapter,
        elapsedMs: sample.elapsedMs,
        clips: sample.clips.map((item) => item.name),
        animate: sample.animate,
      };
    }
    return sample?.animate ?? false;
  }

  return {
    id: opts.id,
    type: "custom",
    // "3d": we want the map's depth buffer, so coastlines and the vector column
    // occlude the model instead of the model floating over everything.
    renderingMode: "3d",

    ready: () => !!g,
    regate: applyGates,

    onAdd(m: MlMap, gl: WebGLRenderingContext | WebGL2RenderingContext) {
      map = m;
      // three.js plus GLTFLoader is a ~1MB chunk (measured, not the ~600KB we
      // guessed). Importing it HERE, inside onAdd, means it is requested only
      // once a gate has already opened — the asset track's rule for the model
      // ("never fetched before their chapter gate") applied to the code that
      // draws it. A static import would ship it to a chapter-1 reader who will
      // never see Skypiea.
      //
      // True of the BUILD, and only of the build: Turbopack's dev server serves
      // dynamic-import chunks eagerly, so in `next dev` three.js loads at chapter
      // 1 regardless. Verified in a real browser both ways rather than assumed —
      // audit_glb asserts it against a `next start` build and refuses to assert
      // it against dev, where it would only be measuring the dev server.
      void (async () => {
        const [three, { GLTFLoader }] = await Promise.all([
          import("three"),
          import("three/examples/jsm/loaders/GLTFLoader.js"),
        ]);
        if (disposed) return;

        // Share the map's context. A second WebGL context would be a second
        // canvas, compositing on its own and drifting by a frame under any pan.
        const renderer = new three.WebGLRenderer({ canvas: m.getCanvas(), context: gl, antialias: true });
        renderer.autoClear = false;

        const scene = new three.Scene();
        const camera = new three.Camera();
        const group = new three.Group();
        // We drive this matrix ourselves every frame from getMatrixForModel.
        group.matrixAutoUpdate = false;
        scene.add(group);

        // The blockout ships 8 materials and no textures (images=0), so it is lit
        // entirely by us. Hemisphere + a low sun reads the volumes without the
        // flat-shaded look a single ambient gives.
        scene.add(new three.HemisphereLight(0xbfe3ff, 0x1b3a5c, 2.4));
        const sun = new three.DirectionalLight(0xfff2d5, 2.0);
        sun.position.set(-0.6, 1, 0.75);
        scene.add(sun);

        const gltf = await new GLTFLoader().loadAsync(opts.url);
        if (disposed) {
          renderer.dispose();
          return;
        }

        const model = gltf.scene;
        model.scale.setScalar(opts.metersPerUnit);
        if (opts.bearing) model.rotation.y = opts.bearing;
        group.add(model);

        // Collect materials once so the per-frame opacity write is a short loop
        // over 8 rather than a traverse of 64 nodes every frame. Same pass
        // collects the gated nodes, so re-gating never traverses either.
        const materials: THREE.Material[] = [];
        const gated: Gated[] = [];
        model.traverse((o) => {
          // Backdrop first, and permanently: a hidden plate needs no material
          // work and never re-gates.
          if (opts.hideNode?.(o.name)) { o.visible = false; return; }
          const extras = (o.userData ?? {}) as Record<string, unknown>;
          // three.js parks glTF `extras` on userData verbatim.
          if (Object.keys(extras).length) gated.push({ obj: o, extras, name: o.name });
          const mesh = o as THREE.Mesh;
          if (!mesh.isMesh) return;
          for (const mat of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
            if (materials.includes(mat)) continue;
            mat.transparent = true;
            // The model is a column of water and cloud seen against the sea:
            // depth-writing transparent geometry would punch holes in itself
            // wherever two banks overlap.
            mat.depthWrite = false;
            materials.push(mat);
          }
        });

        const mixer = gltf.animations.length ? new three.AnimationMixer(model) : null;
        const actions = new Map<string, THREE.AnimationAction>();
        if (mixer) {
          for (const animation of gltf.animations) actions.set(animation.name, mixer.clipAction(animation));
        }
        g = { three, renderer, scene, camera, group, materials, gated, mixer, actions, activeActions: new Set() };
        // Dev-only, beside window.__map: lets an audit reach into the loaded scene
        // to inspect or toggle nodes by name (e.g. testing whether hiding a
        // backdrop plate reads better) without shipping any of it.
        if (process.env.NODE_ENV !== "production") {
          const w = window as unknown as {
            __glbScenes?: Record<string, THREE.Object3D>;
            __glbClipNames?: Record<string, string[]>;
          };
          (w.__glbScenes ??= {})[opts.id] = model;
          (w.__glbClipNames ??= {})[opts.id] = gltf.animations.map((animation) => animation.name);
        }
        // Gate BEFORE the first frame. `loadAsync` resolving means the geometry
        // is ready to draw, so anything withheld must be hidden now and not on
        // the next tick — one frame of a spoiler is a spoiler.
        applyGates();
        opts.onReady?.();
        m.triggerRepaint();
      })();
    },

    render(_gl: WebGLRenderingContext | WebGL2RenderingContext, args: CustomRenderMethodInput) {
      if (!g || !map) return; // still loading — the map is not blocked on us

      const o = opts.opacity();
      if (o <= 0) return;
      for (const mat of g.materials) mat.opacity = o;

      // The whole projection story, in two lines. `transform` is not in the
      // published types (it is documented in CustomRenderMethodInput's own prose
      // as `map.transform.getProjectionData(...)`, which is how you are meant to
      // reach it), so this cast is naming a real, intended API.
      const transform = (map as unknown as { transform: { getMatrixForModel(l: [number, number], a?: number): number[] } }).transform;
      g.group.matrix.fromArray(transform.getMatrixForModel(opts.lngLat, opts.altitude ?? 0));
      g.camera.projectionMatrix.fromArray(args.defaultProjectionData.mainMatrix as unknown as number[]);

      // Globe only: clip everything behind the horizon. `projectionTransition`
      // is 1 on the globe and 0 on mercator, and it is fractional mid-morph, so
      // the plane goes in exactly when the sphere is being drawn.
      const cp = args.defaultProjectionData.clippingPlane;
      if (cp && args.defaultProjectionData.projectionTransition > 0) {
        g.renderer.clippingPlanes = [new g.three.Plane(new g.three.Vector3(cp[0], cp[1], cp[2]), cp[3])];
      } else {
        g.renderer.clippingPlanes = [];
      }

      const keepAnimating = applyAnimation();

      // three.js has no idea MapLibre just used this context.
      g.renderer.resetState();
      g.renderer.render(g.scene, g.camera);
      if (keepAnimating) map.triggerRepaint();
    },

    onRemove() {
      // `unload_when_hidden: true`, honoured literally — the caller removes the
      // layer when the gate shuts and the GPU memory goes with it.
      disposed = true;
      if (!g) return;
      g.group.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.isMesh) mesh.geometry?.dispose();
      });
      for (const mat of g.materials) mat.dispose();
      if (g.mixer) {
        g.mixer.stopAllAction();
        const root = g.group.children[0];
        if (root) g.mixer.uncacheRoot(root);
      }
      if (process.env.NODE_ENV !== "production") {
        const w = window as unknown as {
          __glbScenes?: Record<string, THREE.Object3D>;
          __glbClipNames?: Record<string, string[]>;
          __glbAnimationState?: Record<string, unknown>;
        };
        delete w.__glbScenes?.[opts.id];
        delete w.__glbClipNames?.[opts.id];
        delete w.__glbAnimationState?.[opts.id];
      }
      // NOT renderer.dispose(): the context is MapLibre's, and disposing the
      // renderer takes the map's own GL state down with it.
      g = null;
      map = null;
    },
  };
}
