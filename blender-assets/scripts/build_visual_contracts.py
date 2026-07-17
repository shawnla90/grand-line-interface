#!/usr/bin/env python3
"""Join atlas/API records with curated topology into Blender visual contracts.

The atlas repository is strictly read-only. Generated contracts are written to
the isolated Blender asset workspace and contain no guessed geographic layout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP = Path("/Users/shawnos.ai/dead-reckoning")
GENERATED = APP / "data/generated/islands.json"
RAW_API = APP / "data/raw/locates.json"
COORDS = APP / "canon/islands.coords.json"
OVERRIDES = ROOT / "research/visual-topology-overrides.json"
OUT = ROOT / "contracts"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_evidence(paths: list[Path]) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path),
            "sha256": digest(path),
            "ownership": "atlas_read_only" if path.is_relative_to(APP) else "asset_workspace",
        }
        for path in paths
    ]


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "slug",
        "name",
        "japanese",
        "romaji",
        "region",
        "sea",
        "island_type",
        "debut_chapter",
        "debut_episode",
        "canon_status",
        "canon_confidence",
        "affiliation",
        "wiki_url",
        "source_ref",
    )
    return {key: record.get(key) for key in fields}


THEME_WORDS = {
    "100-island": "juice",
    "black-island": "tea",
    "futoru-island": "tasting",
    "kibo-island": "yeast",
    "kimi-island": "eggs",
    "kinko-island": "finance",
    "komugi-island": "flour",
    "loving-island": "love",
    "milenge-island": "meringue",
    "noko-island": "whipped-cream",
    "poripori-island": "beans",
    "sanshoku-island": "mix",
    "tanega-island": "seeds",
    "unique-island": "design",
    "yakigashi-island": "browned-food",
}


def theme_hint(record: dict[str, Any]) -> dict[str, Any]:
    slug = record["slug"]
    name = record["name"].lower().replace(" island", "")
    theme = THEME_WORDS.get(slug, name.replace(" ", "-"))
    return {
        "theme": theme,
        "confidence": "directional_only",
        "rule": "Use this to choose a research lane, not to invent literal topography.",
    }


def coords_index() -> dict[str, dict[str, Any]]:
    return {item["slug"]: item for item in read(COORDS)["islands"]}


def atlas_anchor(slug: str, coords: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item = coords[slug]
    return {
        "lng": item["lng"],
        "lat": item["lat"],
        "confidence": item.get("canon_confidence"),
        "source_ref": item.get("source_ref"),
        "usage": "atlas_anchor_only",
        "warning": "Deterministic atlas placement; never use it as evidence of relative canon topology.",
    }


def build_totto(
    islands: dict[str, dict[str, Any]],
    raw_api: list[dict[str, Any]],
    coords: dict[str, dict[str, Any]],
    override: dict[str, Any],
) -> dict[str, Any]:
    selector = override["subsidiary_selector"]
    members = [
        record
        for record in islands.values()
        if record.get(selector["field"]) == selector["equals"]
    ]
    member_slugs = {record["slug"] for record in members}
    for slug in override["subsidiary_extras"]:
        if slug not in member_slugs:
            members.append(islands[slug])
            member_slugs.add(slug)
    members.sort(key=lambda record: record["slug"])

    expected = override["expected_subsidiary_count"]
    if len(members) != expected:
        raise RuntimeError(f"Totto Land coverage drift: expected {expected}, found {len(members)}")

    placement = override["placement_hints"]
    component_records = []
    for record in members:
        component_records.append(
            {
                **compact_record(record),
                "role": "subsidiary_island",
                "theme_hint": theme_hint(record),
                "relative_placement": placement.get(
                    record["slug"],
                    {"direction": None, "ring": None, "medium": "unresolved"},
                ),
                "atlas_anchor": atlas_anchor(record["slug"], coords),
            }
        )

    central = islands[override["central_slug"]]
    chateau = islands.get("whole-cake-chateau")
    raw_names = {item["name"] for item in raw_api}
    return {
        "schema_version": 1,
        "id": "totto-land",
        "label": "Totto Land archipelago",
        "entity_type": override["entity_type"],
        "contract_status": "ready_for_component_sketches",
        "identity": {
            "central": {
                **compact_record(central),
                "role": "central_main_island",
                "theme_hint": {"theme": "cake", "confidence": "canon_summary"},
                "atlas_anchor": atlas_anchor(central["slug"], coords),
            },
            "nested_landmark": compact_record(chateau) if chateau else None,
            "subsidiary_count": len(component_records),
            "subsidiaries": component_records,
        },
        "topology": {
            "rule": override["topology"],
            "layout_mode": "semantic_concentric_archipelago",
            "exact_angles": "partially_known",
            "exact_distances": "unknown",
            "source": override["topology_source"],
            "manga_reference": override["manga_reference"],
        },
        "api_coverage": {
            "raw_api_has_whole_cake_island": "Whole Cake Island" in raw_names,
            "raw_api_component_count": sum(record["name"] in raw_names for record in members),
            "generated_wiki_component_count": len(component_records),
            "classification_repairs": [
                {
                    "slug": slug,
                    "problem": "upstream region is New World instead of Totto Land",
                    "action": "included through cited topology override",
                }
                for slug in override["subsidiary_extras"]
            ],
        },
        "visual_program": {
            "master_scene": "One Blender collection per island, instanced into a Totto Land system scene.",
            "sketch_order": [
                "macro topology: central Whole Cake Island plus concentric subsidiary rings",
                "individual silhouette families: no repeated generic island disc",
                "food/material massing derived from researched component references",
                "shared sea, cotton-candy weather, juice-water boundaries, and security outposts",
                "lighting and final runtime LODs",
            ],
            "must_show": [
                "Whole Cake Island is the central hub, not the whole territory",
                "34 independently addressable subsidiary islands",
                "distinct silhouette and material language per researched food/theme family",
            ],
            "must_not_show": [
                "one giant cake island standing in for Totto Land",
                "34 evenly cloned cake meshes",
                "relative placement copied from current deterministic atlas jitter",
            ],
        },
        "unresolved": [
            "Exact ring and bearing for subsidiaries without a cited placement hint.",
            "Exact silhouette/topography for every component; theme names alone are insufficient.",
            "How the app will replace independent jittered points with a coherent local cluster.",
        ],
        "evidence": source_evidence([GENERATED, RAW_API, COORDS, OVERRIDES]),
    }


def build_tarai(
    islands: dict[str, dict[str, Any]],
    raw_api: list[dict[str, Any]],
    coords: dict[str, dict[str, Any]],
    override: dict[str, Any],
) -> dict[str, Any]:
    roles = {
        "enies-lobby": "judicial_facility",
        "impel-down": "underwater_prison",
        "marineford": "former_marine_headquarters",
        "gates-of-justice": "distributed_access_infrastructure",
        "tarai-current": "connecting_water_system",
    }
    ordered = override["facility_slugs"] + override["infrastructure_slugs"]
    raw_names = {item["name"] for item in raw_api}
    components = [
        {
            **compact_record(islands[slug]),
            "role": roles[slug],
            "atlas_anchor": atlas_anchor(slug, coords),
        }
        for slug in ordered
    ]
    return {
        "schema_version": 1,
        "id": "world-government-tarai-system",
        "label": "World Government Tarai Current system",
        "entity_type": override["entity_type"],
        "contract_status": "ready_for_system_sketch",
        "identity": {
            "components": components,
            "relationships": override["relationships"],
        },
        "topology": {
            "rule": override["topology"],
            "layout_mode": "relational_triangle",
            "exact_angles": "unknown",
            "exact_distances": "unknown",
            "source": override["topology_source"],
            "manga_references": override["manga_references"],
        },
        "temporal_logic": {
            "variant": "pre_timeskip_active_system",
            "active_through_chapter": 597,
            "state_change_chapter": 598,
            "note": override["temporal_note"],
            "post_timeskip_rule": "Keep old Marineford as a historical/former node; do not connect New Marineford to this triangle without new evidence.",
        },
        "api_coverage": {
            "raw_api_matches": sorted(record["name"] for record in components if record["name"] in raw_names),
            "raw_api_missing": sorted(record["name"] for record in components if record["name"] not in raw_names),
            "generated_wiki_component_count": len(components),
        },
        "visual_program": {
            "master_scene": "One relational system scene with separate collections for facilities, gates, current, atmosphere, and chapter-state variants.",
            "sketch_order": [
                "triangle/current diagram using relationships, not atlas jitter",
                "distinct facility silhouettes",
                "surface-to-depth cross-section for Impel Down",
                "distributed Gate of Justice structures and directed water flow",
                "pre/post-timeskip visibility variants",
            ],
            "must_show": [
                "three different facilities surrounding one current system",
                "Impel Down extending underwater rather than reading as an ordinary island",
                "Gates of Justice as access infrastructure, not a standalone island",
                "Tarai Current as connective motion and topology",
            ],
            "must_not_show": [
                "five unrelated island plates",
                "New Marineford substituted into the historical triangle",
                "straight connections between independently jittered atlas coordinates presented as canon",
            ],
        },
        "unresolved": [
            "Exact cartographic bearings and scale between the three facilities.",
            "Whether the runtime representation is a geographically expanded inset or a chapter-triggered local system scene.",
            "Post-timeskip visual state of the old Tarai system beyond Marineford's headquarters move.",
        ],
        "evidence": source_evidence([GENERATED, RAW_API, COORDS, OVERRIDES]),
    }


def main() -> int:
    generated = read(GENERATED)
    islands = {record["slug"]: record for record in generated}
    raw_api = read(RAW_API)
    coords = coords_index()
    systems = read(OVERRIDES)["systems"]
    OUT.mkdir(parents=True, exist_ok=True)

    contracts = {
        "totto-land.visual.json": build_totto(
            islands, raw_api, coords, systems["totto-land"]
        ),
        "world-government-tarai-system.visual.json": build_tarai(
            islands, raw_api, coords, systems["world-government-tarai-system"]
        ),
    }
    for filename, contract in contracts.items():
        path = OUT / filename
        path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
