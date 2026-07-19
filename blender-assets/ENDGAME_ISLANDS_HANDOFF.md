# Endgame Islands — Egghead, Wano/Onigashima, Elbaph

Status: built, exported, registered, synced into the app, and locally verified on 2026-07-19.

## What the Journey now has

| Runtime scene | Chapter behavior | Recognizable topology |
|---|---:|---|
| Egghead Future Island system | base 1061; upper phase 1065; Punk Records 1066 | cold sea and ice, tropical Fabriophase, future city, cloud layer, egg laboratory, Frontier Dome |
| Wano Country and Onigashima | country base 793; regions 909; fortress detail 978; geographic shift 997-1109 | high walled bowl, inland sea, six regional nodes, central mountain/capital, separate animated skull fortress, port, torii, roads, katana, Flame Clouds |
| Elbaph Treasure Tree Adam system | approach 1127; Underworld 1130; full verified tree/Sun World 1132 | sleeping-mist sea route, snowy roots, giant ecology, castle/bar landmarks, world tree, branch settlement |

Chapter 1188 is now the app ceiling because VIZ confirms the official release. The fan API currently stops at 1185, so it is not allowed to clamp the Journey backward. Chapter 1188-specific event geometry and any exact Nine Worlds/iceberg-theory map remain fail-closed until page-level evidence is attached.

## How to see it

1. Open `http://localhost:3000/?ch=1188`.
2. Open **3D islands** in the Journey HUD.
3. Choose **Egghead Future Island system**, **Wano Country and Onigashima system**, or **Elbaph Treasure Tree Adam world system** and press **dive**.
4. The GLB appears at close Mercator zoom. The globe/far view uses the transparent fallback and unloads the 3D model.

Earlier chapter checks:

- `/?ch=1061` — Egghead lower island only.
- `/?ch=1065` — Egghead upper laboratory phase opens.
- `/?ch=909` — Wano's country regions open while later fortress detail stays fogged.
- `/?ch=978` — Onigashima's skull, port, roads, and katana open.
- `/?ch=996` — Onigashima remains offshore in its pre-lift position.
- `/?ch=997` — Kaidou's Flame Clouds appear and the complete 39-child Onigashima hierarchy lifts; this is a geometry transform, not an image swap.
- `/?ch=1027` — the geographic track has carried the island toward the Flower Capital.
- `/?ch=1039` — the island is redirected away from the capital.
- `/?ch=1049` — Onigashima is landed outside the Flower Capital and the Flame Clouds are gone.
- `/?ch=1109` — the later cover-story state moves the island back toward Wano's sea and below the water line.
- `/?ch=1130` — Elbaph Underworld opens.
- `/?ch=1132` — Treasure Tree Adam and the Sun World settlement open.

The Wano motion is a local geographic shift inside the Wano scene, not a globe-spanning relocation: Onigashima never leaves Wano. Journey chapter changes sample the named GLB action `onigashima_geographic_shift`, so forward chapter motion advances the island, backward scrubbing restores its earlier location, and pausing Journey freezes the geography. Verified story states are fixed to chapter checkpoints; the continuous path between those states is explicitly a visual interpolation because the manga does not publish survey coordinates.

## Geographic-motion proof

- Named GLB action: `onigashima_geographic_shift` (5.833 seconds, two root-transform channels)
- Animated root: `Onigashima geographic root` with 39 child objects
- Chapter track: 793, 996, 997, 1027, 1039, 1049, 1108, 1109
- Flame Clouds: 14 geometry nodes, visible only from chapter 997 through 1048
- Five-second motion preview: `previews/onigashima-geographic-shift-preview.mp4`
- Six-state contact sheet: `previews/onigashima-geographic-shift-contact-sheet.png`
- Runtime audit: `../scripts/audit_onigashima_geography.mjs`

The in-app check at chapters 997 and 1049 confirmed the model is loaded in the close Mercator dive and changes geographic state with the Chapter control. The present dive camera does not yet track the moving skull closely enough, and the Wano geometry is still LOD1 blockout quality; improving that camera and replacing the blockout with the LOD0 art target are the next presentation pass.

## Source of truth

- Runtime registry: `manifests/runtime-3d.json`
- Build ledger: `manifests/endgame-island-builds.json`
- Evidence policy: `research/endgame-islands-chapter-1188-evidence.json`
- Runtime proof: `proofs/endgame-islands-ch1188-runtime-proof.json`
- Contracts: `contracts/*-system.visual.json`
- Editable Blender sources: `source/*-system.blend`
- Exported models: `runtime/*-system.glb`
- App copies: `../public/art/runtime/*-system.{glb,png}`

## Art direction and next pass

The Blender models are LOD1 world-map geometry, not final cinematic closeups. The three high-detail reference plates in `art/endgame-islands/reference-plates/` are the LOD0 targets. The next pass should preserve the same component IDs and gates while replacing blocks with modular kits:

1. Egghead: cracked-shell modules, dense future-city kit, cloud shader, and a detached Punk Records state.
2. Wano: region-specific terrain/foliage, better Fuji/capital skyline, Onigashima cave/road kit, and a chapter-aware chase camera that keeps the moving fortress framed.
3. Elbaph: sculpted Adam trunk and branches, giant-scale halls/props, better root snow, fog volume, and evidence-backed current-chapter overlays.

Theory assets belong in a separate toggleable overlay. Never merge them into the canon base model.

## Rebuild and verify

```bash
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender --background --python blender-assets/scripts/build_endgame_island_batch.py -- --resolution-x 1400 --resolution-y 1000
python3 blender-assets/scripts/register_endgame_islands.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 scripts/sync_runtime_assets.py
node scripts/audit_onigashima_geography.mjs
npm run build
```

The workspace contains concurrent user/session changes. This batch was not committed or pushed.
