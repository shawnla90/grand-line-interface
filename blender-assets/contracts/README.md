# Visual contracts

These files are the boundary between canon/data research and art production.
They describe what the thing **is** before a script decides what it looks like.

Build and verify:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_visual_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_visual_contracts.py
```

Chapter-aware place, landmark, event, and transit contracts use the v2 schema:

```bash
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/build_narrative_scene_contracts.py
python3 /Users/shawnos.ai/dead-reckoning-blender-assets/scripts/verify_narrative_scene_contracts.py
```

These contracts introduce the production hierarchy `place -> subregion ->
landmark -> event scene -> temporal variant`. Moving entities and transit
networks may add a route graph beside that hierarchy. Any event with an
unverified chapter remains disabled until its gate is confirmed.

The builder joins three layers:

1. the raw location API for upstream coverage,
2. generated island records for richer names/debuts/sources, and
3. the small cited topology overlay in `research/visual-topology-overrides.json`.

Atlas coordinates are retained only as future render anchors. They are marked
as derived and are never used as proof of relative canon geography.
