# Grand Line animation handoff — promoted through the Enies Lobby CP9 spine

Date: 2026-07-18

## Start state

The web app remains the driving product. The illustrated 2.5D atlas pipeline is
the approved character representation; rigid character GLBs are motion studies
only. Do not rebuild the ten proven Arabasta scenes or add per-fight React
components. Extend the generic JSON contract, shared atlas loader, and FX
registry.

`arabasta-saga-2d-v1`, `skypiea-saga-2d-v1`, and
`enies-lobby-saga-2d-v1` are signed, browser-proven, and
`integration_ready: true`. They remain off unless the build allowlists their
saga keys through `NEXT_PUBLIC_STORY_SIMULATION_PACKS`.

## Proven pack

| Chapters | Scene | Signed cast |
| --- | --- | --- |
| 107–108 | Whisky Peak bounty-hunter trap | Zoro and Baroque Works crowd |
| 114 | Miss All Sunday arrives | Robin |
| 158 | Ace intervenes while Smoker pursues Luffy | Ace and Smoker |
| 159 | Fire Fist destroys the Billions convoy | Ace and convoy tableau |
| 176–179 | Luffy versus Crocodile, round one | Crocodile and round-one Luffy |
| 187–189 | Sanji versus Bon Clay | Arabasta Sanji and Bon Clay |
| 190–193 | Nami versus Miss Doublefinger | Arabasta Nami and Miss Doublefinger |
| 194–195 | Zoro versus Mr. One | wounded Arabasta Zoro and Daz Bones |
| 198–201 | Luffy versus Crocodile, round two | Aqua Luffy and wet-state Crocodile |
| 203–210 | Luffy versus Crocodile, final | final Luffy and final-state Crocodile |

Metrics: 18 atlases, 108 poses, 20 actor tracks, 118 keyframes, 63 FX events,
and a 20-second review sampler. The complete three-fight Crocodile spine
explicitly supersedes `arabasta-luffy-crocodile-sand-study`, the old faceless
rigid blockout.

Primary factory files:

- `art/arabasta/character-sheets.json`
- `contracts/story-simulations/arabasta-saga-2d-v1.simulation.json`
- `runtime/story-simulations/arabasta-saga-2d-v1/`
- `renders/story-simulations/arabasta-saga-2d-v1/scene-board.png`
- `manifests/story-simulations/arabasta-saga-2d-v1.json`
- `proofs/arabasta-saga-2d-v1-web-proof.json`

Rebuild in `/Users/shawnos.ai/dead-reckoning-blender-assets`:

```bash
python3 scripts/build_story_simulation_pack.py --config art/arabasta/character-sheets.json
python3 scripts/render_story_simulation_pack.py \
  --config art/arabasta/character-sheets.json \
  --contract contracts/story-simulations/arabasta-saga-2d-v1.simulation.json
python3 scripts/verify_story_simulation_pack.py \
  --config art/arabasta/character-sheets.json \
  --contract contracts/story-simulations/arabasta-saga-2d-v1.simulation.json \
  --canon-intake research/story-scenes/arabasta-batch-a.json \
  --provenance art/arabasta/IMAGEGEN_PROVENANCE.md \
  --web-proof proofs/arabasta-saga-2d-v1-web-proof.json
```

Expected result: `18 actors, 108 poses, 10/10 ready scenes, 12,930,626 atlas
bytes`.

## Promoted Skypiea and Enies Lobby packs

| Chapters | Scene | Signed cast | Required story motion |
| --- | --- | --- | --- |
| 279–302 | Luffy versus Enel | Skypiea Luffy and Enel | rubber immunity, gold-ball burden, Golden Rifle, bell defeat |
| 387–388 | Luffy versus Blueno | Gear Second Luffy and Blueno | Door-Door evasion, first Gear Second, Jet Pistol, Jet Bazooka |
| 415 | Sanji versus Jabra | Enies Lobby Sanji and hybrid Jabra | flame-free opening kicks, first Diable Jambe, Flambage Shot |
| 416–417 | Zoro versus Kaku | bandana Zoro and giraffe-hybrid Kaku | Four-Sword Style, Tempest Kick, Asura, nine-sword finish |
| 418–427 | Luffy versus Rob Lucci | Enies Lobby Luffy and hybrid Lucci | Gear Second/Third, Rokushiki counters, Jet Gatling, exhausted victory |

Skypiea contains two 3x2 atlases and 12 poses. Enies Lobby contains eight 3x2
atlases, 48 poses, four runtime-ready scenes, 48 movement keyframes, and 33 FX
events. Their manifests and browser receipts are:

- `manifests/story-simulations/skypiea-saga-2d-v1.json`
- `proofs/skypiea-saga-2d-v1-web-proof.json`
- `manifests/story-simulations/enies-lobby-saga-2d-v1.json`
- `proofs/enies-lobby-saga-2d-v1-web-proof.json`

The existing `op-luffy-gatling` clip remains removed from
`baratie-luffy-vs-krieg` and bound to Lucci's `jet-gatling` event. This batch
also registers `op-gear-second` on Luffy's Blueno activation,
`op-sanji-diable` on Sanji's ignition, and `op-zoro-santoryu` on the Asura
manifestation. All four rights statuses remain `local_prototype_only`; do not
treat the browser receipt as a public-distribution license.

## App proof

Repository: `/Users/shawnos.ai/dead-reckoning`

```bash
python3 scripts/sync_story_simulation_pack.py --pack arabasta-saga-2d-v1
python3 scripts/sync_story_simulation_pack.py --pack skypiea-saga-2d-v1
python3 scripts/sync_story_simulation_pack.py --pack enies-lobby-saga-2d-v1
python3 scripts/check_story_simulations.py --pack arabasta-saga-2d-v1 --require-promoted
python3 scripts/check_story_simulations.py --pack skypiea-saga-2d-v1 --require-promoted
python3 scripts/check_story_simulations.py --pack enies-lobby-saga-2d-v1 --require-promoted
python3 scripts/check_simulations.py
AUDIT_URL=http://localhost:3000 python3 scripts/audit_story_simulations.py
AUDIT_URL=http://localhost:3000 python3 scripts/audit_journey_climax_simulations.py
AUDIT_URL=http://localhost:3000 python3 scripts/audit_simulations.py
npm run build
```

Current receipts: Enies Lobby promoted artifact 22/22, shared Skypiea/Enies
Lobby browser 47/47, Arabasta browser regression 44/44, East Blue data 9/9,
East Blue browser 14/14, canon 29/29, and production build passed. The audit
proves zero pre-gate atlas fetches, exact two-actor lazy loading per fight, real
pose progression, all four visual/audio alignments, final holds, same-anchor
scene replacement, backward-scrub restarts, and reduced motion.

## Next production order

1. Enies Lobby: Robin's declaration, Franky, and the remaining core Straw Hat
   support library. Do not rebuild the proven Blueno, Jabra, Kaku, or Lucci
   fights.
2. Finish core cast holes: Koby/Morgan, Dragon/Tashigi, Usopp, Zeff farewell,
   and Franky. Sanji now has a signed Arabasta variant.
3. Optionally extend Arabasta with Vivi/Alubarna crowd and palace language;
   the core fight spine is complete and does not depend on this tableau work.
4. Thousand Sunny: research exact Coup de Burst chapter/audio alignment before
   authoring Franky, Sunny, exhaust-cloud, and trajectory tracks.
5. Sabaody: Kizaru arrival/captain clash, Pacifista pressure, and Kuma's crew
   separation with paw-shock/disappearance variants.
6. Marineford: Garp/admiral library, Akainu magma barrage, Luffy reaching the
   admirals, Newgate/Akainu impacts, Ace, and the Oars/Oz battlefield route.

## Canon guardrails

- The user shorthand “Nell” maps to Enel; “Luchi” maps to Rob Lucci.
- Sanji's first Diable Jambe showcase is chapter 415 against Jabra.
  The long-nosed CP9 fighter is Kaku; Zoro fights him in chapters 416–417.
- Luffy versus Rob Lucci begins at chapter 418; Gear Third is chapter 421.
- Luffy's first Gear Second showcase is the Blueno sequence in chapters
  387–388.
- Kizaru's Sabaody arrival/captain clash is chapters 507–509; Kuma's separation
  is around chapters 512–513.
- Aokiji versus Akainu belongs to later Punk Hazard history, not East Blue or
  Marineford.
- “Orum” is unresolved. It may mean Oars/Oz, Ohm, or a local audio slug. Stop
  that one scene until the intended character and chapter are confirmed.
- More Marines belong in later Tashigi/Alubarna or Marineford contracts. Do not
  rewrite the truthful chapter-158 Ace/Smoker intervention into a Crocodile
  scene.

## Worktree safety

The app worktree already contains unrelated audio/roadmap work and a modified
`data/generated/narrative_scenes.json`. Preserve it. Stage only the explicit
story-simulation paths after rechecking `git status --short --branch`.
