# Claude Code handoff — Arabasta Batch A story simulations

Date: 2026-07-18

## Outcome

`arabasta-saga-2d-v1` is built, signed, promoted, and proven in the real shared
MapLibre/Three simulation host. It is `integration_ready: true` and remains off
by default. The web atlas is still the driving product; Unreal is only a later
consumer of the same signed derivatives.

Do not regenerate these approved sheets or replace the existing East Blue
pack. Continue through data and reusable FX, never one React component per
fight.

## Shipped Batch A

| Gate | Scene ID | Runtime cast |
| --- | --- | --- |
| chapters 107–108 | `whisky-peak-zoro-vs-bounty-hunters` | Zoro plus reusable left/right instances of the Baroque Works crowd atlas |
| chapter 114 | `robin-miss-all-sunday-arrival` | Miss All Sunday / Nico Robin |
| chapter 158 | `ace-blocks-smoker-at-nanohana` | Ace and Smoker; this is an intervention tableau, not an invented prolonged duel |
| chapter 159 | `ace-fire-fist-destroys-billions-fleet` | Ace plus a reusable five-ship Baroque Works convoy destruction tableau |

Actor packages:

- `roronoa-zoro-whisky-peak`
- `baroque-works-whisky-peak-crowd`
- `nico-robin-miss-all-sunday`
- `portgas-d-ace-arabasta`
- `smoker-arabasta`
- `baroque-works-ship-convoy`

The pack contains 6 atlases, 36 poses, 4 scenes, 8 actor tracks, and 21 timed FX
events. Source generation used the built-in image generation tool with the
approved East Blue sheets as style/identity references. Full prompt summaries,
source hashes, alpha notes, and reviewer notes live in
`art/arabasta/IMAGEGEN_PROVENANCE.md`. Raw source sheets remain only in the
isolated asset workspace.

## Canon receipts

- Whisky Peak: chapters 107–108, Zoro against the bounty hunters.
- Miss All Sunday: chapter 114, a calm arrival/power demonstration and exit.
- Nanohana: chapter 158, Ace intervenes while Smoker is pursuing Luffy.
- Nanohana departure waters: chapter 159, Ace destroys five ships carrying
  Baroque Works Billions with Fire Fist. They are not Marine ships.

The machine-readable evidence and truthful outcome wording live in
`research/story-scenes/arabasta-batch-a.json`. Do not relabel the Nanohana
scene as “Luffy versus Smoker” or a long Ace/Smoker fight.

## Asset source of truth

Workspace: `/Users/shawnos.ai/dead-reckoning-blender-assets`

- `art/arabasta/character-sheets.json`
- `contracts/story-simulations/arabasta-saga-2d-v1.simulation.json`
- `contracts/story-simulations/story-simulation.schema.json`
- `runtime/story-simulations/arabasta-saga-2d-v1/`
- `renders/story-simulations/arabasta-saga-2d-v1/scene-board.png`
- `renders/story-simulations/arabasta-saga-2d-v1/sampler.mp4`
- `manifests/story-simulations/arabasta-saga-2d-v1.json`
- `proofs/arabasta-saga-2d-v1-web-proof.json`

Rebuild and verify:

```bash
cd /Users/shawnos.ai/dead-reckoning-blender-assets
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

Expected verifier result: 6 actors, 36 poses, 4/4 ready scenes, 4,064,886 atlas
bytes.

## Web integration

Repository: `/Users/shawnos.ai/dead-reckoning`

The app now has a generic compatibility layer while the old East Blue paths
remain intact:

- `config/story-simulations.ts` parses the allowlist and selects a pack;
- `lib/simulation.ts` exports `StorySimulationPack` and keeps the East Blue
  alias;
- `components/sim-models.ts` loads one explicit saga chunk at a time and keeps
  one global active host;
- `components/sim-fx.ts` adds reusable bloom/fire/smoke-clash mappings;
- `scripts/sync_story_simulation_pack.py` promotes signed source-free bytes;
- `scripts/check_story_simulations.py` validates hashes, gates, anchors, and
  deterministic sync;
- `scripts/audit_story_simulations.py` proves actual browser behavior;
- `/dev/sim-proof?pack=arabasta&ch=107` selects the new pack in development.

Default production behavior is off. To opt into both completed packs for a
local build:

```bash
NEXT_PUBLIC_STORY_SIMULATION_PACKS=east-blue,arabasta npm run dev
```

The legacy `NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS=1` input still enables East
Blue for compatibility. Do not expose Arabasta by default merely because its
technical proof passed.

Sync and prove:

```bash
cd /Users/shawnos.ai/dead-reckoning
python3 scripts/sync_story_simulation_pack.py --pack arabasta-saga-2d-v1
python3 scripts/check_story_simulations.py --pack arabasta-saga-2d-v1 --require-promoted
python3 scripts/check_simulations.py
npm run build
python3 scripts/audit_story_simulations.py
python3 scripts/audit_simulations.py
```

Expected results:

- Arabasta promoted pack checks: 15/15;
- East Blue deterministic checks: 9/9;
- Arabasta browser audit: 16/16;
- East Blue browser regression: 12/12;
- Next production build: pass.

The browser proof covers pre-gate zero-byte behavior, per-scene atlas loading,
authored pose changes, final holds, backward-scrub disposal/restart,
newest-scene replacement at Whisky Peak and Nanohana, Ace/Smoker, the
chapter-159 Fire Fist convoy destruction, convoy-only lazy loading, and reduced
motion.

## Worktree safety

At handoff time, `/Users/shawnos.ai/dead-reckoning/data/generated/narrative_scenes.json`
was already modified by another session. It was not edited, staged, or included
in this lane. Recheck `git status --short --branch` before committing and stage
only the explicit story-simulation paths.

## Next production batch

Start Arabasta Batch B only after rerunning the checks above:

1. `arabasta-zoro-vs-mr-one`
2. `arabasta-nami-vs-miss-doublefinger`
3. `arabasta-sanji-vs-bon-clay`

Research exact chapter windows, arena anchors, costumes, technique states, and
outcomes before generating art. Build six actor variants: Zoro, Mr. 1, Nami,
Miss Doublefinger, Sanji, and Bon Clay. Diable Jambe is not valid for the
Arabasta Sanji scene. Keep the three Crocodile rounds as a separate Batch C;
never compress them into one generic fight.
