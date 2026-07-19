# Reverse Mountain / Twin Cape W1 animated-graybox execution receipt

**Completed:** 2026-07-18  
**Driving app:** `/Users/shawnos.ai/dead-reckoning`  
**Asset authority:** `/Users/shawnos.ai/dead-reckoning/blender-assets`  
**Git:** changes are intentionally uncommitted and unpushed

## Outcome

Reverse Mountain is now a real chapter-driven runtime sequence, not only a visual contract. The globe approaches the Red Line, the Merry rides the ascent and descent currents, the chapter-102 encounter preserves the spoiler-safe `Unidentified giant whale` label, Twin Cape and Crocus reveal at chapter 103, the Laboon promise plays at chapter 104, and the Merry departs for Whisky Peak at chapter 105.

The app owns story time, chapter gates, camera, labels, loading, culling, and reduced motion. Blender owns the local-theatre geometry, tagged nodes, reusable motion clips, fallback frame, and procedural-effect masks. The existing MapLibre chase remains the only camera loop.

## Built asset

- Source: `blender-assets/source/reverse-mountain-twin-cape-voyage.blend`
- Runtime GLB: `blender-assets/runtime/reverse-mountain-twin-cape-voyage.glb`
- Sidecar: `blender-assets/runtime/reverse-mountain-twin-cape-voyage.model.json`
- Fallback: `blender-assets/renders/runtime/reverse-mountain-twin-cape-voyage.png`
- Generator: `blender-assets/scripts/build_reverse_mountain_graybox.py`
- Contract: `blender-assets/contracts/reverse-mountain-twin-cape-voyage.visual.json`

Measured GLB facts:

- 1,307,736 bytes, 18,996 triangles, 9,584 vertices, 50 objects, and 16 materials;
- 12 exact addressable component IDs;
- 21 exact named glTF animation clips;
- five signed 256 x 256 RGBA procedural masks;
- chapter-102-safe 1200 x 900 alpha fallback;
- SHA-256 `2accbf7f105a76f6c9b35a6d62c508d1730de9634c0018b8f7052df6a2e60d29`.

The delivered model is `LOD1_LOCAL_THEATRE`. LOD0 close-in, LOD2 globe, and componentized LOD3 remain promotion work. Crocus and the Straw Hats remain 2.5D identity anchors rather than generic low-quality 3D figures.

## Runtime work

- `AnimationMixer` now receives named actions and samples absolute chapter-entry time. It never owns story time.
- Chapter animation plans select one clip per channel; backward/direct navigation and reduced motion produce deterministic poses.
- Default-hidden nodes remain dark unless both the signed manifest and glTF extras permit the narrow verified-state window.
- Label gates keep Laboon unidentified at chapter 102 and reveal the name at chapter 103.
- Model anchors use antimeridian-safe distance math.
- Runtime worlds enter within 9 degrees and unload beyond 13 degrees, including GPU scene disposal.
- The Reverse Mountain asset is allowed on globe projection; the visual proof changed 14.41 percent of canvas pixels when the layer was removed from the same frame.
- Runtime sync now promotes 17 GLBs and refuses 0.

## Chapter receipt

| Chapter | Visible story state | Motion state |
|---:|---|---|
| 100 | globe approach; no local theatre yet | approach transit |
| 101 | mountain, ascent/descent current, crest, and Merry | ascent, summit, descent, wake |
| 102 | Merry and unidentified whale exterior; no Crocus/lighthouse/interior | first contact, breach, swallow transition |
| 103 | Laboon, Crocus, Twin Cape, lighthouse, and interior theatre | surface idle, Crocus explanation and Log Pose |
| 104 | exterior promise tableau; interior closes | Laboon promise response |
| 105 | departure state | Merry Twin Cape departure |

The whirlpool emitter and its control mask remain default-hidden pending a verified story gate.

## Verification

- Reverse Mountain Blender/GLB verifier: **PASS**.
- Runtime 3D registry: **17 assets verified**.
- Narrative contracts and blockouts: **12 verified**.
- Runtime sync: **17 copied, 0 refused**.
- Pure runtime audit: **PASS** for labels, chapter gates, deterministic animation sampling, masks, antimeridian distance, and culling.
- Live chapter browser audit: **22/22 PASS**, including cold chapter entry, one GLB fetch, backward refog, offscreen unload, reduced motion, and zero browser errors.
- Globe proof: **4/4 PASS**, with a measured **14.41%** layer contribution.
- TypeScript: **PASS**.
- Focused ESLint: **0 errors**; one pre-existing `WorldMap` exhaustive-deps warning remains.
- Production build: **PASS** with runtime assets and transitions enabled.
- Local app: process exists and `http://localhost:3000` returned **HTTP 200**.
- `git diff --check`: **PASS**.

The broad 499-second voyage audit was also sampled through chapter 81 after one nondeterministic early test exit. Its second trace crossed the Baratie boundary, restored the model orbit, kept the journey running, and reported zero errors. The focused Reverse Mountain acceptance audit is the binding W1 proof.

## Rerun commands

```bash
cd /Users/shawnos.ai/dead-reckoning
python3 blender-assets/scripts/verify_reverse_mountain_graybox.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 blender-assets/scripts/verify_priority_narrative_blockouts.py
python3 blender-assets/scripts/verify_narrative_scene_contracts.py
python3 scripts/sync_runtime_assets.py
node scripts/audit_reverse_mountain_runtime.mjs
AUDIT_URL=http://localhost:3000 python3 scripts/audit_reverse_mountain_browser.py
AUDIT_URL=http://localhost:3000 python3 scripts/audit_reverse_mountain_globe.py
npx tsc --noEmit
NEXT_DIST_DIR=.next-codex-rm NEXT_PUBLIC_RUNTIME_3D_ASSETS=1 NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS=1 npm run build
```

## Next executable slice

Promote Water 7 / Sea Train into this same moving-world contract instead of starting another renderer. Split the current blockout into a Water 7/station world and reusable Puffing Tom/Rocketman vehicles; keep the route graph, chapter clock, Aqua Laguna weather, loading, and camera in the app. In parallel-safe asset lanes, Reverse Mountain can receive LOD0/LOD2/LOD3, final identity art, and shader consumption of the five masks without changing its signed chapter behavior.

Do not begin Egghead or Elbaph geometry until Water 7 has a comparable chapter/navigation/performance receipt.
