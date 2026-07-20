# Geography expansion overnight handoff — 2026-07-19

This batch turns Punk Hazard and the Totto Land food islands into chapter-aware
map geography. They are not chapter illustrations laid over the map: they are
GLBs placed at atlas anchors, scaled against the existing island silhouettes,
node-gated by chapter, and loaded/unloaded by the shared MapLibre runtime.

The working tree was already shared and dirty. This pass did not commit, push,
delete, or overwrite unrelated work.

> Follow-on update: Water 7/Aqua Laguna/Sea Trains, Mary Geoise/Red Port/Bondola,
> the irregular Red Line continent, and the Sabaody-to-Fish-Man descent are now
> integrated. See `DYNAMIC_GEOGRAPHY_HANDOFF.md`. The signed registry now has 22
> assets, the directory has 20 navigable systems, and sync reports zero refused
> assets and zero gate contradictions.

## What landed

### Punk Hazard fire-and-ice geographic system

- Runtime id: `punk-hazard-geographic-system`
- 195 Blender objects, 28,868 triangles, 17 materials
- GLB: 1,342,704 bytes
- SHA-256: `9cde554e6a085753b4b29eb4a8798eaa08eefbe830d481dcbef73837ca5644a4`
- Source, GLB, fallback render, sidecar, contract, evidence ledger, standalone
  manifest, build script, verifier, hero preview, and contact sheet are present.
- Model bounds are signed into the sidecar and runtime registry. This matters:
  the generic runtime refuses a visual-fit model with no bounds.
- The five-second `punk_hazard_environment_cycle` keeps the climate boundary,
  lava proxies, steam, ice wind, and water alive after the reader enters the
  island.
- The 3.958-second `punk_hazard_duel_memory_fx` exists only during chapter 658.
  It is an abstract environmental reconstruction, not an invented on-page duel
  or character model.

Chapter states:

| Chapter | Runtime state |
|---:|---|
| through 654 | Model absent. |
| 655 | Arrival geography: burning southwest, fiery sea, volcano, melted base. |
| 657 | Cold northeast, crater lake, sea channel, lab, and ambient climate cycle. |
| 658 | Ice river, captured-ships harbor, iceberg choke, industrial system, and one-chapter duel-memory FX. |
| 659 | Compass orientation is safe. |
| 661 | Crater origin explanation is safe. |
| 664 onward | Earlier institute ruins and full verified scene. |

The remembered river belongs here: it runs through Punk Hazard's cold side to
the captured-ships harbor and is obstructed by icebergs. The evidence did not
support inventing a chocolate, juice, or candy river for Totto Land.

### Totto Land food-island hero geography

- Runtime id: `totto-land-food-geography`
- Replaces the former registered `totto-land` model; the runtime never loads
  both systems for the same geography.
- 333 Blender objects, 36,884 triangles, 18 materials
- GLB: 2,728,248 bytes
- SHA-256: `28f50f92090b8cf817e81ae857ba25e96d47a4b4baa3f76bf1df113cdeefd0bb`
- The 5.042-second `totto_land_food_route_cycle` supplies living open-sea route
  motion without changing canon geography.

Chapter states:

| Chapter | Runtime state |
|---:|---|
| 651 | Whole Cake Island and the Chateau silhouette. |
| 827 | Cacao Island, entirely chocolate, plus the neutral edible settlement and Pudding's home. |
| 828 | Biscuits Island. |
| 829 | Sweet City and the chapter-only open-sea foam route. |
| 831 onward | Seducing Woods / Forest of Temptation geography. |

Unsupported specificity was deliberately withheld. The research supports Cacao
Island being chocolate, but not an official structured place label called
"Chocolate Town" and not a Totto Land chocolate/juice/candy river. The build
uses neutral descriptive component names where the canon does not provide one.

### Fish-Man Island gate repair

The already-shipped GLB now has a visual contract and opens at chapter 608, when
the island is reached and shown. It no longer leaks complete Fish-Man Island
geography hundreds of chapters early from an upstream debut artifact.

### Persistent environmental animation runtime

`components/runtime-models.ts` now accepts `ambient_tracks`. These differ from:

- chapter-entry clips, which replay a finite action at an exact chapter; and
- geographic tracks, which permanently move geography according to chapter.

Ambient tracks keep water, steam, lava, wind, weather, or vegetation moving
while their chapter window is open. Reduced-motion mode freezes them at their
authored first frame. `WorldMap` preserves the ambient wall-clock across chapter
scrubs instead of restarting the weather every chapter.

### The live integration defect that was fixed

The island directory used to zoom and tilt for a 3D dive while preserving globe
projection. Mercator-only close-detail models therefore stayed gated off and the
reader landed on a flat silhouette. A directory dive now switches to Mercator,
then flies to zoom 6.4 / pitch 45. This was verified in the running app with the
browser, not inferred from the manifest.

## How to inspect it in Journey

Run the app with `NEXT_PUBLIC_RUNTIME_3D_ASSETS=1`, open the listed chapter,
open **Explore 3D islands**, then select **View** for the matching island.

- `http://localhost:3000/?ch=655` — Punk Hazard arrival-only state
- `http://localhost:3000/?ch=657` — complete hot/cold split and ambient climate
- `http://localhost:3000/?ch=658` — historical cause memory and harbor system
- `http://localhost:3000/?ch=664` — full Punk Hazard geography
- `http://localhost:3000/?ch=827` — Cacao / Whole Cake state
- `http://localhost:3000/?ch=829` — Sweet City and one-chapter route state
- `http://localhost:3000/?ch=831` — complete current Totto Land hero set
- `http://localhost:3000/?ch=607` — Fish-Man Island remains locked
- `http://localhost:3000/?ch=608` — Fish-Man Island becomes reachable

The 3D directory now reports 20 wired place/system rows; the visible number is
chapter-gated. The Fish-Man descent is a new transition row and the complete
Fish-Man Island remains separately gated at chapter 608.

## Map coverage after this batch

The read-only audit snapshot found 19 of 31 core-story places complete across
contract, GLB, and runtime, plus two broken stage chains. This pass closed both
chains: Punk Hazard is registered and copied, and Fish-Man Island has a contract
and corrected gate. Current core-stage coverage is therefore **21 / 31**.

The ten remaining core gaps are:

1. Foosha Village
2. Shells Town
3. Orange Town
4. Syrup Village
5. Baratie, treated as a floating vessel/place rather than a fabricated island
6. Little Garden
7. Drum Island
8. Jaya
9. Long Ring Long Land
10. Thriller Bark, preserved as a mobile island-ship

The full canon/API inventory contains 485 unique location slugs, but includes
anime, non-canon, guessed, minor, and duplicate rows. It is an inventory
boundary, not a sensible immediate production denominator.

## Ready for the next Blender workers

Five Paradise visual contracts are ready and verified:

- `contracts/paradise-gap-batch-a-little-garden.visual.json`
- `contracts/paradise-gap-batch-a-drum-island.visual.json`
- `contracts/paradise-gap-batch-a-jaya-upper-yard.visual.json`
- `contracts/paradise-gap-batch-a-long-ring-long-land.visual.json`
- `contracts/paradise-gap-batch-a-thriller-bark.visual.json`

Together they define 51 chapter-gated components backed by 20 evidence claims.
Important boundaries are already encoded: Little Garden first visually opens at
115; Thriller Bark's complete mobile ship/island system opens at 443; Jaya
references the existing Upper Yard asset rather than duplicating it; the Long
Ring tide is explanatory, not an invented per-chapter flood; and unsupported
post-timeskip or damage states remain hidden.

Recommended next parallel build wave:

1. Little Garden + Dorry/Brogy-scale landmark geography
2. Drum Island's drum-rock skyline and settlement layers
3. Jaya / Mock Town / Knock-Up launch coastline
4. Long Ring Long Land's elongated islands and tide state
5. Thriller Bark as a mobile world-root with mast, wall, manor, forest, and fog

After that, close the five opening East Blue places as one route-continuity
batch. This produces a continuous voyage before adding lower-value incidental
API locations.

## Rebuild and verification

```sh
python3 blender-assets/scripts/register_geography_expansion.py
python3 blender-assets/scripts/punk-hazard-verify.py
python3 blender-assets/scripts/verify_totto_land_food_geography.py
python3 blender-assets/research/paradise-gap-batch-a-verify.py
python3 blender-assets/scripts/verify_runtime_3d.py
python3 scripts/sync_runtime_assets.py
node scripts/audit_geography_expansion.mjs
node scripts/audit_runtime_ambient_tracks.mjs
npm run build
```

The follow-on dynamic-geography pass repaired the older Water 7 and Mary Geoise
manifest-versus-node contradictions. Sync now reports zero contradictions;
the New World-side Red Port remains explicitly unresolved and fail-closed.

## Primary evidence artifacts

- `research/runtime-map-gap-audit-2026-07-19.md` — pre-integration map audit
- `research/punk-hazard-geography-evidence.json`
- `research/totto-land-food-geography.evidence.json`
- `research/paradise-gap-batch-a-evidence.json`
- `proofs/geography-expansion-2026-07-19.json`
