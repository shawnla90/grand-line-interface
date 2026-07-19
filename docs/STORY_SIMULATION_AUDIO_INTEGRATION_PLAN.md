# Story Simulation + Audio Integration Plan

_Prepared 2026-07-18. This is the app-side handoff for moving the signed East
Blue and Arabasta scene packs from proof stages into chapter playback, the
cinematic journey, and the Epic Journey audio timeline._

## Outcome

When the reader reaches a scene's verified chapter, the globe can frame its
anchor, run the deterministic animation once, play synchronized original or
cleared sound design after an explicit sound gesture, and hold the final
tableau as the chapter's visible history. The same scene must work in three
modes without separate implementations:

1. **Manual chapter exploration** — entering the chapter and moving close to
   the anchor starts the scene once; moving backward closes the spoiler gate
   and resets it.
2. **Sail with story stops** — the voyage pauses, dives to the scene, lets the
   complete scene run, then returns to the route.
3. **Epic Journey** — the visual master, music/voice beds, and scene-local
   sound effects share one deterministic timeline.

The browser plays only checked-in, hashed derivatives. Search and generation
APIs are build tools, never runtime dependencies.

## What is already shipped

This is an extension of the current app, not a replacement runtime.

- `components/WorldMap.tsx` already calls the generic `syncSimulations()` host
  when `NEXT_PUBLIC_STORY_SIMULATION_PACKS` is enabled.
- `components/sim-models.ts` already owns chapter gates, viewport/zoom gates,
  one-play clocks, hidden-tab pause, backward reset, and final-frame holds.
- `lib/simulation.ts` already evaluates every actor and visual FX event at an
  exact scene-local millisecond.
- `lib/journey.ts` and `lib/epic-journey.ts` already provide the pure visual
  master that camera and audio can sample.
- `lib/epic-audio-player.ts` already plays long-form voice/music lanes, fades
  cuts, and ducks the score under foreground cues.
- `scripts/prepare_epic_audio.mjs`, `scripts/audit_epic_audio.mjs`, and the Epic
  browser audit already establish the normalize, hash, gate, and prove pattern.

Current scene inventory: **27 runtime-ready scenes**, consisting of 12 East
Blue scenes, 10 Arabasta scenes, one Skypiea scene, and four Enies Lobby CP9
fights. The art factory remains the source of the signed atlas/scene packs; the
web app remains the owner of chapter playback, camera, audio, feature flags,
and release rights.

## Bridge status

The generic scene host, compiled playback manifest, shared audio director,
scene-local audio cursor, journey stops, gesture gate, and backward-reset
behavior are implemented. The remaining release gaps are:

1. `NEXT_PUBLIC_STORY_SIMULATION_PACKS` remains off by default and still needs
   an explicit deployment allowlist decision.
2. The Gear Second, Diable Jambe, Santoryu, and Jet Gatling voice clips are
   correctly synchronized but remain `local_prototype_only`.
3. The reusable cleared sword, beam, punch, debris, crowd, and ambience library
   is not yet complete for public distribution.
4. A developer soundboard and final bus-level mix pass remain useful before a
   wider release.

## Canonical app-side contracts

### 1. Scene playback manifest

Add `canon/story_scene_playback.json`. It is deliberately app-owned: changing a
mix or camera dwell must not invalidate or regenerate a signed character atlas.
Each row supplies journey treatment and sound bindings for an existing scene.

```json
{
  "scene_id": "ace-fire-fist-destroys-billions-fleet",
  "journey": {
    "enabled": true,
    "hold_ms": 9000,
    "zoom": 5.8,
    "pitch": 55,
    "orbit_deg_per_sec": 0
  },
  "audio": [
    {
      "id": "ace-charge",
      "cue_id": "fire-charge-01",
      "at": { "event_type": "speed-lines", "occurrence": 0, "offset_ms": 0 },
      "gain": 0.68,
      "pan": -0.18,
      "playback_rate": 1
    },
    {
      "id": "fleet-hit",
      "cue_id": "heavy-fleet-impact-01",
      "at": { "event_type": "impact", "occurrence": 0, "offset_ms": -40 },
      "gain": 0.9,
      "pan": 0.2,
      "playback_rate": 1
    }
  ]
}
```

Prefer an existing visual event plus an offset over copying an absolute time.
This keeps a sword flash and its sword cut together when a scene is retimed.
Allow `{ "ms": 1200 }` only for Foley or ambience without a visual event.

The compiler must reject unknown scene IDs, unknown event occurrences, times
outside `duration_ms`, duplicate binding IDs, and journey holds shorter than the
scene. It should emit `data/generated/story_scene_playback.json` with all event
references resolved to exact milliseconds.

### 2. Audio asset registry

Add `data/simulation-audio-cues.json` for sound assets and provenance:

```json
{
  "id": "heavy-fleet-impact-01",
  "kind": "sfx",
  "family": "impact-heavy",
  "src": "/audio/simulations/impact/heavy-fleet-impact-01.mp3",
  "master": "assets/audio/simulations/impact/heavy-fleet-impact-01.wav",
  "sha256": "...",
  "duration_ms": 1450,
  "sample_rate": 48000,
  "channels": 2,
  "source": "generated",
  "license": "elevenlabs-paid-output",
  "rights_status": "cleared",
  "receipt": "assets/audio/licenses/elevenlabs/2026-07-18.json",
  "attribution": null,
  "max_voices": 4
}
```

Allowed release states are `cleared`, `attribution_required`,
`local_prototype_only`, and `blocked`. Production builds fail when an enabled
cue is not cleared or is missing required attribution/receipt metadata.

### 3. One scene clock, two cursors

Keep `components/sim-models.ts` as the only clock owner. The renderer continues
sampling its visual FX cursor. A new `SimulationAudioPlayer` samples a separate
compiled audio-event cursor using that exact same `getTimeMs()` value.

Rules:

- A cue fires once only when local time crosses its timestamp going forward.
- Moving backward rebuilds the fired set but does not make reverse scrubbing
  noisy. It becomes eligible again only on the next forward scene replay.
- Unmount, pack switch, chapter rollback, journey stop, or map teardown fades
  and releases every voice owned by that scene.
- A final tableau never fires audio. A replay button explicitly resets both
  visual and audio cursors to zero.
- Variant, pan, gain, and playback rate are authored values. Do not choose a
  random sound at runtime; deterministic playback is part of the proof.

## Audio runtime

Create one user-gesture-unlocked `AudioDirector` rather than a second unrelated
mute system.

```text
master
├── score       long music beds; ducked under voice and large impacts
├── voice       narration/dialogue; one foreground chain
├── ambience    wind, rain, crowd, ocean, fire loops
└── sfx         sword, beam, punch, impact, debris one-shots
```

- Keep media elements for long score/voice tracks, routed through Web Audio
  gain nodes when the shared director lands.
- Decode short SFX to `AudioBuffer`s; connect each voice through gain and
  stereo-pan nodes. Add a conservative master limiter.
- Use an LRU buffer cache and preload only the selected scene's cue set after
  its chapter, viewport, zoom, and sound-opt-in gates are all open.
- Cap simultaneous voices by family: one ambience loop, four blade cuts, four
  impacts, and one voice lane are sensible starting values.
- Keep sound off on cold load. `Epic Journey with audio` and a global sound
  toggle are valid unlock gestures. Never attempt audible autoplay.
- Persist master mute and bus gains locally. `prefers-reduced-motion` still
  produces the safe static tableau; it does not silently enable audio.

## Journey and chapter wiring

Replace the East-Blue-only story-stop builder with
`buildStoryJourneyStops(world, enabledPacks, playbackManifest)`.

- `STORY_JOURNEY_ON` becomes true when any signed story pack or runtime 3D
  spotlight is enabled.
- A scene enters the journey only when its signed chapter gate is verified and
  its playback row has `journey.enabled: true`.
- Labels and facts still resolve from live canon events; the playback manifest
  contains treatment, not duplicated lore.
- The scene's anchor remains the signed pack coordinate. Camera zoom/pitch and
  hold length remain app-owned.
- Ordinary Sail uses `hold_ms` instead of the current hard-coded eight seconds.
  Epic traverses the scene's full local-time range, so its last cue and final
  pose complete before the camera recovers.
- Keep `NEXT_PUBLIC_STORY_SIMULATION_PACKS=east-blue,arabasta` as the staging
  activation path. Retain the legacy East Blue bit only as a compatibility
  alias until deployment configuration has migrated.

### First 16 scene treatments

| Chapter | Scene | Journey | Initial sound cut |
|---:|---|:---:|---|
| 1 | Roger's execution | Yes | crowd hush, rope/wood creak, wind, low era hit |
| 1 | Fruit and promise | Supporting | fruit bite, surf, warm promise sting |
| 2 | Luffy punches Alvida | Yes | rubber stretch, fast whoosh, heavy punch |
| 20 | Luffy vs Buggy | Yes | body detach, rubber snap, launch, distant impact |
| 40 | Luffy vs Kuro | Yes | silent-step rush, claw cuts, body hit |
| 51 | Zoro vs Mihawk | Yes | blade draw, three sword cuts, Yoru sweep, impact |
| 66 | Luffy vs Krieg | Yes | metal launch, explosion, armor tear, punch |
| 68 | Sanji leaves Baratie | Supporting | sea room tone, footsteps, emotional sting |
| 81 | Nami asks for help | Yes | quiet wind, cloth movement, resolve hit, walk-up dust |
| 93 | Arlong Park final clash | Yes | windup, hit, stone cracks, building collapse |
| 99 | Luffy on the scaffold | Yes | rain loop, thunder crack, lightning, scaffold break |
| 100 | The crew's vows | Yes | ocean wind, barrel stomps, sail swell, departure sting |
| 107 | Zoro vs bounty hunters | Yes | crowd, sword draw, layered cuts, impacts, dust |
| 114 | Robin arrives | Yes | cloth movement, hush, Hana-Hana bloom, route pulse |
| 158 | Ace blocks Smoker | Yes | smoke pressure, fire wall, flame/smoke clash |
| 159 | Fire Fist destroys the fleet | Yes | fire charge, huge whoosh, hull hit, wood collapse, fire, splash |

"Supporting" scenes still play during manual chapter exploration, but the
first cinematic cut may skip them to protect pacing. The list is data; changing
a scene from supporting to a journey stop does not require renderer code.

## Where the sound comes from

### One Piece API

The current API documentation exposes encyclopedia categories—sagas, fruits,
chapters, tomes, episodes, dials, movies, swords, haki, gears, techniques,
crews, characters, boats, arcs, and locations. It does **not** expose music,
dialogue, or downloadable sound effects. Use it to help label and gate scenes,
not to source media. An API response also would not, by itself, grant reuse
rights to anime audio.

### Recommended source stack

1. **Primary SFX: ElevenLabs Sound Effects API, offline ingestion.** Generate
   original one-shots and loops from functional descriptions such as "three
   rapid steel blade cuts, dry and close, no music". It supports explicit
   duration/loop controls and downloadable MP3/WAV output. Put the API key only
   in a local or server-side preparation script. Check the active plan's terms
   and save a receipt with every accepted generation.
2. **Primary music: original instrumental saga beds.** Eleven Music can create
   score via API on eligible paid plans, but media/game rights depend on the
   subscription and use case. Generate original cues by mood, tempo, structure,
   and instrumentation. Never ask it to reproduce a named One Piece theme,
   composer, performance, or voice.
3. **Safe base library: Kenney CC0 packs.** Impact, RPG, UI, and digital-audio
   packs are useful raw layers for punches, blades, clicks, and beams. These are
   downloadable packs, not a runtime API.
4. **Discovery fallback: Freesound.** Its API supports search, metadata, and
   authenticated original-file downloads, but individual sounds carry CC0,
   Attribution, or Attribution-NonCommercial licenses, and free API usage is
   non-commercial. Use only through a rights-aware ingestion step and never
   assume a search result is production-cleared.

Do not make Spotify, Apple Music, YouTube, anime soundboards, or ripped episode
audio part of the production dependency. Metadata/playback access is not a
license to package the track into this app. The current One Piece OST and voice
clips under `assets/audio/epic-journey/` remain local-prototype material until
separately cleared or replaced.

Research references checked for this plan:

- [API One Piece documentation](https://api-onepiece.com/fr/documentation)
- [ElevenLabs Sound Effects API](https://elevenlabs.io/docs/overview/capabilities/sound-effects)
- [Eleven Music API quickstart](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/music)
- [Freesound API resources](https://freesound.org/docs/api/resources_apiv2.html)
  and [API terms](https://freesound.org/docs/api/terms_of_use.html)
- [Kenney Impact Sounds](https://www.kenney.nl/assets/impact-sounds) and
  [Kenney RPG Audio](https://www.kenney.nl/assets/rpg-audio)

## Asset preparation pipeline

Add `scripts/prepare_simulation_audio.mjs`:

1. Read approved WAV/FLAC/MP3 masters under `assets/audio/simulations/`.
2. Verify a matching provenance/rights receipt before processing.
3. Strip metadata, generate a 48 kHz browser derivative, record duration and
   hashes, and write the audio registry.
4. Peak-normalize short transients by family; loudness-normalize long ambience,
   voice, and score separately. Do not flatten every punch to the same LUFS.
5. Emit an attribution page artifact for all `attribution_required` files.

Add `scripts/audit_simulation_audio.mjs` to validate paths, hashes, sample rate,
duration, cue references, rights state, attribution, concurrency families, and
chapter-safe bindings.

Add `/dev/audio-board` as a local audition/mix surface:

- filter by family, source, and rights state;
- play dry cue and scene-timed cut;
- view duration, waveform, gain, pan, and provenance;
- audition the exact scene at 0.5x/1x/2x without editing JSON by hand;
- export only reviewed values back to `canon/story_scene_playback.json`.

## Phased build

### Phase 0 — activate and reconcile (half day)

- Turn on `east-blue,arabasta` in staging, never by changing the default.
- Replace the stale East-Blue-only journey condition with the generic pack
  allowlist.
- Compile all 16 playback rows and prove every journey hold is at least the
  scene duration.

### Phase 1 — deterministic audio core (1–2 days)

- Add schemas/compiler, registry, `AudioDirector`, scene audio cursor, cleanup,
  unlock/mute controls, and test hooks.
- Route the existing Epic player's mute/duck state through the director while
  preserving its long-form timeline behavior.

### Phase 2 — Ace Fire Fist vertical slice (1 day)

Build six original cues for chapter 159: fire charge, Fire Fist whoosh, fleet
impact, timber break, fire crackle, and debris splash. Bind them to the existing
1450/3000/3450/4250/5650/6750 ms visual events, mix the full nine-second cut,
and prove manual, Sail, and Epic modes.

### Phase 3 — East Blue and Arabasta batch (2–3 days)

- Finish the remaining 15 scene cuts, starting with ch51 Zoro/Mihawk, ch20
  Buggy, ch93 Arlong, ch107 Whisky Peak, and ch158 Ace/Smoker.
- Compose three to five cleared saga beds rather than a unique song for every
  fight: East Blue adventure, Baroque tension, Arabasta desert, emotional
  resolve, and boss battle.
- Keep dialogue optional. The fight must read from movement and effects without
  needing actor imitation or copyrighted quotes.

### Phase 4 — soundboard, proof, and release gate (1–2 days)

- Ship the local audio board and batch-preparation commands.
- Extend Playwright audits across Chrome and WebKit/mobile behavior.
- Generate a human-readable attribution/rights report.
- Promote only `cleared` tracks to the public release channel.

The first useful, production-shaped result is the chapter-159 vertical slice.
The full 16-scene sound pass is roughly **5–8 focused build days**, excluding
time spent choosing generations or negotiating third-party rights.

## Required proofs

The work is complete only when automated checks demonstrate:

1. Flags off: no simulation code, atlas, or audio requests.
2. Before a gate: no scene, caption, preload, or sound leaks.
3. At chapter 159: the Ace scene starts at local time zero and each cue fires
   at its compiled event crossing, never on every render frame.
4. Moving backward below the gate removes the scene and resets both cursors;
   re-entering replays once from the start.
5. Epic reaches each enabled anchor, holds for the complete scene, and recovers
   to the route without leaving audio or camera ownership behind.
6. Audio remains silent until an explicit user gesture; mute works across Epic
   and scene SFX; a hidden tab does not advance the scene or its audio.
7. Only selected-scene files preload; pack changes evict unneeded decoded
   buffers; no API key or external audio URL reaches the client bundle.
8. Production refuses `local_prototype_only`, blocked, missing-receipt, or
   missing-attribution audio.
9. Existing canon, scene, simulation, Epic audio, Epic journey, build, and
   browser audit suites remain green.

## First implementation order for the next session

1. Add and validate `canon/story_scene_playback.json` for all 16 scenes.
2. Generalize `config/journey-stops.ts` and exact scene dwell durations.
3. Add the cleared audio registry and offline preparation/audit scripts.
4. Implement the shared audio director and simulation event cursor.
5. Produce and integrate the six chapter-159 Fire Fist cues.
6. Extend the browser proof for chapter 159, then batch the other 15 scenes.
