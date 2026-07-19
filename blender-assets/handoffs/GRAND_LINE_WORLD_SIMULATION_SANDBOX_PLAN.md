# Grand Line world-simulation sandbox plan

**Status:** W0 + M0 + W1 contract executed, 2026-07-18  
**Driving product:** `/Users/shawnos.ai/dead-reckoning` web app  
**Current story horizon:** chapter 441, end of Post-Enies Lobby  
**Purpose:** close the voyage and cast gaps before advancing the build, while evolving the existing story simulations into a living 3D world that can later share assets with Unreal.

## Outcome

Do not replace the current illustrated character system with full 3D characters. Keep the most recognizable, identity-sensitive action in 2.5D, make it more fluid, and surround it with a true 3D world:

1. **MapLibre owns the world:** globe position, chapter state, route progress, camera, loading, and lifetime.
2. **Three.js owns the local scene:** islands, ships, trains, creatures, skeletal/morph clips, instancing, and local effects.
3. **Blender owns reusable assets:** geometry, rigs, named clips, masks, materials, and LODs.
4. **The story-simulation layer owns character action:** signed pose atlases, deterministic movement, contact FX, and reduced-motion fallbacks.
5. **One journey director owns synchronization:** chapter gates, world state, simulation time, camera shots, and audio cues.

The first proof should be **Reverse Mountain into Laboon**, not Egghead. It exercises a ship, a moving current, a creature, a landmark, camera travel, story action, and chapter/audio synchronization in one early-voyage sequence. The second proof should promote the existing **Water 7 / Sea Train** work instead of rebuilding it.

## Verified baseline

### Story simulations

- 27 runtime scenes through chapter 441.
- 42 signed atlases and 252 illustrated poses.
- 58 actor tracks, 266 movement keyframes, and 133 FX events.
- 25 scenes are enabled in the automatic journey; 2 are currently disabled.
- East Blue has 12 scenes, Arabasta 10, Skypiea 1, and Enies Lobby 4.
- Most hero actors still use six poses and roughly six movement keys over 10–13 seconds.
- Only three journey scenes currently have an authored camera push.

### 3D world

- The embedded app asset package declares 16 Blender models: 14 local world scenes and 2 vertical transitions.
- 13 GLBs are promoted into the web app.
- 3 are explicitly refused: `arabasta-kingdom`, `skypiea-sky-system`, and `water-7-sea-train-network`.
- The refusals are useful safety gates: hidden chapter components are declared but are not addressable as tagged glTF nodes.
- Every current GLB exports `animations: false`; these are static blockouts, not living scenes yet.
- The current loader has no viewport-distance culling, LOD selection, `AnimationMixer`, instancing layer, or procedural environment clock.
- The newer source of truth is `/Users/shawnos.ai/dead-reckoning/blender-assets`. The standalone `/Users/shawnos.ai/dead-reckoning-blender-assets` 3D manifest is older and must be reconciled before another bulk 3D run.

## What is missing before chapter 441

This is the continuity checklist. It is intentionally smaller than “animate every manga scene,” but large enough that the voyage no longer skips its own story.

| Chapters | Area | Existing coverage | Must-have continuity additions |
|---:|---|---|---|
| 1–7 | Romance Dawn | Roger, fruit/promise, Alvida | Morgan defeat/Zoro joins; Koby art and farewell |
| 8–21 | Orange Town | Luffy vs Buggy | No required anchor; Chouchou is optional |
| 22–41 | Syrup Village | Luffy vs Kuro | Usopp joins; Going Merry received |
| 42–68 | Baratie | Mihawk, Krieg, Sanji farewell | Zeff library/tableau; re-enable farewell journey beat |
| 69–100 | Arlong Park / Loguetown | Nami plea, Arlong, scaffold, vows | Dragon/Tashigi storm escape; one Usopp support showcase |
| 101–105 | Reverse Mountain | Waypoint only | Merry ascent/descent; Laboon collision/swallow; Crocus; Luffy/Laboon promise |
| 106–114 | Whisky Peak | Zoro fight, Robin arrival | Vivi/Igaram reveal and Arabasta commitment |
| 115–129 | Little Garden | Nothing | Dorry/Brogy duel; wax trap; Island Eater finish and launch |
| 130–154 | Drum Island | Nothing | Mountain climb; Hiriluk flag; Wapol finish; Chopper joins under the blossoms |
| 155–217 | Arabasta | Strong fight pack | Luffy/Vivi argument; Mr. Prince; Usopp/Chopper; bomb/Pell; X-mark farewell; Robin joins |
| 218–236 | Jaya | Nothing | Robin crew boundary; Blackbeard dream beat; Bellamy one-punch; Cricket/stream preparation |
| 237–302 | Skypiea | Knock-Up Stream and Enel climax | Arrival/dials; Wyper/war montage; Noland/Kalgara; Giant Jack/Shandora setup |
| 303–321 | Long Ring Long Land | Nothing | Compact Aokiji/Robin threat beat; Foxy montage optional |
| 322–374 | Water 7 | Static, refused Sea Train blockout | Merry verdict/Luffy vs Usopp; CP9 reveal; Franky/Tom; Aqua Laguna/Rocketman; Sogeking train raid |
| 375–430 | Enies Lobby | Blueno, Jabra, Kaku, Lucci | Robin declaration/flag shot; Franky; Monster Chopper; Nami; Buster Call; Merry rescue/funeral |
| 431–441 | Post-Enies Lobby | Nothing | Garp reveal; Franky joins; Sunny launch; Shanks/Newgate; Ace/Blackbeard |

### Foundational libraries still missing

These are not optional if the app is going to tell the voyage rather than only sample its fights:

- Usopp: Arabasta support, Water 7 duel, and Sogeking variants.
- Chopper: Drum base, Arabasta support, and Monster Point.
- Robin: crew, Skypiea, Water 7 cloak, and declaration variants.
- Franky: Water 7, train raid, Enies fight, and joining variants.
- Vivi: Whisky Peak reveal, desert, clock tower, and farewell variants.
- Zeff: Baratie farewell tableau.
- Going Merry: navigable vehicle, damaged state, rescue, and farewell.
- Thousand Sunny: launch vehicle and Coup de Burst-ready state.
- Laboon: multi-LOD creature plus interior/tableau staging.
- Dorry and Brogy: giant-scale actor library and reusable giant rig.

## Motion-quality plan

### Phase M0 — repair the current six-pose motion

Use the existing art before commissioning more poses.

1. Normalize every pose for a character against one shared body scale and foot baseline. The current builder independently fills each cell and hardcodes the pivot, which creates size pumping and foot sliding.
2. Hold scene time at zero until all required textures are GPU-ready. Preload the next simulation during the preceding voyage leg.
3. Install or buffer the audio sink before the first scene mount so the opening cue cannot race the renderer.
4. Make streak and trail positions pure functions of absolute event age. Never update them with frame-dependent `+=` movement.
5. Add reusable choreography macros in the factory: `idle`, `anticipate`, `dash`, `strike`, `contact`, `hit_stop`, `overshoot`, `knockback`, and `recover`.
6. Expand hero fights from roughly 6 to 14–20 transform keys per actor while reusing the current six illustrations.

Recommended combat cadence:

- anticipation: 180–300 ms
- travel/smear: 80–140 ms
- contact: 33–67 ms
- hit-stop: 70–110 ms
- overshoot: 120–220 ms
- recovery/reaction: 300–700 ms

Pilot the remaster on four different motion types:

- Zoro vs Mihawk: measured blade timing and recoil.
- Luffy vs Crocodile final: elastic barrage and environmental impact.
- Luffy vs Enel: stretch, lightning, vertical scale, and bell contact.
- Luffy vs Lucci: Soru/Jet speed, afterimages, and Gatling cadence.

### Phase M1 — motion contract v2

Keep v1 readable. Add optional, backward-compatible fields:

- keyframes: `scale_x`, `scale_y`, `skew`, `facing`, optional depth/layer, and cubic-bezier easing;
- actor trails: `count`, `spacing_ms`, and `opacity`;
- FX: stable `id`, `origin`, `target`, `attach_to`, and optional stage shake;
- explicit authored holds and impact phases;
- factory macros that compile to explicit signed keyframes, leaving the browser deterministic.

The renderer can create two or three afterimages by sampling `evaluateActor(t - spacing)` without new drawings. That is the highest-leverage improvement for Soru, Jet attacks, Santoryu, kicks, and Gum-Gum barrages.

### Phase M2 — atlas v2

Only after M0 proves the value:

- support actors: 8–10 poses;
- hero actors: 12–16 poses;
- pose family: `guard -> anticipation -> smear -> contact -> recoil -> recovery`;
- dynamic atlas dimensions instead of the fixed 3x2 schema;
- target 4x4 at 1024 px with 256 px cells for mobile, subject to profiling;
- retain each six-pose atlas as LOD/reduced-motion fallback;
- generate each pose family from one approved identity reference to avoid costume and face drift.

Illustrated poses should intentionally step around 10–12 fps while transform motion, camera, and FX remain continuous.

### Phase M3 — cinematic treatment

Evolve the current single camera push into app-owned `shots[]`:

- establishing wide;
- anticipation push;
- 120–300 ms impact cut;
- recovery pullback;
- optional event-bound shake and stage-relative focus.

Keep the existing `WorldMap` chase loop as the one MapLibre camera authority. Do not introduce a second animation loop.

Classify audio as hard-sync impact Foley or soft-sync dialogue/ambience. Target about 80 ms for hard-sync impacts after predecode, instead of the current broad 600 ms compilation allowance.

## Living-world architecture

Every world package should stop being a single monolithic GLB. Use these asset classes:

- `environment`: terrain, coast, architecture, and collision proxies;
- `landmarks`: separately chapter-gateable towers, ports, bridges, trees, and interiors;
- `routes`: canals, rails, currents, ascent paths, and camera splines;
- `vehicles`: Merry, Sunny, Sea Trains, Marine ships, and local craft;
- `creatures`: Laboon, Sea Kings, dinosaurs, whales, and ambient species;
- `event_states`: storm, destruction, Buster Call, battle damage, and aftermath;
- `fx_masks`: named volumes, empties, and vertex masks consumed by procedural runtime effects;
- `lod0`, `lod1`, `lod2`, `impostor`: explicit quality tiers;
- `clips`: named animation clips such as `idle`, `breach`, `headbutt`, `sail`, `turn`, `wheel_loop`, `arrival`, and `impact`.

Recommended Blender collections:

- `00_TOPOLOGY`
- `10_TERRAIN`
- `20_LANDMARKS`
- `30_VEHICLES`
- `40_CREATURES`
- `50_EVENT_STATES`
- `60_FX_MASKS`
- `90_RUNTIME_LOD`

### Procedural instead of baked

Build silhouette-changing geometry and landmarks in Blender. Build repeatable motion in the runtime:

- ocean swell, current flow, ship wake, and foam;
- Reverse Mountain currents, waterfalls, and whirlpool discs;
- Aqua Laguna wave wall, rain, and spray;
- Knock-Up Stream turbulence and cloud breach;
- Arabasta sandstorms, dune drift, and heat haze;
- Drum snow and blizzards;
- Skypiea cloud-sea flow;
- Sabaody/Fish-Man bubbles and caustics;
- fog, mist, lightning, sparks, and port smoke.

Blender supplies masks, anchors, splines, and collision/occlusion volumes. The app supplies the clock, particles, shaders, and device quality level.

## World production order

### W0 — truth and runtime foundation

- Reconcile the embedded and standalone asset packages; treat the embedded app package as authoritative until then.
- Reconcile stale queue states, roadmap counters, saga boundaries, and disabled journey rows.
- Repair node tags and chapter gates for Arabasta, Skypiea, and Water 7.
- Add viewport proximity with hysteresis, selected LOD, quality tiers, and a one-hero-world active budget.
- Add `AnimationMixer`, instancing support, and a procedural environment clock to the existing loader rather than creating island-specific renderers.

### W1 — Reverse Mountain / Laboon vertical slice

Deliver:

- Reverse Mountain/Red Line local environment;
- ascent and descent current splines;
- reusable Going Merry vehicle with `sail`, `turn`, `climb`, `descend`, and `impact` clips;
- Laboon LODs and rig with `idle`, `breach`, `mouth_open`, `headbutt`, `impact`, and `settle` clips;
- Twin Cape, lighthouse, and Crocus landmarks;
- procedural current, waterfall, foam, wake, spray, and whirlpool;
- Laboon collision/swallow and promise simulations;
- one continuous chapter/audio/camera receipt from chapter 100 vows into chapter 105 departure.

This is the acceptance proof for a voyage that moves through a world rather than teleports between markers.

### W2 — Little Garden / Drum / Arabasta continuity

- Little Garden environment, volcano state, giant skeleton, Dorry/Brogy variants, prehistoric vegetation, dinosaurs, and Island Eater.
- Drum terrain, Drum Rockies, castle, village kit, climbing route, snow/blizzard, flag, and cherry-blossom event state.
- Repair Arabasta’s GLB refusal, then add reusable desert/oasis/city chunks plus sandstorm and river states.
- Build Vivi, Chopper, Usopp, Robin, and the continuity scenes listed above.

### W3 — Jaya / Skypiea continuity

- Jaya/Mock Town and Cricket approach environment.
- Connect the ship route into the existing Knock-Up Stream transition.
- Promote the full Skypiea system by repairing Giant Jack/Belfry tagging.
- Add White Sea motion, Milky Road routing, cloud islands, Giant Jack, Shandora, and Belfry event states.
- Build Blackbeard, Bellamy, Cricket, Wyper, and the supporting story beats.

### W4 — Water 7 / Sea Train / Enies Lobby

Do not rebuild the existing Sea Train asset from zero. Split and promote it:

1. Water 7 and station environment GLBs.
2. App-owned route graph and submerged rail line.
3. Separate Puffing Tom and Rocketman vehicle GLBs with wheel/engine clips.
4. Procedural wake, spray, steam, rain, sparks, and Aqua Laguna.

First tag the hidden Day Station, Rocketman, and Aqua Laguna components so the current safety gate can pass. Verify the exact Rocketman/Aqua Laguna chapter gate before promotion.

Then build a dedicated Enies Lobby hero environment: courthouse, Tower of Law, bridge, waterfall void, Gates of Justice, Buster Call, destruction state, and escape route. Anchor the existing CP9 fights inside it and add Robin, Sogeking, Franky, Chopper, Nami, Merry, and Sunny story beats.

### W5 — later-world continuity

- Optimize Sabaody’s large grove blockout using a small root/tree kit and instancing; animate bubbles and resin.
- Add Fish-Man depth, currents, creatures, bubbles, and caustics.
- Build Thriller Bark as a moving ship-island with fog and stateful anchor behavior.
- Create evidence contracts for Egghead and Elbaph before modeling either one.
- Build Dorry/Brogy at Little Garden first, then reuse the giant skeleton and identity library for Elbaph.
- Treat Egghead and Elbaph map coordinates as derived placement anchors, never proof of canon local topology.

## Performance contract

### World layer

| Tier | Target |
|---|---:|
| Orbit | GeoJSON/raster only; no GLB |
| Distant LOD2 | 2k–8k triangles, <=250 KB compressed |
| Near LOD1 | 15k–30k triangles, <=750 KB compressed |
| Hero LOD0 | 40k–80k triangles, <=2 MB per streamed chunk |
| Active worlds | 1 hero plus at most 3 support representations |
| Visible geometry | <=150k triangles desktop; about half on mobile |
| Draw calls | <=80 desktop; <=40 mobile |
| Textures | KTX2/Basis; at most two 1024 maps per hero and 512 maps for support |
| Animated entities | <=4 live skinned rigs, <=64 bones each |
| Particles | about 3k desktop / 1k mobile |
| GPU textures | <=64 MB desktop / <=24 MB mobile |

The runtime load gate becomes:

`feature flag + chapter gate + projection + viewport proximity + selected LOD + device quality`

### Story-simulation layer

- one active story simulation;
- simulation work <=4 ms inside a 16.7 ms target frame;
- p95 <=25 ms desktop and <=33 ms throttled/mobile proof;
- <=16 MB decoded active actor textures;
- <=12 active draw calls;
- <=3 actor afterimages.

## Parallel production train

These workstreams can run concurrently after W0 establishes the contracts. Each owns separate source files; one integrator alone updates generated registries and shared roadmaps.

| Lane | Owns | First deliverable | Must not edit |
|---|---|---|---|
| A — runtime motion | evaluator, sim renderer, choreography compiler, proofs | M0 fixes and four remastered fights | character art and canon gates |
| B — story/canon | chapter ledger, gates, anchors, scene research | verified chapter 1–441 continuity ledger | generated registries and renderer code |
| C — character art | identity references, pose sheets, keyed atlases, provenance | Laboon tableau cast, Vivi, Chopper, Usopp/Sogeking, Robin, Franky | app runtime code |
| D — world geometry | contracts, Blender scenes, LODs, landmarks | Reverse Mountain/Twin Cape environment | story simulation JSON |
| E — vehicles/creatures | rigs, clips, animation exports | Going Merry and Laboon | island topology contracts |
| F — ocean/weather FX | shader/particle primitives, masks, device tiers | Reverse Mountain current/wake/whirlpool | Blender landmark geometry |
| G — integration/QA | sync, registry, chapter journey, camera/audio, receipts | one continuous Reverse Mountain receipt | source art except explicit repair |

Ownership rule: no lane manually edits generated files. The integrator runs the canonical compilers after source reviews pass. Do not stage or overwrite unrelated in-flight audio/camera changes.

## Quality gates

### Motion

- no moving combat segment longer than 900 ms unless explicitly marked as a hold;
- every finisher has anticipation, contact, freeze, overshoot, and recovery;
- shared-scale and foot-lock checks pass across each pose family;
- 30, 60, and 120 Hz samples return identical transforms at the same authored time;
- scene time remains zero until actors are visible;
- backward scrub and reduced motion remain deterministic;
- golden frames exist at anticipation, contact, and final hold.

### World

- every chapter-hidden component is a tagged, addressable glTF node or is omitted from the export;
- GLB hashes, bytes, node extras, named clips, LODs, and fallback art verify;
- orbit mode loads no GLB;
- offscreen worlds unload after hysteresis;
- the active-world and GPU budgets hold on a throttled/mobile proof;
- route splines and local topology are labeled schematic unless panel evidence establishes them;
- procedural effects have reduced-motion and device-quality paths.

### Journey

- one deterministic timeline drives ship/train/creature motion, character simulation, camera, and audio;
- forward play, backward scrub, direct chapter jump, and cold load land on the same state;
- hard-sync audio impacts remain within the measured tolerance;
- every built chapter anchor has a fallback when 3D is disabled;
- localhost and production health are verified separately.

## Execution status — 2026-07-18

- The three refused GLBs were repaired. All 16 declared runtime GLBs now pass the export/sync gate.
- The asset-package split now has an explicit ownership manifest and a drift audit.
- Pose normalization now uses one actor-family scale and one foot baseline. The factory regression proof passes; existing signed atlases were not bulk-regenerated.
- Simulation time waits for atlas readiness, hidden-tab startup begins paused, the audio sink is installed before the first synchronization pass, and streak positions are absolute-time functions.
- Zoro vs Mihawk and Luffy vs Lucci were expanded to 17–20 movement keys per actor using their existing illustrated poses.
- The Reverse Mountain/Twin Cape visual contract now covers the Merry, Laboon, Crocus, currents, chapter-safe identities, clips, FX masks, fallbacks, LODs, runtime ownership, and Unreal reuse.
- The live journey climax audit passes 47/47, including the synchronized Jet Gatling/Lucci defeat contact, backward scrub, direct re-entry, reduced motion, and audio gating.
- The production build passes with an isolated Next output directory. Localhost is separately verified at HTTP 200.
- The Reverse Mountain W1 contract is now executed as a 1.28 MiB animated graybox with 12 addressable components, 21 named clips, five signed masks, and a spoiler-safe fallback.
- Chapters 101–105 are integrated through the existing journey director and single MapLibre chase loop. Backward/direct navigation, reduced motion, offscreen unload, one-fetch behavior, and globe rendering are browser-proven.
- Runtime sync now promotes 17 GLBs and refuses 0. The Reverse Mountain chapter audit passes 22/22 and the globe proof passes 4/4 with 14.41% measured canvas contribution.

The foundation receipt is `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_W0_M0_W1_EXECUTION.md`. The completed graybox receipt is `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_W1_GRAYBOX_EXECUTION.md`.

## Recommended next sandbox session

Execute the **Water 7 / Sea Train moving-world promotion**, not another planning pass and not Egghead/Elbaph.

1. Turn the existing Water 7 blockout into a signed visual contract with exact station, route, train, Aqua Laguna, and chapter-state gates.
2. Split the current scene into Water 7/station environment and reusable Puffing Tom/Rocketman vehicle GLBs instead of rebuilding the art from zero.
3. Keep rail routing, chapter clock, weather, loading, audio, and camera in the app; keep meshes, rigs, clips, anchors, and masks in Blender.
4. Integrate the Sea Train voyage through the existing runtime registry and MapLibre chase loop. Do not add a second camera loop.
5. Prove cold load, forward/backward/direct navigation, 3D-off fallback, reduced motion, low-quality mode, offscreen unload, and measured mobile/GPU budgets.
6. In a separate asset-only polish lane, add Reverse Mountain LOD0/LOD2/LOD3 and shader consumption of its signed masks without changing the verified chapter contract.

## Copy-paste prompt for the next execution session

> Work in `/Users/shawnos.ai/dead-reckoning`. Read `AGENTS.md`, `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_SANDBOX_PLAN.md`, `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_W0_M0_W1_EXECUTION.md`, and `blender-assets/handoffs/GRAND_LINE_WORLD_SIMULATION_W1_GRAYBOX_EXECUTION.md`. Treat `/Users/shawnos.ai/dead-reckoning/blender-assets` as authoritative for runtime 3D and app integration, and use the ownership manifest before touching the standalone factory. Preserve unrelated dirty-worktree changes and do not commit or push unless explicitly asked. Promote the existing Water 7 / Sea Train blockout into the moving-world contract proven by Reverse Mountain: define exact chapter/evidence gates, split the environment from Puffing Tom/Rocketman vehicle GLBs, add reusable clips and procedural Aqua Laguna/steam/wake masks, integrate through the existing runtime registry and single MapLibre camera chase, and verify cold load, forward/backward/direct navigation, reduced motion, 3D-off fallback, offscreen unload, and measured device budgets. Do not start Egghead/Elbaph or replace the illustrated character system.
