# Continuous Blender → MapLibre asset factory

This directory owns art production. `/Users/shawnos.ai/dead-reckoning` owns the
application. The two tracks never edit the same files.

## The loop

1. **Request** — Shawn names an island, transition, ship, creature, landmark,
   or environmental event in this task.
2. **Identify** — determine whether the request is an island, archipelago,
   connected facility system, vertical transition, moving structure, or
   chapter-dependent state. Never default every location record to “island.”
3. **Visual contract** — join raw API identity, generated research records,
   cited topology overrides, chapter state, atlas anchors, and unresolved
   questions. The contract defines components and relationships before art.
4. **System sketch** — for compound entities, render the component graph and
   unresolved topology as a labeled schematic before producing beauty art.
5. **2.5D proof** — create a transparent map-scale plate or transition sprite.
   This establishes silhouette, palette, composition, and integration bounds.
6. **3D scene** — deepen the approved proof into editable Blender geometry,
   materials, lights, volumetrics, and animation reference.
7. **Runtime export** — produce an optimized GLB plus PNG fallback, hashes,
   bounds, and integration metadata.
8. **Validation** — verify alpha, GLB headers, hashes, file-size budgets, and
   importability. Keep canon guesses explicitly unset.
9. **Handoff** — Claude Code reads the manifests and integrates only approved
   assets behind chapter gates and a feature flag.

## State machine

`requested → identified → visual_contract → system_sketch → proof_2_5d → scene_3d → runtime_glb → integration_ready → integrated`

Revisions can move an asset from any later state back to `proof_2_5d` or
`scene_3d` without touching the app. The runtime manifest is the boundary;
chat history is not an integration contract.

## Accuracy gate

Before sketching, run:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_visual_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_visual_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_system_sketches.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_narrative_scene_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_narrative_scene_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_intake_scene_boards.py
```

The builder keeps four evidence layers distinct:

- the raw API establishes upstream identity and reveals coverage gaps;
- generated wiki records add names, debuts, affiliations, and source links;
- `research/visual-topology-overrides.json` adds only cited relationships that
  neither API encodes;
- atlas coordinates remain render anchors only when marked derived. They are
  never treated as evidence for the relative layout of a compound place.

System entities get both component sketches and one system-level proof. A
single attractive component cannot graduate on behalf of the whole system.

Narrative entities add the hierarchy `place -> subregion -> landmark -> event
scene -> temporal variant`. Moving world entities use a moving anchor rather
than a permanent atlas position. Transit systems add a chapter-gated route
graph; MapLibre owns the geographic line while Blender owns vehicles,
stations, spray, storm volumes, and close-up structures.

The current priority blockouts can be rebuilt and verified with:

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background \
  --python /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_priority_narrative_blockouts.py

python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_priority_narrative_blockouts.py
```

## Runtime policy

- Globe/orbit/lower-end devices use the transparent PNG fallback.
- Supported close-up scenes may load the GLB through a MapLibre custom 3D
  layer.
- The atlas owns chapter gating, camera state, model lifetime, and ship motion.
- Blender's ship proxy is preview-only and is excluded from GLB exports.
- Models unload when hidden; they are never fetched before their chapter gate.

## Current completed batch

The runtime registry now contains 16 validated models: two vertical transitions
and fourteen scene systems. The non-transition batch uses
`NEXT_PUBLIC_RUNTIME_3D_ASSETS`; the existing pilots retain
`NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS`.

Runtime scenes carry `component_id`, `reveal_chapter`, `gate_confidence`, and
`default_hidden` in glTF node extras. The app loader must apply those gates
before first render. A complete PNG fallback is gated by
`safe_full_scene_chapter`; it cannot reveal or hide individual nodes.

The runtime files are optimized procedural blockouts intended for map-scale
closeups. A future material/detail pass may improve them without changing the
manifest or loader contract.
