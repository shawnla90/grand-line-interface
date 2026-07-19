# Grand Line Interface — Master Roadmap

_The single reconciliation point for every track building this atlas. Three
parallel builders work the repo; this file is how none of their threads get
lost. Update it when a phase ships or a new thread starts. The in-app
provenance stays in `canon/build_log.json` (the shipwright's log); this file is
forward-looking where that one is backward-looking._

## The three tracks

| Track | Builder | Lane | Live state |
|---|---|---|---|
| **Camera & scale** | Claude Code session | `components/runtime-models.ts`, `components/WorldMap.tsx`, orbit/directory components | Un-crushing archipelago `visual_fit` (Totto Land, Sabaody); next: dive-to island directory, grab-and-spin orbit |
| **Assets & simulation** | Codex (Sol) | `../dead-reckoning-blender-assets/` — contracts, GLBs, character art | 27 runtime-ready 2.5D scenes and 42 signed atlases through the four-fight Enies Lobby CP9 spine; next: Robin, Franky, Usopp support |
| **Canon & lore** | Claude Code session (this track) | `canon/`, `lib/schema.ts`, `lib/canon.ts`, `scripts/`, entry pages | Events layer, verification queue, red Road Poneglyphs, presence backfill |

**Cross-track rules.** The asset workspace is read-only to the app tracks —
requests travel as reports in `data/review/*.md` (the
`asset-track-report.md` pattern), never as patches. Hand-authored data lives
only in `canon/`. Every claim ships `verified:false` until a human checks the
page. `scripts/check_canon.py`, `check_scenes.py`, `check_buildlog.py` and
`npm run build` must stay green on every landing.

## Shipped (phases 1–9)

1–4 — data spine, chapter-axis atlas, Straw Hat journey + ship morph, cartographic chart, `/admin/place`.
5 — crews, characters & ships on the map (presence windows, portrait rings, shipwright's log).
6 — real chapter-gated art (Jolly Rogers, portraits, fruits, islands) with SVG fallbacks.
6A — presence lenses: By Crew / By Fruit / By Haki (`lib/lenses.ts`, `?lens=`).
7A — Blender asset factory: narrative contracts, 2.5D plates, 3D blockouts.
8 — every dot a door: entry pages (`/character`, `/crew`, `/fruit`), OG cards, page platform.
9 — the third dimension: three.js GLB layer on the globe (`components/glb-layer.ts`), 11 runtime islands, contact sheets, asset-track report. Flags `NEXT_PUBLIC_RUNTIME_3D_*` still OFF in prod.

## In flight

- **Story simulation + audio integration:** the 12-scene East Blue pack,
  10-scene Arabasta pack, Luffy/Enel climax, and four-fight Enies Lobby CP9
  pack are runtime-ready behind `NEXT_PUBLIC_STORY_SIMULATION_PACKS`. That is
  27 scenes and 42 signed actor/tableau atlases. Enies Lobby now runs from
  Luffy/Blueno's first Gear Second through Sanji/Jabra's first Diable Jambe,
  Zoro/Kaku's Asura finish, and Luffy/Lucci's Jet Gatling. The four matching
  prototype voice clips fire on the authored visual events. The app-side plan
  for generic journey stops, chapter-local SFX, a cleared audio registry, the
  developer soundboard, and the chapter-159 Ace Fire Fist vertical slice is in
  `docs/STORY_SIMULATION_AUDIO_INTEGRATION_PLAN.md`. The current animation
  receipt and ordered Robin/Franky/Usopp → Sabaody → Marineford queue is
  in `blender-assets/handoffs/CLAUDE_CODE_GRAND_LINE_ANIMATION_NEXT.md`.
- **Camera & scale:** the ~90s journey cinematic shipped (`aa02516`) but Shawn reports it doesn't track the voyage line and glitches at Skypiea — that session is FIXING it now and owns `lib/journey.ts`/`Atlas.tsx`/`WorldMap.tsx`/`ChapterDock.tsx` until the fix lands. NOTE for that fix: 2.5D story cards are vertical billboards — the journey camera must PITCH (~50–60°) during close dwells or they render edge-on (invisible).
- **Assets:** Codex superseded the rigid pilot with the full **East Blue 2.5D pack** (14 illustrated atlases, 12 runtime-ready scenes) — now INTEGRATED app-side (`d94eaf3`): signed sync pipeline, deterministic evaluator, sim-layer/sim-models hosts, 9-check + 12-audit battery, ch-51 proof PASSED on the real host. Codex may set `integration_ready: true` (see `data/review/east-blue-2d-integration-report.md`). Flag `NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS` default OFF; dev proof stage at `/dev/sim-proof`.
- **Deferred on the journey fix** (specs in `data/review/east-blue-2d-integration-report.md`): the ~3-line WorldMap `syncSimulations` wiring; journey MOMENT stops (120s run, 5 East Blue beats with facts from `world.events`); `journeyFocus` camera damping; the `?record=1` MediaRecorder button (user-approved; map-only capture caveat — DOM markers incl. the ship don't reach canvas).
- **Asset-track requests outstanding** (from `data/review/asset-track-report.md`): add `projection_support` to unlock 14 models; fix 3 refused models (`arabasta-kingdom`, `water-7`, `skypiea-sky-system`); resolve the Mary Geoise gate contradictions; verify Wano's reveal beats.
- **Canon & lore (this plan):**
  - **Phase 1 — master ledger.** This file + `scripts/verification_queue.py` → `data/review/verification-queue.md` (275 pending claims at first run) + README roadmap refresh.
  - **Phase 2 — canon events layer.** `canon/events.json` (duels, wars, deaths, declarations…) → zod → `data/canon.json` → chapter-gated `eventsAtChapter()`; East Blue seeded complete first, then Arabasta → Marineford → Sabaody → Wano → Egghead. Entry pages at `/event/[slug]`. Map pins + Events lens wait for integration.
  - **Phase 3 — Road Poneglyphs in red.** DONE in the mark: `components/marks/poneglyph.ts` is kind-aware (`poneglyphInk(kind)`, road = aged crimson `#a12a33`), back-compatible default keeps the map compiling unchanged; island pages already show the red chip. Phase-6 flips in `WorldMap.tsx` (three spots, one line each): `makePoneglyphElement()` take a kind and call `poneglyphSvg(18, kind)` (~line 593, call site ~1960 has `pg.kind`); the `poneglyph-glint` `circle-color` (~line 1685) becomes a per-kind match expression; the tooltip kicker color (~line 2288) uses `poneglyphInk(pg.kind)`. NOTE: WorldMap.tsx contains a NUL byte — grep/ugrep treat it as binary; use `grep -a`.
  - **Phase 4 — identity backfill.** MEASURED, the README wishlist was already done: all 6 Worst Generation crews, Sun Pirates, Baroque Works and the Revolutionary Army were in presence (31 crews / 102 windows). This phase added the real gaps: Rayleigh (Sabaody → Amazon Lily → Rusukaina), Vivi (Whisky Peak → Arabasta), Ener (Upper Yard) — 19 characters now windowed. Still missing: Yamato, Magellan (no windows), Koby (no upstream character row at all). Bounties need NO seeding — `sync_wiki_characters.py` already parses full histories; `canon/bounties.json` is the empty-by-design repair door.
  - **Phase 5 — East Blue simulation briefs.** Beat-sheets for Arlong Park, Syrup Village, Orange Town, Loguetown in the `SceneEvent`/`camera_cue`/`fx` vocabulary, delivered via `data/review/`; Codex's Zoro/Mihawk pilot is the template.
  - **Phase 6 — integration** (after the camera track lands): red glint paint in `WorldMap.tsx`, event pins, Events lens, `FLAGS.narrativeScenes` wiring.

## Don't-lose-these backlog

- **Verify the canon** — burn down `data/review/verification-queue.md` to zero; islands from `derived` → `canon` via `/admin/place` or a license-clean dataset.
- **`FLAGS.narrativeScenes`** — the scene registry (`lib/scenes.ts`, 11 contracts) is ready but nothing imports it.
- **Wano screen-space renderer** — Wano is a marker-style asset, not a map model; needs its own render path and verified reveal beats.
- **Runtime-3D prod flags** — `NEXT_PUBLIC_RUNTIME_3D_ASSETS` / `_TRANSITIONS` off pending Cloudflare bundle-size blockers.
- **4th Road Poneglyph policy** — deliberately excluded (its location IS the plot); the Rio Poneglyph likewise (not a physical stele). Documented in `canon/poneglyphs.json` `_deliberately_excluded`; do not "complete" the set.
- **Iceberg lore & theory layers** — chapter-gated theory overlays (README "Fork it").
- **Roster Jolly Rogers** — each new presence crew needs one original SVG mark.
- **Distribution** — Reddit go-to-market recon in `docs/distribution-reddit.md` (r/OnePiece 9:1 rule).
