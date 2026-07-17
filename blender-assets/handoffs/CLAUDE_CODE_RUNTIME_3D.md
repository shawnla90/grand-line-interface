# Claude Code handoff: load the completed Blender runtime batch

The asset-production pass is complete. Do not regenerate or edit the `.blend`
files from the app-owning session.

## Read first

- `blender-assets/manifests/runtime-3d.json`
- `blender-assets/manifests/narrative-blockouts.json`
- `blender-assets/queue/asset-requests.json`
- `blender-assets/WORKFLOW.md`

The registry has 16 validated GLBs: the already-integrated Knock-Up Stream and
Wano pilots plus 14 scene systems. All fourteen new units are
`integration_ready` and use `NEXT_PUBLIC_RUNTIME_3D_ASSETS`.

## Integration order

1. Reuse the app's existing MapLibre/Three custom-layer implementation; do not
   create one loader per island.
2. Update the app-owned sync step for schema version 2. Copy only `glb` and
   `fallback.path` for queue entries whose state is `integration_ready`.
3. Load one scene at a time in this order: Fish-Man Island, Loguetown, Water 7,
   Conomi/Arlong Park, Whisky Peak, Dressrosa/Green Bit, Skypiea sky system,
   Sabaody grove network, Totto Land, Tarai system, Amazon Lily, Mary Geoise,
   Arabasta, then Zou/Zunesha.
4. Read glTF node extras before first render. Enforce `reveal_chapter`; keep
   `default_hidden=true` or `gate_confidence=chapter_to_verify` nodes hidden.
5. Use `safe_full_scene_chapter` for the complete PNG fallback. It is intentionally
   later than the base scene gate when the fallback contains later landmarks.
6. Mercator closeups may use the GLB. Globe, unsupported WebGL, and lower-end
   paths use the transparent fallback.
7. Unload and dispose geometry, materials, and textures when hidden, refogged,
   projected to globe, or unmounted.

## Special placement rules

- Totto Land is a 35-island system (Whole Cake plus 34 subsidiaries), not one
  cake island. Unknown subsidiary gates remain default-hidden.
- The Tarai Current triangle and Water 7 rail bearings are local relationship
  schematics. Do not project their local layout as canon world coordinates.
- Zou/Zunesha is a moving entity. Its derived atlas anchor opens the encounter;
  it is not a permanent canon coordinate.
- Sabaody is the 79-root network. Never substitute the old three-grove study.
- Skypiea's late Giant Jack/Belfry collection remains withheld because its
  exact chapter gate is unresolved.
- The old `whole-cake-island`, `impel-down`, and `sabaody-archipelago` queue
  entries remain `study_only`; their replacement systems are the loadable units.

## Acceptance

- `python3 blender-assets/scripts/verify_runtime_3d.py` passes all 16 models.
- `python3 blender-assets/scripts/verify_priority_narrative_blockouts.py` passes
  all 11 narrative scenes.
- A scene is never fetched before its base chapter gate.
- A GLB node is never rendered before its component gate.
- Globe projection never receives a naive mercator-only model matrix.
- Feature flag off preserves current behavior.
- No `chapter_to_verify` value is replaced with an invented chapter.
