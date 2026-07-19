# Runtime map gap audit — 2026-07-19

Snapshot: **2026-07-19 02:09 EDT**, read-only audit of the dirty working tree. This report does not treat the checkout as a clean release. Two standalone packages appeared during the audit and are included at their observed stages: `punk-hazard-geographic-system` has a contract, source, GLB, fallback, previews, sidecar, and standalone manifest but no main-manifest/public/generated-registry integration; `totto-land-food-geography` has a local build package but no main-manifest/public/generated-registry entry.

## Scope and stage definitions

The canonical inventory is `data/canon.json` (`islands`, `locations`, `arcs`, and `voyage.waypoints`), with `canon/islands.extra.json` supplying the hand-authored Thriller Bark exception. The Blender/runtime stages checked were:

1. **Contract (C):** a canonical place slug/id is declared by a `blender-assets/contracts/*.visual.json` contract, including a component of a larger geographic system.
2. **GLB (G):** a corresponding system is in `blender-assets/manifests/runtime-3d.json` and its `blender-assets/runtime/*.glb` binary exists.
3. **Registry/runtime (R):** the asset is copied into `data/generated/runtime_assets.json` and has a runtime path. A component inside a registered system counts as covered, but not as an independently anchored/fly-to model.

This is a **map-geography** audit. The 2.5D story-simulation packs do not count as runtime-map GLB coverage.

## Headline

- Canon/data exposes **414 island rows** and **128 location rows**, or **485 unique slugs** after the 55-slug overlap is removed. The island corpus includes 257 manga rows, 33 anime rows, 123 non-canon rows, and 1 unknown row; all 128 API location rows are marked `canon_confidence: derived`. The raw 485-row denominator is therefore an inventory boundary, not a sensible immediate production target.
- There are now **18 visual-contract files**. Exact canonical slug/id matching finds **96 / 485** canon/data places declared somewhere in those contracts.
- `runtime-3d.json` contains **20 models**. The generated runtime registry contains **20 copied assets, 0 refused**, and exact component/id matching finds **94 / 485** canon/data places. Exact matching slightly understates semantic coverage: for example, the Reverse Mountain GLB tags `reverse-mountain-massif` while the contract and canonical place use `reverse-mountain`.
- The top-level asset runtime directory currently has **22 GLBs**: the 20 main-manifest models plus standalone, unintegrated `punk-hazard-geographic-system.glb` and `totto-land-food-geography.glb` binaries.
- The Totto Land candidate has a source blend, model sidecar, renders, and contact sheet, but no `runtime-3d.json` row, public GLB, generated registry entry, or runtime-code reference at snapshot time. It duplicates already-covered Totto Land geography until an ownership decision says whether it replaces or supplements `totto-land`.
- **17 of the 18 visual contracts** are linked from `runtime-3d.json`; every one of those 17 has an on-disk GLB and a generated registry entry. There is no contract-linked manifest model whose GLB is missing.
- The one contract-linked stage-chain exception is **Punk Hazard**: its contract explicitly says `standalone_runtime_package_not_registered`. Its GLB/fallback package now exists locally with `manifests/punk-hazard-runtime.json`, but the id is absent from `runtime-3d.json`, the public tree, generated registry, and runtime code.
- Three manifest models have no visual-contract link: `skypiea-knock-up-stream`, `wano-waterfall-ascent`, and `fish-man-island`. Skypiea has a bespoke GLB path in `WorldMap.tsx`; Wano currently integrates the raster only and deliberately withholds GLB motion; Fish-Man Island is loaded by the generic registry but lacks the visual contract that should own its chapter/topology policy.

## Prioritized core-story coverage matrix

The matrix uses the 26 authored Straw Hat `voyage.waypoints`, plus five arc settings that the voyage list does not independently add: Long Ring Long Land, Amazon Lily, Impel Down, Marineford, and Mary Geoise/Levely. This produces a 31-place core story set rather than prioritizing hundreds of incidental, anime-only, non-canon, or API-duplicate rows.

Legend: `yes` = stage present; `no` = missing; `component` = present inside a registered composite system; `partial` = a runtime artifact exists but the stage/policy is incomplete.

| Pri | Canonical place | Canon story evidence | C | G | R | Runtime system / primary gap |
|---|---|---:|:---:|:---:|:---:|---|
| P0 | Foosha Village | voyage ch. 1 | no | no | no | Missing visual contract; therefore no map GLB or registry entry. |
| P0 | Shells Town | voyage ch. 3 | no | no | no | Missing visual contract; exact canonical slug is `shells-town`. |
| P0 | Orange Town | voyage ch. 9 | no | no | no | Missing visual contract. |
| P0 | Syrup Village | voyage ch. 23 | no | no | no | Missing visual contract. |
| P0 | Baratie | voyage ch. 43 | no | no | no | Authored waypoint with no island slug because it is a floating restaurant; needs an explicit vessel/place contract rather than an invented island row. |
| — | Conomi Islands / Arlong Park | voyage ch. 69 | yes | yes | component | `conomi-arlong-park`; one registered system anchor. |
| — | Loguetown | voyage ch. 96 | yes | yes | component | `loguetown-roger-execution`. |
| — | Reverse Mountain | voyage ch. 101 | yes | yes | component | `reverse-mountain-twin-cape-voyage`; runtime node uses `reverse-mountain-massif`. |
| — | Whisky Peak | voyage ch. 105 | yes | yes | component | `cactus-island-whisky-peak`. |
| P1 | Little Garden | voyage ch. 115 | no | no | no | Missing visual contract. |
| P1 | Drum Island | voyage ch. 133 | no | no | no | Missing visual contract. |
| — | Arabasta Kingdom | voyage ch. 157 | yes | yes | component | `arabasta-kingdom`. |
| P1 | Jaya | voyage ch. 223 | no | no | no | Missing visual contract; Skypiea coverage does not cover its Blue Sea launch geography. |
| — | Skypiea | voyage ch. 237 | yes | yes | component | `skypiea-sky-system`; the separate Knock-Up Stream GLB uses a bespoke runtime path. |
| P1 | Long Ring Long Land | arc ch. 303–321 | no | no | no | Canon arc-setting gap omitted from the authored voyage waypoints as well as 3D. |
| — | Water 7 | voyage ch. 323 | yes | yes | component | `water-7-sea-train-network`. |
| — | Enies Lobby | voyage ch. 375 | yes | yes | component | Present in both Water 7 network and Tarai-system contracts; no independent model anchor. |
| P1 | Thriller Bark | voyage ch. 444 | no | no | no | Hand-authored manga island/ship exception exists in canon; no visual contract or map GLB. |
| — | Sabaody Archipelago | voyage ch. 490 | yes | yes | component | `sabaody-grove-network`. |
| — | Amazon Lily | arc ch. 514–524 | yes | yes | component | `amazon-lily`. |
| — | Impel Down | arc ch. 525–549 | yes | yes | component | `world-government-tarai-system`; local-theatre component, not its own map anchor. |
| — | Marineford | arc ch. 550–580 | yes | yes | component | `world-government-tarai-system`; local-theatre component, not its own map anchor. |
| P0 | Fish-Man Island | voyage ch. 608 | no | yes | yes | **Contract missing despite shipped GLB.** Registry opens the full model at ch. 68 while the authored voyage says ch. 608 and the same asset records dive beats at 602–653. |
| P0 | Punk Hazard | voyage ch. 655 | yes | yes | no | **Standalone GLB package exists; main manifest entry, public copy, generated registry entry, and runtime loader path are missing.** |
| — | Dressrosa | voyage ch. 700 | yes | yes | component | `dressrosa-green-bit`. |
| — | Zou | voyage ch. 802 | yes | yes | component | `zou-zunesha`. |
| — | Whole Cake Island | voyage ch. 827 | yes | yes | component | `totto-land`. |
| — | Mary Geoise / Levely | Levely arc ch. 903–908 | yes | yes | component | `mary-geoise-red-line`; unverified/contradictory later nodes remain default-hidden. |
| — | Wano Country | voyage ch. 909 | yes | yes | component | `wano-onigashima-country-system`. Separate waterfall **raster** is wired at 909; its GLB is not wired because climb beats remain unverified. |
| — | Egghead | voyage ch. 1061 | yes | yes | component | `egghead-future-island-system`. |
| — | Elbaph | voyage ch. 1125 | yes | yes | component | `elbaph-adam-world-system`. |

Core-set totals:

| Measure | Coverage |
|---|---:|
| Contract present | 20 / 31 |
| GLB present | 21 / 31 |
| Registered runtime coverage | 20 / 31 |
| All three stages complete | **19 / 31** |
| Missing all three stages | **10 / 31** |
| Partial stage chain | **2 / 31** (`fish-man-island`, `punk-hazard`) |

The partial chains have opposite defects: Fish-Man Island supplies the GLB/runtime coverage but lacks a contract, while Punk Hazard supplies the contract/GLB package but lacks main-manifest and runtime integration.

## Recommended gap order

### P0 — close broken stage chains before broadening the map

1. **Integrate the completed standalone Punk Hazard package.** It is the most ready missing runtime island: its contract and standalone manifest supply verified chapter gates (655/657/658/659/661/664), GLB/fallback paths, component ids, projection policy, scale policy, build evidence, and previews. Remaining stages are `runtime-3d.json`, public copy, generated registry/runtime loader, and the normal validators.
2. **Give Fish-Man Island a visual contract and reconcile its whole-model gate.** The GLB is already copied and generically loadable, but `base_reveal` and `safe_full_scene` are both 68. `data/canon.json` explicitly calls that upstream debut wrong for route arrival and uses 608; the asset itself records the dive at 602 and deep arrival at 605. This is a policy gap, not an art gap.
3. **Resolve the in-flight Totto Land duplicate before registering it.** `totto-land-food-geography` is a real local GLB package but currently orphaned from runtime ownership. Decide whether it supersedes `totto-land`, becomes a review-only study, or earns a distinct registered role; registering both at the same geography without that decision would create duplicate loading and conflicting chapter/component policy.
4. **Fill the opening East Blue voyage as one deliberate batch:** Foosha Village, Shells Town, Orange Town, Syrup Village, and Baratie. They are five consecutive authored waypoints before the already-covered Conomi system. Baratie needs a vessel/place model contract, not a fabricated island identity.

### P1 — repair the remaining arc-shaped holes

5. **Paradise route batch:** Little Garden, Drum Island, Jaya, Long Ring Long Land, and Thriller Bark. Each is manga geography with an arc/voyage record and no visual contract, GLB, or registry component. Thriller Bark should preserve its canon `island_type: Ship` treatment.
6. **Wano waterfall GLB integration is a gate-verification task, not a missing-Wano task.** `components/wano.ts` intentionally shows the raster from ch. 909 without animating an invented climb. Once exact climb/crest beats are verified, the existing GLB can receive a deliberate runtime path; until then, the country is already covered by `wano-onigashima-country-system`.

### P2 — improve registry addressability after geometry coverage

7. Composite contracts provide geometry but only one runtime model anchor/directory entry. Enies Lobby, Impel Down, Marineford, the Totto Land islands, Arabasta cities, and Water 7 rail stops are registered node components, not independently flyable canonical places. If the product needs place-by-place discovery, extend registry metadata with component dive anchors/local-camera targets; do not duplicate GLBs merely to create directory rows.
8. After the 31-place core is continuous, triage the remaining corpus by `canon_status`, chapter/arc participation, and confidence. Do not interpret the 389 contract-unmatched or 391 registry-unmatched exact slugs as equally valuable asset requests: the source set intentionally includes anime, non-canon, guessed, minor-landmark, and duplicated API rows.

## Evidence and reproducibility notes

- Canon inventory and route: `data/canon.json`; Thriller Bark exception: `canon/islands.extra.json`.
- Visual contracts: `blender-assets/contracts/*.visual.json`.
- Signed runtime asset inventory: `blender-assets/manifests/runtime-3d.json`.
- Copied runtime registry: `data/generated/runtime_assets.json`.
- Generic registry gating/skip rules: `components/runtime-models.ts` (`gate_unverified`, no anchor, no chapter, silhouette-fit, projection support).
- Runtime loader: `components/WorldMap.tsx`; the Knock-Up Stream is explicitly skipped by the generic loop because its bespoke module/path owns it.
- Wano partial integration: `components/wano.ts` references only `/art/runtime/wano-waterfall-ascent.png` and documents why unverified climb motion remains withheld.
- Punk Hazard package: `blender-assets/contracts/punk-hazard-geographic-system.visual.json`, `blender-assets/research/punk-hazard-geography-evidence.json`, `blender-assets/manifests/punk-hazard-runtime.json`, `blender-assets/runtime/punk-hazard-geographic-system.glb`, its sidecar/source/fallback/previews, and build/verify scripts existed locally. The exact id did not occur in `runtime-3d.json`, `data/generated/runtime_assets.json`, `public/art/runtime`, or runtime code at snapshot time.
- In-flight Totto Land package: `blender-assets/runtime/totto-land-food-geography.glb`, its `.model.json`, source blend, generator, runtime renders, and contact sheet existed locally; no exact id occurred in `runtime-3d.json`, `data/generated/runtime_assets.json`, `public/art/runtime`, or runtime code at snapshot time.
- No sync/build/validator command was run because some existing check scripts regenerate derived files. All audit commands were read-only (`jq`, `rg`, `find`, `stat`, and `git status`).
