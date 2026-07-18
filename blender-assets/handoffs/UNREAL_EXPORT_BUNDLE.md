# Unreal export bundle handoff

The engine-neutral East Blue bundle is produced from the tracked Grand Line
asset factory and consumed by the separate `grand-line-unreal` repository.
Unreal does not reach into this package at editor or runtime.

## Build and verify

From the `dead-reckoning` repository root:

```bash
python3 blender-assets/scripts/build_unreal_export_bundle.py
python3 blender-assets/scripts/verify_unreal_export_bundle.py
```

Output: `blender-assets/exports/unreal/east-blue-v1/`

Current contract:

- 14 illustrated character/tableau atlas packages;
- 84 stepped pose frames;
- 12 verified, runtime-ready East Blue simulations;
- the existing Loguetown/Roger runtime-blockout GLB;
- two unfinished scenes listed as excluded rather than runnable;
- stable relative paths and SHA-256 receipts for every file.

`baratie-zoro-vs-mihawk` is already runnable as illustrated actor tracks. Its
original encounter-deck environment and temporary original ship proxy remain
explicit vertical-slice blockers; they must enter the asset factory and bundle
through the same manifest/hash gate.

## Consumer sync

From the sibling Unreal repository:

```bash
python3 Scripts/sync_bundle.py \
  --source ../dead-reckoning/blender-assets/exports/unreal/east-blue-v1
python3 Scripts/validate_source_art.py
python3 -m unittest discover -s Tests -p 'test_*.py'
```

The consumer snapshots the bundle into `SourceArt/Imported/east-blue-v1`.
Generated Unreal assets belong under `/Game/GrandLine/Generated`; handmade
levels, materials, Blueprints, Niagara, Water, and gameplay belong under
`/Game/GrandLine/Native`.
