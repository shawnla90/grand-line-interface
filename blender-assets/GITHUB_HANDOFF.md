# GitHub handoff: Blender asset factory

When this package is read from the Grand Line Interface repository, its root is
`blender-assets/`. It is intentionally self-contained: Claude Code can inspect
contracts, source scenes, renders, manifests, and handoffs without relying on
chat history.

## Start here

1. `WORKFLOW.md` — production states and ownership boundary.
2. `queue/asset-requests.json` — current maturity and the next step per asset.
3. `contracts/narrative-scene-index.json` — eleven chapter-aware place systems.
4. `manifests/runtime-3d.json` — all 16 validated runtime models and fallbacks.
5. `manifests/narrative-blockouts.json` — eleven loader-ready narrative scenes.
6. `handoffs/CLAUDE_CODE_RUNTIME_3D.md` — the next app integration batch.
7. `handoffs/CLAUDE_CODE_NARRATIVE_SYSTEMS.md` — chapter/node/route safety rules.
8. `provenance/sol-session-usage.json` — measured Codex Sol workload snapshot.
9. `handoffs/UNREAL_EXPORT_BUNDLE.md` — deterministic Unreal SourceArt export
   and the separate client-project boundary.
10. `handoffs/CLAUDE_CODE_ARABASTA_BATCH_A.md` — promoted generic story pack,
    web proof, opt-in flag, and Batch B continuation.
11. `manifests/story-simulations/arabasta-saga-2d-v1.json` — signed five-actor
    Arabasta manifest with its web-proof receipt.

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
runtime public assets. Sixteen entries now meet that gate: the two transition
pilots plus fourteen scene systems. The old Whole Cake, Impel Down, and
three-grove Sabaody files remain `study_only` and must never be loaded as final
geography. MapLibre continues to own chapter gates, geographic anchors, route
state, node visibility, and object lifetime.

## Unreal SourceArt export

The Unreal client never reads arbitrary files from this package. Build and
verify its exact East Blue input with:

```bash
python3 blender-assets/scripts/build_unreal_export_bundle.py
python3 blender-assets/scripts/verify_unreal_export_bundle.py
```

The generated bundle contains all 14 illustrated atlas packages, the 12
runtime-ready story simulations, the existing Loguetown runtime GLB, the
original Baratie encounter-deck blockout, and the original ship proxy. It
excludes both `art_partial` scenes and fails on source hash drift, missing
anchors, or unverified chapter gates.

## Generic saga packs

The app can now consume source-free packs under
`runtime/story-simulations/<pack-id>/` through one shared loader. Arabasta
Batch A is the first promoted pack. It remains off by default; the technical
promotion receipt proves readiness, while the web build allowlist controls
actual exposure. Continue with Arabasta Batch B through JSON, illustrated
atlases, and reusable FX rather than scene-specific React components.
