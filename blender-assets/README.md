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

The v2 narrative batch adds eleven chapter-aware systems, including Loguetown,
Dressrosa/Green Bit, Zou/Zunesha, Sabaody's 79-grove network, the full Skypiea
sky system, and the Water 7 Sea Train network. Six priority system boards live
in `sketches/intake/`. Loguetown and Water 7 also have editable Blender
blockouts in `source/` and review renders in `renders/blockouts/`; they are not
runtime exports yet.

## Character and encounter simulations

`CHARACTER_SIMULATION_ROADMAP.md` defines the approved character direction:
recognizable illustrated 2.5D actors on camera-facing planes, deterministic
movement tracks, and lightweight local 3D effects. The earlier rigid-part GLBs
are preserved as motion studies only; their mannequin art is superseded and no
longer approved for app integration.

The East Blue v1 asset pack contains 14 actor/tableau atlases, 84 reusable
poses, and 14 chapter-gated scenes spanning chapters 1–100. Twelve scenes are
runtime-ready; Shells Town and the Loguetown storm escape remain disabled until
their missing supporting characters are drawn.

Build, preview, and verify the 2.5D package with:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_east_blue_2d.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/render_east_blue_2d_preview.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_east_blue_2d.py
```

Start with `manifests/east-blue-2d.json` and
`contracts/east-blue-saga.simulation.json`. App instructions live in
`handoffs/CLAUDE_CODE_EAST_BLUE_2D.md`; visual review files live in
`renders/east-blue-2d/`. A source-free injection bundle is available at
`dist/east-blue-2d-runtime-v1.zip`.

The first generalized saga pack, `arabasta-saga-2d-v1`, is also built and web
proven. It contains 18 actor packages, 108 poses, and 10 verified scenes: the
original Whisky Peak, Robin, Ace/Smoker, and Fire Fist beats plus Sanji/Bon
Clay, Nami/Miss Doublefinger, Zoro/Mr. One, and all three distinct
Luffy/Crocodile encounters. The signed pack is marked `integration_ready:
true`, but remains invisible unless the web build explicitly allowlists it.

Two later saga packs are now promoted through the same generic pipeline:
`skypiea-saga-2d-v1` (Luffy/Enel, chapters 279–302) and
`enies-lobby-saga-2d-v1` (four CP9 fights across chapters 387–427). Together
they add 10 signed atlases, 60 poses, five scenes, and 41 timed FX events.
Enies Lobby now progresses from Luffy/Blueno's first Gear Second through
Sanji/Jabra's first Diable Jambe, Zoro/Kaku's Asura finish, and Luffy/Lucci's
Jet Gatling. The matching local-prototype Gear Second, Diable Jambe, Santoryu,
and Gatling clips are bound to their authored visual events.

```bash
python3 scripts/build_story_simulation_pack.py --config art/arabasta/character-sheets.json
python3 scripts/render_story_simulation_pack.py \
  --config art/arabasta/character-sheets.json \
  --contract contracts/story-simulations/arabasta-saga-2d-v1.simulation.json
python3 scripts/verify_story_simulation_pack.py \
  --config art/arabasta/character-sheets.json \
  --contract contracts/story-simulations/arabasta-saga-2d-v1.simulation.json \
  --canon-intake research/story-scenes/arabasta-batch-a.json \
  --provenance art/arabasta/IMAGEGEN_PROVENANCE.md \
  --web-proof proofs/arabasta-saga-2d-v1-web-proof.json
```

Open `handoffs/CLAUDE_CODE_GRAND_LINE_ANIMATION_NEXT.md` for the current proof
matrix, feature flag, and ordered continuation queue.

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
