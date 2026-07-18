# Pack intake — wiring a new signed saga pack

The socket is data-only: after the steps below, **zero hand-written TypeScript
or Python changes**. The pack roster the app imports from
(`config/story-packs.generated.ts`) is emitted by the sync script, the compiler
discovers artifacts by scanning `data/generated/`, and the renderer/host
(`lib/simulation.ts`, `components/sim-layer.ts`, `components/sim-models.ts`)
were generic already.

Run every step from the repo root, in this order. Each step's verifier is the
gate for the next — do not skip forward past a red step.

## ① Codex signs the manifest

The asset factory finishes when `blender-assets/manifests/story-simulations/<id>.json`
says `state: "runtime_verified"` with final sha256s for the contract, character
index, and every atlas. **The app never edits `blender-assets/` and never
hand-copies from it.** If atlases appear in `public/art/story-simulations/`
before the manifest is signed, that is not integration — the sync script will
verify-or-refuse them against the signed manifest, and the refusal is the
contract working, not a bug.

## ② Author the anchor table (app-owned)

`canon/story_scene_anchors/<id>.json` — one anchor per scene:
`{"event": "<canon-event-slug>"}` (preferred), `{"island": "<slug>"}`, or a
literal `{lng, lat}` with a `note` explaining why no canon door exists.
If a scene's moment has no canon event yet, author it in `canon/events.json`
first (14-field schema, `verified: false` pending Shawn's manga check — the
`6f7ac7d` pattern), then `python3 scripts/normalize.py` and
`python3 scripts/check_canon.py`.

## ③ Sync the pack

```
python3 scripts/sync_story_simulation_pack.py --pack <id>
```

Verifies every signature, copies atlases to `public/art/story-simulations/<id>/`,
writes `data/generated/story_simulations/<id>.json` (runtime-ready scenes with
verified gates only), and **re-emits `config/story-packs.generated.ts`** — the
pack's id, alias, first-scene chapter gate, and chunk-splitting `import()` thunk
now exist in the app with no code edit.

## ④ Author the treatment

Add one row per scene to `canon/story_scene_playback.json`: journey
enablement + `hold_ms`, the canon `event` slug, and audio bindings (cue ids
from `data/simulation-audio-cues.json`, times as
`{type, occurrence, offset_ms}` against the scene's FX events or literal
`{ms}`). The compiler hard-fails on any scene left without a row — silence is
a decision you must write down (`journey: {enabled: false}`), not a default.

## ⑤ Compile

```
python3 scripts/compile_scene_playback.py
```

Byte-stable output; hard-fails on unknown scenes/packs/cues, bindings past the
scene end, or journey holds too short for the scene to finish.

## ⑥ Audits (frozen tree — HMR kills mid-run browser audits)

```
python3 scripts/check_story_simulations.py --pack <id>   # includes registry drift + determinism
python3 scripts/check_simulations.py
python3 scripts/audit_story_simulations.py               # browser, boots its own port
python3 scripts/audit_journey.py                         # journey stops honor the new holds
python3 scripts/audit_simulation_audio.py                # if the pack ships audio bindings
npx tsc --noEmit && npm run build
```

## ⑦ Enable

Add the pack id (or its alias) to `NEXT_PUBLIC_STORY_SIMULATION_PACKS` —
`.env.development` for local, Railway env for production. Production also
requires the rights wall: `npm run audit:sim-audio -- --release` must pass
(every enabled cue `cleared`, receipts on disk) before the flag flips.
