# Dynamic geography handoff — Water 7, Red Line, and Fish-Man descent

Date: 2026-07-19

This batch is integrated into the web app. It is not a set of chapter images:
all three systems are signed GLBs loaded by the shared MapLibre/Three runtime,
with glTF node extras controlling spoiler gates and named Blender Actions
sampled from the reader's chapter.

The working tree was already shared and dirty. This pass did not commit, push,
delete media, or overwrite unrelated work.

## What is now in Journey

### Water 7, Aqua Laguna, and the Sea Train network

- Runtime id: `water-7-sea-train-network`
- 334 objects, 26,352 triangles, 18 materials
- GLB: 1,589,396 bytes
- GLB SHA-256: `d706bbb7ccfba5ac70ad59a1404172db1c270a4b6d0c132cbe88d6fdec273e5d`
- Fallback SHA-256: `9e56a1f1e4997d0a917751fea6dbc2cb61abcda52bf1f619f4293847305f2251`

The old source had a keyed Puffing Tom but the production GLB contained no
animations. The replacement exports four real clips:

| Clip | Purpose | Duration |
|---|---|---:|
| `water7_puffing_tom_route_cycle` | moving commercial Sea Train | 5.042 s |
| `water7_rocketman_route_state` | chapter-sampled Water 7 to Enies pursuit | 5.042 s |
| `water7_aqua_laguna_tide_state` | chapter-sampled flood/wave intensity | 5.042 s |
| `water7_enies_waterfall_cycle` | permanent Enies waterfall motion | 4.208 s |

Expected chapter states:

| Chapter | Geography |
|---:|---|
| 322 | submerged rails, Shift/Blue Stations, Puffing Tom, and known route relationships |
| 323 | Water 7's terraced city and radial canals |
| 358 | Enies Lobby's never-night court, land bridge, abyss, and permanent waterfall ring |
| 363–367 | Aqua Laguna floods Water 7 and disturbs the route waters |
| 365–378 | Rocketman route state is visible and advances toward Enies Lobby |
| 375 | Day Station and the Enies waterfall ambient clip are active |
| 656 | Puffing Ice is available |
| 657 | complete currently verified local scene |

Accuracy boundary: Aqua Laguna is a temporary Water 7 / approach-water state.
Enies Lobby is not converted into a flooded Water 7 clone; its authored water
system is the permanent waterfall/void. Sea Train branches are a cited
relationship graph, but exact bearings and distances remain schematic.

### Mary Geoise, Red Port, and the Bondola ascent

- Runtime id: `mary-geoise-red-line`
- 89 objects, 6,084 triangles, 9 materials
- GLB: 422,652 bytes
- GLB SHA-256: `f4fcebd62cd09f1abce1b4efd26985b70f6f330ca1947423488a53cf9955a4a3`
- Fallback SHA-256: `c375f08270d852402034454916e5f7986c8c3bf7fc0bb47e40f83718baed2f45`

The rectangular cliff block was replaced by seven irregular rock strata, a
summit plateau/city distinct from Pangaea Castle, Paradise-side Red Port,
Bondola cables and cabin, and a high-altitude cloud bank.

Named clips:

- `mary_geoise_bondola_cycle` — Red Port to summit ascent, active from chapter 905
- `red_line_cloud_drift` — persistent summit cloud motion from chapter 142

Canon correction: Bondola is a boat-shaped lift that carries people. Lawful
sailors leave their original ship at Red Port and obtain another ship on the
other side. The GLB therefore does not hoist an arriving ship up the wall.

The New World-side Red Port is modeled and addressable but remains
`chapter_to_verify`, default-hidden, and has no reveal chapter in its glTF
extras. The exact Red Line coastline is also not asserted as survey data.

### Sabaody coating and Fish-Man descent

- Runtime id: `fish-man-red-line-descent`
- 68 objects, 15,156 triangles, 14 materials
- GLB: 826,768 bytes
- GLB SHA-256: `412f6e45fdae9f2a1f68b86d8b457f8ac8602fac17055eecd5e3aefd33646d42`
- Fallback SHA-256: `90abfec5f6e2bdfcf4c50296ddf10d180826f823c401e4c290911a62bcd90f87`

This is a new vertical transition system, separate from the complete
`fish-man-island` destination asset. It contains the Sabaody coating work area,
resin-coated Sunny, Red Line undersea walls, depth/light bands, pressure ring,
downward plume, Kraken landmark, deep-sea creatures, volcanic vents, trench,
and a distant destination glow.

Expected chapter states:

| Chapter | Descent state |
|---:|---|
| 496 | the 10,000-meter route is explained and the cross-section becomes available |
| 507 | coating work area/tools become available; no Rayleigh proxy is invented |
| 602 | coated Sunny submerges at route progress 0.00 |
| 603 | pressure/light zone and progress 0.18 |
| 604 | downward plume, Kraken hazard, and progress 0.38 |
| 605 | Underworld of the Sea creatures and progress 0.58 |
| 606 | deep volcanic region and progress 0.78 |
| 607 | trench/distant-gate approach and progress 1.00 |
| 608 | all temporary descent nodes close; `fish-man-island` owns the full destination |

Named clips:

- `fishman_descent_route_state` — 5.042 s, chapter-sampled
- `fishman_current_cycle` — 4.833 s, ambient only during chapters 603–607
- `fishman_volcanic_cycle` — 5.042 s, ambient only during chapters 606–607

The cross-section explains vertical sequence and depth. It does not claim exact
horizontal bearings, distances, trench width, or Red Line wall proportions.

## Global Red Line map change

`components/world-geometry.ts` still uses the exact 0/180 meridian as the
topological Red Line great circle. The visible continent fill now has a
deterministic irregular centre offset and varying width, with the equatorial
crossings held exactly at longitude 0/180. This makes it read as rock rather
than a straight UI stripe without pretending the app has a canon coastline
survey.

## Accuracy and source policy

The One Piece API remains useful for entity identity and debut metadata, but it
does not supply the dynamic island geography needed here. Chapter timing and
place mechanics are recorded in:

- `research/dynamic-geography-evidence-2026-07-19.json`
- `contracts/water-7-sea-train-network.visual.json`
- `contracts/mary-geoise-red-line.visual.json`
- `contracts/fish-man-red-line-descent.visual.json`

The evidence ledger contains 15 chapter/place claims. The contracts distinguish
verified geometry, temporary verified state windows, unresolved components,
and stylized interpolation. Runtime metadata carries the same flood, transport,
coastline, destination, anchor, and route policies into
`data/generated/runtime_assets.json` for inspectors and audits.

## How to inspect in Journey

Run the app with `NEXT_PUBLIC_RUNTIME_3D_ASSETS=1`, open the chapter, expand
**Explore 3D islands**, and choose **View** for the corresponding island.

- `http://localhost:3000/?ch=363` — Aqua Laguna begins over Water 7
- `http://localhost:3000/?ch=367` — peak authored storm/pursuit state
- `http://localhost:3000/?ch=375` — Enies terminus, Day Station, trains, waterfall
- `http://localhost:3000/?ch=904` — Mary Geoise exterior only; no Bondola
- `http://localhost:3000/?ch=905` — Red Port and Bondola ascent
- `http://localhost:3000/?ch=602` — initial coated-Sunny dive
- `http://localhost:3000/?ch=604` — plume and Kraken route hazard
- `http://localhost:3000/?ch=606` — deep volcanic region
- `http://localhost:3000/?ch=607` — trench and destination approach
- `http://localhost:3000/?ch=608` — descent state closes; complete Fish-Man Island opens

Live browser verification passed for chapters 363, 375, 607, and 905. All
three models rendered in the actual Journey close-detail view with zero browser
warnings or errors.

## Registry and rebuild

The signed runtime registry now contains 22 total assets: 3 transitions and 19
runtime scenes. The 3D directory exposes 20 navigable place/system rows, with
the visible count changing by reader chapter.

```sh
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background --python blender-assets/scripts/build_dynamic_geography_systems.py

# Export each source with --animations (required; a static export drops the clips).
/Users/shawnos.ai/Applications/Blender-4.5.3.app/Contents/MacOS/Blender \
  --background blender-assets/source/water-7-sea-train-network.blend \
  --python blender-assets/scripts/export_runtime_glb.py -- \
  --id water-7-sea-train-network \
  --out blender-assets/runtime/water-7-sea-train-network.glb \
  --metadata blender-assets/runtime/water-7-sea-train-network.model.json \
  --animations

python3 blender-assets/scripts/register_dynamic_geography_expansion.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 scripts/sync_runtime_assets.py
node scripts/audit_dynamic_geography.mjs
npm run build
```

Current verification result:

- 22 GLBs/fallbacks verified
- 22 runtime assets copied
- 0 refused
- 0 gate contradictions
- production build passed
- scoped lint for the changed TypeScript/JavaScript passed

The repository-wide `npm run lint` is not currently a clean signal: the ESLint
config scans generated `.next` output inside `.claude/worktrees` and
`.next-codex-w1`, then also reaches pre-existing `OrbitControls.tsx` and
`SearchPalette.tsx` hook errors. This pass did not modify those unrelated files.

## Best next art pass

The contracts and runtime motion are now the stable spine. The next upgrade
should be visual fidelity, not new timing logic:

1. sculpt Water 7 facade/canal kits and add water spray/foam particles;
2. replace the abstract Enies court towers with a stronger courthouse/bridge
   silhouette while preserving the proven waterfall-void topology;
3. add LOD0 cliff erosion, vegetation, and architectural detail to the Red Line;
4. replace the descent's proxy Sunny/Kraken/creatures with reusable authored
   hero meshes while keeping the same component ids and chapter windows;
5. add a dedicated undersea camera rail so the Journey can follow the Sunny
   through the vertical cross-section instead of only orbiting the whole model.
