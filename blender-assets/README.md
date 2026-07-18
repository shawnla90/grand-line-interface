# Grand Line Interface — Blender island plates

This directory is the isolated art-production track for the atlas in
`/Users/shawnos.ai/dead-reckoning`. The atlas is read-only here. No file from
this directory is copied into or wired into the app by the build.

The operating model is documented in `WORKFLOW.md`. New requests enter
`queue/asset-requests.json`; runtime-ready GLBs are registered in
`manifests/runtime-3d.json`; Claude Code receives a paste-ready app integration
brief from `handoffs/`.

Compound places are specified first in `contracts/`. The contract builders
combine the raw atlas API, richer generated island records, and a small cited
topology overlay without writing to the app repository.

`scripts/build_system_sketches.py` turns those verified component graphs into
editable SVG system sketches plus PNG previews. These are topology briefs for
Blender, not runtime map art.

The v2 narrative batch contains eleven chapter-aware, loader-ready runtime
blockouts, including Loguetown, Dressrosa/Green Bit, Zou/Zunesha, Sabaody's
79-grove network, the full Skypiea sky system, and the Water 7 Sea Train
network. Every scene has an editable `.blend`, transparent fallback, GLB,
sidecar, contract, and queue entry. They are deliberately described as runtime
blockouts rather than final cinematic art.

`manifests/runtime-3d.json` is the complete integration boundary: 16 models,
covering Claude's two transition pilots and the fourteen remaining scene
systems. Rebuild/verify the new batch with:

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background --python blender-assets/scripts/build_runtime_scene_batch.py
python3 blender-assets/scripts/build_runtime_registry.py
python3 blender-assets/scripts/finalize_runtime_scene_batch.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 blender-assets/scripts/verify_priority_narrative_blockouts.py
```

## Unreal export bundle

Unreal is a separate renderer, not a replacement for the web atlas or this
asset factory. Build its deterministic East Blue SourceArt bundle with:

```bash
python3 blender-assets/scripts/build_unreal_export_bundle.py
python3 blender-assets/scripts/verify_unreal_export_bundle.py
```

The exporter copies only manifest-approved runtime derivatives into
`exports/unreal/east-blue-v1/`. It fails on missing or drifted hashes, duplicate
IDs, unverified chapter gates, and unfinished scenes. Raw character-generation
sheets are never exported.

## Arabasta story-simulation Batch A

The first generic saga pack is signed and web proven. `arabasta-saga-2d-v1`
contains 6 source-free runtime atlases, 36 poses, and 4 verified scenes for
Whisky Peak, Miss All Sunday's arrival, Ace's Nanohana intervention, and his
chapter-159 destruction of the Billions' five-ship convoy. It is
technically integration-ready but disabled unless the app build explicitly
allowlists it with `NEXT_PUBLIC_STORY_SIMULATION_PACKS`.

Start with:

- `handoffs/CLAUDE_CODE_ARABASTA_BATCH_A.md`
- `manifests/story-simulations/arabasta-saga-2d-v1.json`
- `contracts/story-simulations/arabasta-saga-2d-v1.simulation.json`
- `proofs/arabasta-saga-2d-v1-web-proof.json`
- `renders/story-simulations/arabasta-saga-2d-v1/scene-board.png`

Raw source sheets and editable alpha intermediates remain in the isolated asset
factory and are intentionally absent from this source-free package.

## Pilot

`fish-man-island` is a top-down RGBA plate built around the atlas's exact
deterministic coastline seed. It uses the proposed 128-point hero ring and
keeps all visible pixels inside that footprint. The image adds visual ideas
that the flat terrain layer cannot carry alone: deep teal murk, caustic arcs,
surface light shafts, coral fading beneath a glassy dome, and warm settlement
light.

## Additional plates

- `whole-cake-island` — central-island palette/massing study only; the real
  integration unit is the 35-island Totto Land system (one center plus 34
  subsidiary islands)
- `impel-down` — underwater-depth study only; the real integration unit also
  includes Marineford, Enies Lobby, the Gates of Justice, and Tarai Current
- `sabaody-archipelago` — a three-grove palette/material study only; the real
  integration unit is the cited 79-tree mangrove network in
  `contracts/sabaody-grove-network.visual.json`

Build all three with:

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background \
  --python /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_additional_plates.py \
  -- --resolution 2048
```

For a focused art-direction rerender, add `--only <slug>`; repeat the flag to
select more than one plate. Existing manifest entries are preserved.

Verify them with:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_additional_plates.py
```

The two studies above must not be promoted to runtime until their system-level
contracts have advanced through component sketches and a system proof.

## Vertical transition sprites

The Knock-Up Stream and Wano waterfall are portrait, transparent 2.5D assets
rather than coastline plates. Each `.blend` contains a 120-frame proxy showing
the ship's intended direction; the app's real ship marker still owns runtime
motion.

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background \
  --python /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_vertical_transitions.py

python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_vertical_transitions.py
```

Skypiea is designed for a geographic MapLibre image source between the current
`SKY_BASE` and `SKY_BODY`. Wano is designed as a screen-space marker anchored
at the southern waterfall; its exact chapter beats remain a later canon/app
verification task.

The scene is original procedural art. It does not use anime frames, manga
panels, franchise logos, or downloaded textures.

## Viewing the real 3D depth

The production PNGs are deliberately top-down or portrait-composited, so they
can hide how much geometry exists. Perspective review renders live in
`renders/perspective/`, with honest maturity labels in its `manifest.json`.

To inspect an editable scene, open any file from `source/` in Blender, press
`Home` to frame the scene, switch the viewport to Material Preview or Rendered,
and orbit with the middle mouse button. Skypiea and Wano also contain a
120-frame preview ship proxy; that proxy is excluded from runtime GLBs.

## Build

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background \
  --python /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_fishman_plate.py \
  -- --resolution 2048
```

Outputs:

- `source/fish-man-island.blend` — editable source scene
- `renders/fish-man-island.png` — 2048px RGBA production plate
- `renders/fish-man-island-preview.png` — lightweight review image
- `geometry/fish-man-island-coastline.geojson` — exact alpha/shape contract
- `manifests/island-plates.json` — future MapLibre integration contract

Verify the package with:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_outputs.py
```

## Ownership boundary

This track may read the atlas plan, generated island data, canon coordinates,
voyage/presence weighting, and terrain scripts. It must never write to the
atlas repo. Integration is a later app-owning task because the current atlas
does not yet load raster plates.

When integration begins, use the manifest's four `coordinates` directly for a
MapLibre image source and gate the raster layer with the same constructive
chapter reveal used by the coastline. Do not infer bounds from transparent
pixels; the manifest already pins the camera extent.
