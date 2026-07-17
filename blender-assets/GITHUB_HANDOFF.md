# GitHub handoff: Blender asset factory

When this package is read from the Grand Line Interface repository, its root is
`blender-assets/`. It is intentionally self-contained: Claude Code can inspect
contracts, source scenes, renders, manifests, and handoffs without relying on
chat history.

## Start here

1. `WORKFLOW.md` — production states and ownership boundary.
2. `queue/asset-requests.json` — current maturity and the next step per asset.
3. `contracts/narrative-scene-index.json` — eleven chapter-aware place systems.
4. `manifests/runtime-3d.json` — the only current runtime-ready 3D pilots.
5. `manifests/narrative-blockouts.json` — editable studies that must not ship yet.
6. `handoffs/CLAUDE_CODE_RUNTIME_3D.md` — Skypiea runtime pilot instructions.
7. `handoffs/CLAUDE_CODE_NARRATIVE_SYSTEMS.md` — future event/place/route registry.
8. `provenance/sol-session-usage.json` — measured Codex Sol workload snapshot.

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

