# GitHub handoff: Blender asset factory

When this package is read from the Grand Line Interface repository, its root is
`blender-assets/`. It is intentionally self-contained: Claude Code can inspect
contracts, source scenes, renders, manifests, and handoffs without relying on
chat history.

## Start here

1. `WORKFLOW.md` — production states and ownership boundary.
2. `queue/asset-requests.json` — current maturity and the next step per asset.
3. `contracts/narrative-scene-index.json` — eleven chapter-aware place systems.
4. `manifests/runtime-3d.json` — permanent geography and transition runtime assets.
5. `manifests/narrative-blockouts.json` — editable studies that must not ship yet.
6. `handoffs/CLAUDE_CODE_RUNTIME_3D.md` — Skypiea runtime pilot instructions.
7. `handoffs/CLAUDE_CODE_NARRATIVE_SYSTEMS.md` — future event/place/route registry.
8. `CHARACTER_SIMULATION_ROADMAP.md` — phased character rig and encounter plan.
9. `manifests/east-blue-2d.json` — verified illustrated East Blue runtime package.
10. `contracts/east-blue-saga.simulation.json` — 14 chapter-gated story scenes.
11. `runtime/east-blue-2d/character-index.json` — 14 actor/tableau atlases.
12. `handoffs/CLAUDE_CODE_EAST_BLUE_2D.md` — app renderer and integration brief.
13. `art/east-blue/IMAGEGEN_PROVENANCE.md` — source generation and rights posture.
14. `provenance/sol-session-usage.json` — measured Codex Sol workload snapshot.
15. `handoffs/CLAUDE_CODE_GRAND_LINE_ANIMATION_NEXT.md` — verified journey
    through Enel and Jet Gatling, plus the ordered CP9/Sabaody/Marineford queue.
16. `manifests/story-simulations/skypiea-saga-2d-v1.json` — promoted
    Luffy/Enel climax pack.
17. `manifests/story-simulations/enies-lobby-saga-2d-v1.json` — promoted
    four-fight CP9 pack from first Gear Second through Jet Gatling.

## Path translation

Older generated evidence records retain the production machine's absolute
paths. In a checkout, translate them as follows:

- `/Users/shawnos.ai/dead-reckoning/` means the repository root.
- `/Users/shawnos.ai/dead-reckoning-blender-assets/` means `blender-assets/`.

Hashes remain the authority. The absolute string is provenance, not a runtime
dependency.

## Rebuild from inside the repository

Set the app root explicitly for scripts that read atlas data:

```bash
export DEAD_RECKONING_REPO="$(git rev-parse --show-toplevel)"
python3 blender-assets/scripts/build_narrative_scene_contracts.py
python3 blender-assets/scripts/verify_narrative_scene_contracts.py
```

Blender builds require Blender 4.5.3 LTS or a deliberately tested compatible
version. The committed `.blend` files and renders mean a reader does not need
Blender merely to review the work.

## Integration rule

Only queue entries marked `integration_ready` may be copied into the app's
runtime public assets. A `scene_3d` or `3d_blockout_not_final_art` entry is
reviewable source—not permission to integrate it. MapLibre continues to own
chapter gates, geographic anchors, route state, and object lifetime.

The character track now uses illustrated 2.5D atlases. East Blue, the ten-scene
Arabasta pack, Luffy/Enel, and the four-fight Enies Lobby CP9 pack are
technically promoted behind the shared allowlist. Keep both East Blue
`art_partial` scenes disabled and do not enable a future fight until its own
browser proof passes.

All older rigid-part character GLBs are `motion_blockout` references. Their
wooden mannequin visuals are superseded and must not be copied into the app.

The generalized `arabasta-saga-2d-v1` pack now contains 18 actor packages, 108
poses, and 10 verified scenes: Whisky Peak, Robin, Ace/Smoker, Fire Fist,
Sanji/Bon Clay, Nami/Miss Doublefinger, Zoro/Mr. One, and the three distinct
Luffy/Crocodile encounters. It is
`integration_ready: true` and invisible unless the web build explicitly
allowlists it. Continue from `handoffs/CLAUDE_CODE_GRAND_LINE_ANIMATION_NEXT.md`.

The two promoted later-saga packs add 10 actor atlases and 60 poses. Skypiea
authors rubber immunity through the Golden Rifle/bell finish. Enies Lobby now
authors four CP9 fights: Luffy/Blueno, Sanji/Jabra, Zoro/Kaku, and Luffy/Lucci.
Its shared 47/47 browser receipt proves exact chapter-gated lazy loading, scene
replacement, backward reset, one-shot Gear Second/Diable Jambe/Santoryu/Jet
Gatling audio, and silent reduced motion.
