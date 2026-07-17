# Paste into the Claude Code session that owns `/Users/shawnos.ai/dead-reckoning`

Integrate the first Blender runtime-3D pilot into the Grand Line Interface.
You own app code; the Codex Blender task owns art. Do not edit, regenerate, or
move the source `.blend` files.

## Read first

- `/Users/shawnos.ai/dead-reckoning-blender-assets/manifests/runtime-3d.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/manifests/vertical-transitions.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/WORKFLOW.md`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/queue/asset-requests.json`
- the current `components/WorldMap.tsx` and `components/skypiea.ts`

The app currently uses MapLibre GL JS 5.24.0 and toggles between globe and
mercator. `three` is not currently installed. Re-read every target before
editing because `WorldMap.tsx`, canon, normalize, and lens work are in flight.

## Pilot boundary

Start with **Skypiea only** behind
`NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS=1`. Do not wire Wano's climb chapters yet;
its manifest intentionally leaves them unset pending human verification.

1. Add the minimal Three.js/GLTFLoader dependency required to load the GLB.
2. Create a small custom MapLibre layer module rather than adding model-loader
   logic directly to `WorldMap.tsx`.
3. The custom layer must use `type: "custom"` and `renderingMode: "3d"`, share
   MapLibre's depth buffer, restore GL state, handle context loss/restoration,
   and dispose geometries/materials/textures on removal.
4. Convert the manifest anchor with `MercatorCoordinate.fromLngLat`; derive
   model scale from `meterInMercatorCoordinateUnits()` and manifest bounds.
5. Fetch the GLB only when all are true: feature flag enabled, chapter gate
   open, close zoom active, and the supported projection path is active.
6. On globe/orbit or unsupported WebGL, render the manifest's transparent PNG
   fallback. A naive mercator-only Three.js matrix must not be used on globe.
7. Keep ship motion owned by the existing pure `altitudeT(ch)` logic. The GLB
   deliberately excludes Blender's preview proxy.
8. Unload the GLB whenever it is hidden, the chapter refogs, projection changes,
   or the component unmounts.

## Asset paths

- GLB: `/Users/shawnos.ai/dead-reckoning-blender-assets/runtime/skypiea-knock-up-stream.glb`
- fallback: `/Users/shawnos.ai/dead-reckoning-blender-assets/renders/skypiea-knock-up-stream.png`

Choose an app-owned public/static destination and copy only the runtime GLB and
fallback required by the pilot. Do not make the app read files outside its repo
at runtime.

## Acceptance

- `npm run build` passes.
- Chapter <235 does not fetch or reveal the asset.
- Chapters 235–237 show the ascent; backward scrub removes/reverses it cleanly.
- Globe mode uses the fallback unless the custom renderer is explicitly made
  globe-aware with MapLibre projection data.
- Mercator close-up uses the GLB with correct depth and model cleanup.
- Feature flag off returns the current app byte-for-byte in behavior.
- No Wano chapter constants are invented.

Stop after the Skypiea pilot and report performance, bundle impact, and the
exact files changed before extending the mechanism to Wano.

## Semantic safety

Do not integrate the current `whole-cake-island` or `impel-down` scenes as
final geography. They have been demoted to component studies after the data
model was corrected. Their replacement integration units are:

- `/Users/shawnos.ai/dead-reckoning-blender-assets/contracts/totto-land.visual.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/contracts/world-government-tarai-system.visual.json`

Neither replacement has reached `integration_ready`. In particular, do not
draw canon-looking connections between the current independently jittered
atlas coordinates for Marineford, Impel Down, Enies Lobby, the Gates of
Justice, or the Tarai Current.

The later narrative geography batch is documented separately in
`/Users/shawnos.ai/dead-reckoning-blender-assets/handoffs/CLAUDE_CODE_NARRATIVE_SYSTEMS.md`.
Its Loguetown and Water 7 files are 3D blockouts with `runtime_export: false`;
do not integrate them as runtime assets.
