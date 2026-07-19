# Grand Line world simulation — W0/M0/W1 execution receipt

**Completed:** 2026-07-18  
**Driving app:** `/Users/shawnos.ai/dead-reckoning`  
**Asset authority:** `/Users/shawnos.ai/dead-reckoning/blender-assets` for runtime 3D and app integration  
**Git:** changes are intentionally uncommitted and unpushed

## Delivered

### Runtime motion foundation

- Simulation time stays at zero until every required atlas reports ready.
- A scene first opened in a hidden tab starts paused.
- The audio sink is installed before the first synchronization pass, removing the opening-cue race.
- Streak and trail movement is derived from absolute event age and is deterministic at 30, 60, and 120 Hz and after rewind.
- The standalone pose factory now normalizes an actor's full pose family with one shared scale and one foot baseline. A focused regression script proves the invariant. Existing signed atlases were preserved; regenerate them only through a deliberate pack promotion.

### Remastered action pilots

- `baratie-zoro-vs-mihawk`: Zoro has 19 movement keys and Mihawk 17, with short anticipation, contact, hit-stop, recoil, and recovery beats.
- `enies-lobby-luffy-vs-rob-lucci`: both actors have 20 keys. Jet Gatling begins on the same step as Lucci's matching defeat pose, eliminating a live-browser race.
- Existing illustrated character art remains the identity layer; no generic replacement figures were introduced.

### Loader-ready 3D repairs

- `arabasta-kingdom`: tagged `yuba-oasis` node.
- `skypiea-sky-system`: tagged `giant-jack` and `golden-belfry-cloud` nodes.
- `water-7-sea-train-network`: tagged `day-station`, `rocketman`, and `aqua-laguna` nodes.
- Runtime sync now promotes 16 GLBs and refuses 0. Newly addressable chapter-sensitive nodes remain default-hidden and use chapter verification gates.

### Reverse Mountain/Twin Cape W1 contract and animated graybox

`blender-assets/contracts/reverse-mountain-twin-cape-voyage.visual.json` defines:

- 12 environment, landmark, vehicle, creature, actor, route, and FX components;
- 21 named clips, 5 procedural FX masks, and 4 LOD tiers;
- Going Merry, Laboon, Crocus, ascent/descent currents, Twin Cape, interior staging, event states, fallback behavior, and Unreal reuse;
- a chapter 100–105 evidence ledger, including chapter-safe UI naming;
- a reusable whirlpool component that remains `default_hidden` and `chapter_to_verify`.

The matching research ledger, verifier, narrative index entry, and asset-queue state are present. The contract has now been executed as an animated `LOD1_LOCAL_THEATRE` graybox: 12 addressable components, 21 named clips, five signed FX masks, a chapter-102-safe fallback, and a 1.28 MiB loader-ready GLB.

### Source-of-truth guardrail

`blender-assets/manifests/workspace-ownership.json` records which package owns runtime 3D, the original story-art factory, app story integration, and app runtime. `blender-assets/scripts/audit_workspace_ownership.py` detects drift against the standalone mirror before bulk generation.

## Verification receipt

- Runtime asset sync: **17 copied, 0 refused**.
- Narrative contracts: **12 verified**.
- Story simulation contract: **22/22 checks pass** for Enies Lobby.
- Runtime determinism: **PASS** for readiness, pause/resume, 30/60/120 Hz, and rewind.
- Mihawk live simulation audit: **14/14 pass**.
- Journey climax live browser audit: **47/47 pass**.
- Production build: **PASS** with `NEXT_DIST_DIR=.next-codex-w1 npm run build`.
- Local app: process and `http://localhost:3000` independently returned HTTP 200 during verification.
- `git diff --check`: **PASS**.
- Reverse Mountain live chapter audit: **22/22 pass**.
- Reverse Mountain globe proof: **4/4 pass**, with 14.41% measured canvas contribution.

Primary rerun commands:

```bash
cd /Users/shawnos.ai/dead-reckoning
python3 blender-assets/scripts/audit_workspace_ownership.py
python3 blender-assets/scripts/verify_reverse_mountain_contract.py
python3 blender-assets/scripts/verify_narrative_scene_contracts.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 scripts/sync_runtime_assets.py
python3 scripts/audit_motion_remaster.py
node scripts/audit_sim_runtime_determinism.mjs
python3 scripts/check_story_simulations.py --pack enies-lobby-saga-2d-v1 --require-promoted
AUDIT_URL=http://localhost:3000 python3 scripts/audit_simulations.py
AUDIT_URL=http://localhost:3000 python3 scripts/audit_journey_climax_simulations.py
NEXT_DIST_DIR=.next-codex-w1 npm run build
```

## Boundaries and remaining work

- Reverse Mountain is now a verified animated GLB and in-app chapter 101–105 voyage sequence. It remains a graybox, not final identity art.
- Existing atlases were not regenerated with the corrected normalizer in this slice.
- The runtime now has `AnimationMixer` support and offscreen hysteresis. Reverse Mountain still needs LOD0/LOD2/LOD3 promotion, shader consumption of its masks, instancing where repetition justifies it, and measured device/GPU budgets.
- Mary Geoise still produces three safe manifest/extras contradictions. The current runtime hide predicate keeps those nodes hidden; repair them in their own scoped pass.
- Crocodile Final and Enel remain candidates for the next motion-remaster batch after the world graybox proof.
- Do not start Egghead or Elbaph geometry until the Reverse Mountain receipt passes end to end.

## Next executable slice

The Reverse Mountain W1 graybox is complete. Its detailed receipt is `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_W1_GRAYBOX_EXECUTION.md`.

Promote Water 7 / Sea Train next using the same contract: split environment and vehicles, retain app-owned route/chapter/camera/weather state, and prove the moving-world sequence before opening Egghead or Elbaph work. Preserve the illustrated simulation layer for recognizable character action.
