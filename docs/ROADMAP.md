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
| **Assets & simulation** | Codex (Sol) | `../dead-reckoning-blender-assets/` — contracts, GLBs, character art | 2.5D character pilot: Baratie-era Zoro + Mihawk illustrated sprites replacing the rigid-part mannequins |
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

- **Camera & scale:** archipelago un-crush → island directory → orbit controls (plan `linked-frolicking-toucan`).
- **Assets:** Zoro/Mihawk 2.5D pilot (pose sheets keyed; atlas packaging + composited review render pending). Not promoted to `integration_ready` until the visual proof passes.
- **Asset-track requests outstanding** (from `data/review/asset-track-report.md`): add `projection_support` to unlock 14 models; fix 3 refused models (`arabasta-kingdom`, `water-7`, `skypiea-sky-system`); resolve the Mary Geoise gate contradictions; verify Wano's reveal beats.
- **Canon & lore (this plan):**
  - **Phase 1 — master ledger.** This file + `scripts/verification_queue.py` → `data/review/verification-queue.md` (275 pending claims at first run) + README roadmap refresh.
  - **Phase 2 — canon events layer.** `canon/events.json` (duels, wars, deaths, declarations…) → zod → `data/canon.json` → chapter-gated `eventsAtChapter()`; East Blue seeded complete first, then Arabasta → Marineford → Sabaody → Wano → Egghead. Entry pages at `/event/[slug]`. Map pins + Events lens wait for integration.
  - **Phase 3 — Road Poneglyphs in red.** Per-kind ink in `components/marks/poneglyph.ts` (road = aged crimson); `WorldMap.tsx` glint recolor deferred to integration.
  - **Phase 4 — identity backfill.** Presence windows for the rest of the Worst Generation, Sun Pirates, Baroque Works, admirals, Revolutionary Army. (Bounties need NO seeding — `sync_wiki_characters.py` already parses full bounty histories; `canon/bounties.json` is the empty-by-design repair door.)
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
