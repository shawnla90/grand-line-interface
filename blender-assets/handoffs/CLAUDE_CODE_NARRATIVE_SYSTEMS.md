# Paste into the Claude Code session that owns `/Users/shawnos.ai/dead-reckoning`

The Blender asset track has added a chapter-aware narrative geography batch.
Do not edit the asset workspace and do not copy any new `.blend` or blockout
render into the app. None of these v2 scenes is `integration_ready` yet.

## Read first

- `/Users/shawnos.ai/dead-reckoning-blender-assets/contracts/narrative-scene-index.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/contracts/narrative-scene.schema.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/queue/asset-requests.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/manifests/narrative-blockouts.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/WORKFLOW.md`

The new hierarchy is:

`place -> subregion -> landmark -> event scene -> temporal variant`

Moving entities add a moving anchor. Transit systems add a route graph. Every
variant is constructive: render only the latest verified state whose reveal
chapter is at or below the current reader chapter. A `chapter_to_verify` state
must remain disabled.

## Batch inventory

The contracts cover Arlong Park/Conomi, Arabasta, Cactus Island/Whisky Peak,
Dressrosa/Green Bit, Zou/Zunesha, Amazon Lily, Mary Geoise, Sabaody's 79-grove
network, the actual Skypiea sky-island system, Loguetown's execution platform,
and the Water 7 Sea Train network.

Loguetown and Water 7 have editable 3D blockouts and 1400x900 review renders,
but their manifest deliberately says `runtime_export: false`. Treat the
blockouts as proof of scene organization, camera, animation, and collection
ownership—not shippable art.

## Water 7 route behavior

Read:

- `/Users/shawnos.ai/dead-reckoning-blender-assets/contracts/water-7-sea-train-network.visual.json`
- `/Users/shawnos.ai/dead-reckoning-blender-assets/sketches/intake/water-7-sea-train-network.svg`

The app-side architecture should eventually separate:

1. **MapLibre route UI** — chapter-gated line and station markers on the globe.
2. **Blender runtime layer** — animated train, station structures, wheel spray,
   steam, and Aqua Laguna close-up state.
3. **Narrative state** — Puffing Tom's first network reveal at Chapter 322,
   an Aqua Laguna/Rocketman state whose exact chapter is still unverified, and
   Puffing Ice at Chapter 656.

The Sea Train rails sit just below the ocean surface and sway with the tides.
Known connected nodes are Water 7, Enies Lobby, Pucci, St. Poplar, and San
Faldo; Shift Station is an intermediate station/lighthouse. Current atlas
coordinates are deterministic placement anchors, not canon route geometry.
Any temporary globe line must be labeled `derived_schematic` in data and UI;
do not present its branch bearings as canon.

## Semantic safety

- Do not integrate the old three-grove Sabaody scene. It is now a material and
  palette study; the replacement unit is `sabaody-grove-network`.
- Do not treat the existing Knock-Up Stream GLB as all of Skypiea. It is only
  the transition into the future `skypiea-sky-system` scene.
- Do not make Amazon Lily itself serpent-shaped. Current evidence supports
  serpent culture/architecture and a city inside a mountain-top hollow, not a
  serpent island silhouette.
- Do not connect Green Bit's bridge to Doflamingo's palace. The bridge connects
  Green Bit to northern Dressrosa; the palace belongs on the central King's
  Plateau in the pre-Pica state and moves in the later terrain variant.
- Do not fix Zou to a permanent canon coordinate. Zunesha is the moving anchor.
- Do not expose late Mary Geoise/Pangaea Castle interiors in its early exterior
  state.
- Do not insert event actors permanently into free roam. Roger, crowds,
  lightning, Birdcage, battle damage, and similar elements belong to gated
  scene-state collections.

## Recommended app preparation when this work is scheduled

Add a small app-owned narrative visual registry that can represent static
landmarks, temporal variants, event scenes, moving anchors, and routes without
loading any asset. Keep it data-only and feature-flagged first. It should be
able to report why a scene is hidden: `chapter_locked`, `gate_unverified`,
`asset_not_ready`, `projection_unsupported`, or `distance_lod`.

Do not wire the new Blender blockouts. Stop after the registry/data model and
report exact files changed, build result, and how existing map behavior stays
unchanged while the feature flag is off.
