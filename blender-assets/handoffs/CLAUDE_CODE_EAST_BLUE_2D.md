# Claude Code handoff — East Blue 2.5D simulations

## Outcome

Add the verified East Blue illustrated simulation pack to the Grand Line
Interface behind a disabled-by-default feature flag. Prove one scene in the
real map, then make all twelve runtime-ready scenes available through the same
generic renderer. Do not recreate scene logic in components.

The asset workspace is read-only from the app integration task. Copy only the
runtime paths listed below and preserve their relative structure.

## Source of truth

From the asset workspace:

- `manifests/east-blue-2d.json`
- `contracts/east-blue-saga.simulation.json`
- `contracts/east-blue-saga-simulation.schema.json`
- `runtime/east-blue-2d/character-index.json`
- `runtime/east-blue-2d/characters/*/atlas.png`
- `runtime/east-blue-2d/characters/*/character.json`

Review before integration:

- `renders/east-blue-2d/east-blue-character-atlas-catalog.png`
- `renders/east-blue-2d/east-blue-saga-scene-board.png`
- `renders/east-blue-2d/east-blue-saga-sampler.mp4`

The manifest is `runtime_verified` but intentionally
`integration_ready: false`. The app proof described here is the remaining
promotion gate.

## Hard rules

1. Add `NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS=1`; default behavior is off.
2. Never fetch a scene before its verified chapter start.
3. Never enable a scene whose `readiness` is not `runtime_ready`.
4. Never replace missing art with the old rigid character GLBs.
5. Run at most one close simulation at a time.
6. Dispose cloned textures, materials, planes, and FX geometry on exit.
7. Backward chapter scrub resets local time, actors, FX, and environment cues.
8. Reduced motion shows a safe static pose with autoplay and animated FX off.
9. The app owns map anchors and chapter state; the asset contract owns local
   choreography.

## Recommended first proof

Use `baratie-zoro-vs-mihawk` at its verified chapter-51 gate. It has two actors,
three FX cues, obvious motion contrast, and an existing Baratie location. A
successful proof means:

- both actors stay visually readable at intended close-map zoom;
- Zoro and Mihawk occupy the correct local sides and face the camera;
- pose changes are stepped while transforms interpolate smoothly;
- no texture is fetched at chapter 50;
- chapter 51 plays once and holds the final pose;
- scrubbing to 50 unloads it, and returning to 51 restarts at time zero;
- reduced motion shows the safe hold without repeated slash/impact FX;
- no material, texture, or RAF loop survives disposal.

After that proof, enable the other eleven `runtime_ready` scenes through data,
not scene-specific components.

## Renderer shape

Use the app's existing Three.js/MapLibre custom-layer lifecycle if present. A
single generic `StorySimulationLayer` should own:

- asset registry and texture cache;
- one local stage group anchored to the scene's map place;
- one plane per actor track;
- deterministic scene time derived from app state;
- event dispatch to a small reusable FX registry;
- pause, reset, and disposal.

Each character metadata file describes a 3-column by 2-row atlas. For a
top-left frame row/column in Three.js texture coordinates:

```ts
texture.repeat.set(1 / 3, 1 / 2)
texture.offset.set(column / 3, 1 - (row + 1) / 2)
```

Clone the cached base texture per actor plane before changing `repeat` or
`offset`. Otherwise two actors using the same atlas will overwrite each
other's pose.

Suggested material settings:

```ts
new THREE.MeshBasicMaterial({
  map: actorTexture,
  transparent: true,
  alphaTest: 0.05,
  depthWrite: false,
  side: THREE.DoubleSide,
})
```

Use each actor package's `map_height` and frame pivot. Keep the plane
camera-facing around the local up axis; do not flatten it onto the map. Honor
the authored `z` ordering with a small render-order or local-depth separation.

## Deterministic evaluation

For local scene time `t`:

1. Select the last keyframe whose `t <= localTime` for the pose.
2. Find the next keyframe, if any.
3. Interpolate numeric values `x`, `y`, `scale`, `rotation`, and `opacity`.
4. Apply authored `ease` only to numeric interpolation.
5. Never blend poses; change atlas cells at the authored keyframe.
6. Fire an FX event once when local time crosses its `t`.
7. Rebuild event-fired state whenever time moves backward.

The local stage coordinates are normalized. Convert `x` and `y` to a
scene-specific world-unit span after the geographic anchor is resolved. Do not
store MapLibre coordinates in the asset contract.

## FX v1

Implement a small registry, not one bespoke class per scene:

- line/arc sprite: `slash`, `black-blade-slash`, `rubber-stretch`;
- radial sprite or shader quad: `impact`, `promise-pulse`, `farewell-pulse`,
  `era-pulse`, `route-pulse`;
- particle emitter: `smoke`, `dust`, `walk-up-dust`, `rain`, `wind`;
- burst/debris emitter: `explosion`, `armor-break`, `scaffold-break`,
  `structure-collapse`;
- visibility/offset helper: `detach`, `speed-lines`, `wave`, `lightning`.

It is acceptable for the first proof to map unsupported event types to a
generic pulse, provided the event remains deterministic and the fallback is
logged during development.

## Chapter and readiness filter

Pseudo-code:

```ts
const eligible =
  flagEnabled &&
  scene.readiness === 'runtime_ready' &&
  scene.chapter_gate.verification === 'verified' &&
  currentChapter >= scene.chapter_gate.start

const activeWindow =
  eligible && currentChapter <= scene.chapter_gate.end
```

Do not preload ineligible scene assets. After the active window, the app may
show the final safe pose or an explicit replay affordance, but it should not
loop the fight indefinitely.

The two disabled v1 scenes are:

- `zoro-joins-at-shells-town` — missing Morgan and Koby;
- `smoker-dragon-storm-escape` — missing Dragon and Tashigi.

## Suggested app-owned files

Adapt names to the current repo instead of forcing a new architecture:

- `lib/story-simulations/types.ts` — schema-derived types;
- `lib/story-simulations/evaluate-track.ts` — pure deterministic evaluator;
- `components/map/story-simulation-layer.ts` — MapLibre/Three lifecycle;
- `components/map/story-simulation-fx.ts` — small FX registry;
- `public/story-simulations/east-blue/...` — copied runtime data/assets;
- unit tests for gating, interpolation, backward scrub, and UV selection.

If the app already has equivalent GLB-layer lifecycle or asset-manifest code,
extend it rather than creating parallel loading/disposal systems.

## Verification checklist

- Validate copied hashes against `manifests/east-blue-2d.json`.
- Confirm feature flag off means zero East Blue atlas network requests.
- Confirm chapter-before-start means zero scene atlas network requests.
- Confirm `art_partial` means zero requests even at its chapter.
- Test first and last atlas frame UVs in both rows.
- Test same-atlas simultaneous actors with independent texture clones.
- Test numeric interpolation and step pose selection.
- Test forward event firing and backward event reset.
- Test reduced motion and hidden-document pause.
- Test scene replacement and full resource disposal.
- Measure texture memory and frame time on the real target device/browser.

## Do not integrate

- `runtime/encounters/*.glb` as visible character art;
- `source/encounters/*.blend`;
- `renders/encounters/*`;
- raw keyed/source sheets under `art/east-blue/`;
- either `art_partial` scene;
- future Crocodile, Robin, or Kuma registry entries as runtime content.

Those future entries are roadmap anchors only. Their art and chapter contracts
must be built and verified in their own saga batches.
