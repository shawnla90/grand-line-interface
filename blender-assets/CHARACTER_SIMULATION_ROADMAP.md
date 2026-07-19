# Grand Line character and story-simulation roadmap

## Current direction

The Grand Line Interface should become a living, chapter-aware world. As a
reader advances through the story, small recognizable characters appear at the
correct place, perform a short authored action, and settle into the correct
aftermath.

The approved visual direction is **illustrated 2.5D characters on
camera-facing planes with authored movement and local 3D effects**. The earlier
rigid-part GLBs read as wooden mannequins and are now motion references only.
They are not approved character art and must not be copied into the app.

This is deliberately not a fighting game:

- chapter contracts choose what is visible and who wins;
- pose atlases supply recognizable character states;
- keyframes supply deterministic movement, scale, rotation, and opacity;
- lightweight 3D particles, slashes, smoke, debris, and lighting add depth;
- backward chapter scrubbing resets every scene exactly.

## What is built now

The East Blue v1 pack covers chapters 1 through 100 with six arc groups:
Romance Dawn, Orange Town, Syrup Village, Baratie, Arlong Park, and Loguetown.

| Deliverable | Count / status |
| --- | --- |
| Character and tableau atlas packages | 14 |
| Reusable transparent pose frames | 84 |
| Authored story scenes | 14 |
| Runtime-ready scenes | 12 |
| Art-partial scenes | 2 |
| Actor movement tracks | 32 |
| Movement keyframes | 101 |
| Timed FX events | 33 |
| Review sampler | 28 seconds |

The two partial scenes are structurally complete but disabled until their
missing character art exists:

- `zoro-joins-at-shells-town` needs Axe-Hand Morgan and Koby;
- `loguetown-storm-escape` needs Dragon and Tashigi.

The source of truth is:

- `manifests/east-blue-2d.json` — verified runtime package and hashes;
- `runtime/east-blue-2d/character-index.json` — actor atlas registry;
- `contracts/east-blue-saga.simulation.json` — chapter gates and choreography;
- `handoffs/CLAUDE_CODE_EAST_BLUE_2D.md` — app integration contract;
- `art/east-blue/IMAGEGEN_PROVENANCE.md` — generation method and prompt set.

## East Blue story spine

The v1 batch selects the scenes that explain a change in the story, introduce a
core character, or deliver an arc climax. It does not attempt every panel.

| Chapter | Scene | State |
| ---: | --- | --- |
| 1 | Roger starts the Great Pirate Era | ready |
| 1 | Devil Fruit, sea rescue, and straw-hat promise | ready |
| 2 | Luffy punches Alvida | ready |
| 6 | Zoro becomes the first crewmate | art partial |
| 20 | Luffy launches Buggy from Orange Town | ready |
| 40 | Luffy stops Kuro | ready |
| 51 | Zoro challenges Mihawk | ready |
| 66 | Luffy breaks Krieg's armor | ready |
| 68 | Sanji leaves Baratie | ready |
| 81 | Nami asks Luffy for help | ready |
| 93 | Luffy defeats Arlong | ready |
| 99 | Buggy nearly executes Luffy on Roger's scaffold | ready |
| 100 | Smoker and the storm block the escape | art partial |
| 100 | The crew declares its dreams and enters the Grand Line | ready |

Exact tracks, timings, poses, and effects live in the simulation contract rather
than this roadmap.

## Ownership boundary

### This asset workspace owns

- original generated character/tableau sheets and keyed-alpha derivatives;
- pose slicing, normalized atlas packaging, hashes, and runtime metadata;
- scene choreography, local movement, effect cues, and preview rendering;
- visual review artifacts, manifests, validators, and integration handoffs.

### `/Users/shawnos.ai/dead-reckoning` owns

- the reader's chapter and spoiler state;
- map anchors, camera distance, projection, and object lifetime;
- fetching, instancing, pausing, unloading, and device budgets;
- the deterministic playback clock, reduced motion, replay, and sound policy;
- final geographic alignment with island and landmark contracts.

The isolated factory remains the editable art source. Promotion mirrors only
signed, source-free derivatives into the app repository. A saga remains off
until the app proves it behind the shared feature flag; the current Arabasta
pack has passed that proof and is `integration_ready: true`.

## Runtime representation by distance

| Level | Reader view | Representation | Runtime rule |
| --- | --- | --- | --- |
| LOD 0 | globe / far zoom | existing portrait bubble or SVG | cheapest discovery layer |
| LOD 1 | regional zoom | one static atlas pose | no animation and no FX |
| LOD 2 | close map view | stepped pose atlas plus interpolated transforms and FX | one active scene; up to three background actors |
| LOD 3 | explicit replay | same 2.5D scene with camera cues and optional sound | user initiated |

This gives character recognition at map scale without paying for high-poly hero
models. Select future scenes may use full 3D only when the camera and story beat
justify the cost.

## Choreography contract

Each actor track contains deterministic keyframes in a normalized local stage:

- `x`: -1 left to +1 right;
- `y`: 0 ground plane and positive values above it;
- `scale`: multiplier over the actor's `map_height`;
- `rotation`: billboard roll in degrees;
- `opacity`: 0 to 1;
- `pose`: step-selected atlas frame;
- `ease`: optional numeric transform easing.

FX events remain renderer-owned cues such as `impact`, `slash`, `lightning`,
`smoke`, `debris`, `rubber-stretch`, and `structure-collapse`. They never decide
an outcome.

## Chapter behavior

- Before a verified start chapter, do not fetch the scene or its actor atlases.
- In an active window, entering close range may play the scene once.
- After the window, show the safe aftermath pose or a replay affordance.
- Scrubbing backward resets local time and all actor/FX state.
- A `chapter_to_verify` scene remains disabled.
- Reduced motion selects a safe static frame and suppresses autoplay and FX.
- A scene marked `art_partial` is never enabled merely because its chapter is
  known.

## Production pipeline

The approved 2.5D state machine is:

`idea -> scene_contract -> canon_verified -> generated_sheet -> alpha_review -> pose_atlas -> movement_authored -> runtime_verified -> app_proof -> integration_ready -> integrated`

Required gates:

1. **Contract** — saga, arc, place, chapter, cast, outcome, and unknowns.
2. **Canon review** — exact chapter window and early-story visual variant.
3. **Generated sheet** — six clear, reusable states on a flat key background.
4. **Alpha review** — preserve costume colors, remove the key, inspect edges.
5. **Atlas** — normalize frames, pivots, UVs, hashes, and map height.
6. **Movement** — author short deterministic actor and FX tracks.
7. **Validation** — schema, alpha, hashes, pose names, durations, and previews.
8. **App proof** — measure map-scale readability, memory, and disposal.
9. **Promotion** — set `integration_ready` only after the proof passes.

The old GLB state machine remains valid for terrain, landmarks, vehicles, and
rare full-3D scenes. It is no longer the default character pipeline.

## Performance targets

- 384 x 384 pixels per normalized pose cell;
- one 3 x 2 RGBA atlas per actor variant;
- lazy-load only actors referenced by the active scene;
- one active LOD 2 scene at a time;
- at most three dormant LOD 1 scene markers in the camera neighborhood;
- material `transparent: true`, `depthWrite: false`, and alpha test near 0.05;
- dispose texture clones and effect geometry on chapter/camera exit;
- pause when offscreen or the document is hidden;
- keep uncompressed v1 atlases as the source of truth, then test WebP/KTX2 only
  after visual comparison in the real renderer.

## Saga roadmap

### Phase 0 — systems and motion studies (complete)

- schemas, queue, manifests, chapter-gate research, and validators;
- six rigid-part encounter studies proving deterministic motion/export;
- decision recorded that rigid figures are references, not shippable art.

### Phase 1 — East Blue 2.5D story pack (asset build complete)

- 14 recognizable actor/tableau packages and 84 poses;
- 14 chapter-gated story simulations across all six East Blue arcs;
- verified catalog, scene board, and sampler video;
- runtime/app handoff with two art-partial scenes disabled.

Next East Blue asset batch:

1. Morgan and Koby for Shells Town.
2. Dragon and Tashigi for Loguetown.
3. Zeff and a Baratie farewell tableau if the close replay needs more emotion.
4. Genzo/Nojiko only if the Arlong Park story layer needs village context.

### Phase 2 — Baroque Works and Arabasta (ten scenes promoted)

Batch A is complete and web proven:

| Chapter | Scene | State |
| ---: | --- | --- |
| 107–108 | Zoro defeats the Whisky Peak bounty hunters | integrated behind allowlist |
| 114 | Miss All Sunday appears and demonstrates her power | integrated behind allowlist |
| 158 | Ace intervenes between Smoker and Luffy | integrated behind allowlist |
| 159 | Ace destroys the Baroque Works Billions' five-ship convoy with Fire Fist | integrated behind allowlist |
| 176–179 | Crocodile defeats Luffy in their first desert encounter | integrated behind allowlist |
| 187–189 | Sanji defeats Bon Clay with his Arabasta-era kick set | integrated behind allowlist |
| 190–193 | Nami defeats Miss Doublefinger with the first Clima-Tact weather sequence | integrated behind allowlist |
| 194–195 | Zoro defeats Mr. One with the breath-of-steel/Lion Song sequence | integrated behind allowlist |
| 198–201 | Luffy counters Crocodile with water in their palace-rooftop rematch | integrated behind allowlist |
| 203–210 | Luffy defeats Crocodile with the final underground Gum-Gum Storm sequence | integrated behind allowlist |

The generalized pack loader, signed manifest pipeline, reusable FX mappings,
dev proof selector, backward-scrub behavior, lazy atlas fetches, the reusable
ship-destruction tableau, and East Blue
compatibility all pass their browser audits. The pack is technically promoted
but remains off by default.

The promoted pack now contains 18 actor/tableau atlases, 108 poses, 20 actor
tracks, 118 movement keyframes, and 63 timed FX events. The browser proof passes
44/44 assertions and the signed app artifact passes 22/22 checks. The complete
three-fight Crocodile spine explicitly supersedes the old faceless rigid
blockout.

Continue shared actor libraries and scenes in this order:

1. Optionally add Vivi plus reusable Alubarna crowd, smoke, debris, and palace
   language without blocking the completed fight spine.
2. Finish East Blue cast holes: Koby/Morgan, Dragon/Tashigi, Usopp, and a Zeff
   farewell tableau. Sanji now has a signed Arabasta actor variant.
3. Enies Lobby's four-fight CP9 spine is complete. Continue there with Robin's
   declaration, Franky, Usopp support, and the remaining crew beats without
   rebuilding Blueno, Jabra, Kaku, or Lucci.
4. Add a Little Garden scale study only after the character fights above.

Do not collapse the Crocodile story into one fight contract.

### Phase 3 — Skypiea through Marineford animation spine

1. Skypiea is promoted: Luffy versus Enel at chapters 279–302 now includes
   rubber immunity, lightning, gold-ball burden, Golden Rifle, final bell
   impact, two signed atlases, 12 poses, and a 26/26 cross-pack browser proof.
2. Enies Lobby now has a promoted four-fight CP9 spine: Luffy versus Blueno at
   chapters 387–388 with first Gear Second and Jet Bazooka; Sanji versus Jabra
   at chapter 415 with first Diable Jambe and Flambage Shot; Zoro versus Kaku
   at chapters 416–417 with Four-Sword Style and Asura; and Luffy versus Rob
   Lucci at chapters 418–427 with Gear Second/Third, Rokuogan, and Jet Gatling.
   The pack contains eight atlases, 48 poses, four scenes, 48 movement
   keyframes, and 33 FX events. Its 47/47 shared browser receipt proves exact
   lazy loading, same-anchor replacement, backward reset, and the four matched
   voice calls. Continue with Robin's declaration plus Franky and Usopp core
   libraries; do not rebuild the proven fight spine.
3. Thousand Sunny: research the exact chapter/audio alignment for Coup de
   Burst before authoring Franky, Sunny, exhaust-cloud, and ship-trajectory
   tracks.
4. Sabaody: Kizaru's arrival and captain clash (chapters 507–509), then Kuma's
   crew separation around chapters 512–513 using paw-shock, disappearance,
   and spoiler-locked destination metadata.
5. Marineford: Garp/admiral cast library, Akainu magma-fist barrage, Luffy's
   approach to the three admirals, Newgate/Akainu impacts, and the Oars/Oz
   battlefield route. Keep Aokiji versus Akainu as a later Punk Hazard history
   tableau, not an East Blue or Marineford event.

The spoken request "Orum" is not a confirmed canon identifier. It may refer to
Oars/Oz, Ohm, or a local audio slug; do not generate that scene until the term
is mapped to the intended chapter and character.

## Art and rights posture

The v1 atlases are original generated fan-art interpretations intended for an
internal prototype. They do not use anime frames, traced manga panels,
franchise logos, official textures, or ripped game models. Source sheets,
generation method, prompt summaries, alpha corrections, and runtime hashes are
kept in the workspace.

Before public or commercial distribution, obtain a rights review and replace
or license anything required by that review. Technical readiness is not a
statement of franchise permission.

## Explicit non-goals

- autonomous combat AI, health systems, or random winners;
- every manga scene or panel;
- official dialogue, music, anime clips, or copied camera cuts;
- permanent actors embedded in island GLBs;
- early variants that silently reveal later outfits or abilities;
- shipping the superseded wooden mannequin character art.
