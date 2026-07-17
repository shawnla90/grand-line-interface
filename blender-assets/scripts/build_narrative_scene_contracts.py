#!/usr/bin/env python3
"""Build chapter-aware place, event, and transit contracts for Blender.

The app repository is read-only. This script joins its generated place records,
raw API coverage, and atlas anchors with a small, cited visual-topology overlay.
Atlas coordinates are retained as scene entry anchors only; relationship graphs
drive every local sketch and Blender blockout.
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
OVERRIDES = ROOT / "research/narrative-scene-overrides.json"
SCHEMA = ROOT / "contracts/narrative-scene.schema.json"
OUT = ROOT / "contracts"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def evidence(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": sha(path),
        "ownership": "atlas_read_only" if path.is_relative_to(APP) else "asset_workspace",
    }


def atlas_anchor(slug: str, coordinates: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    item = coordinates.get(slug)
    if not item:
        return None
    return {
        "lng": item["lng"],
        "lat": item["lat"],
        "confidence": item.get("canon_confidence"),
        "source_ref": item.get("source_ref"),
        "usage": "scene_entry_anchor_only",
        "warning": "Never infer local bearings, distances, or topology from this deterministic atlas point.",
    }


def generated_component(
    spec: dict[str, Any],
    records: dict[str, dict[str, Any]],
    coordinates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    slug = spec["slug"]
    if slug not in records:
        raise RuntimeError(f"Missing generated component: {slug}")
    return {
        **compact_record(records[slug]),
        "id": slug,
        "role": spec["role"],
        "record_origin": "generated_wiki_record",
        "atlas_anchor": atlas_anchor(slug, coordinates),
    }


def manual_component(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": spec["id"],
        "slug": None,
        "name": spec["name"],
        "role": spec["role"],
        "debut_chapter": spec.get("reveal_chapter"),
        "canon_status": "manga_or_official_summary",
        "canon_confidence": "cited_summary",
        "source_ref": spec["source_url"],
        "record_origin": "cited_manual_topology_node",
        "atlas_anchor": None,
    }


def build_contract(
    spec: dict[str, Any],
    records: dict[str, dict[str, Any]],
    raw_api: list[dict[str, Any]],
    coordinates: dict[str, dict[str, Any]],
    coordinate_policy: dict[str, Any],
) -> dict[str, Any]:
    anchor_slug = spec["anchor_slug"]
    if anchor_slug not in records:
        raise RuntimeError(f"Missing anchor record: {anchor_slug}")
    anchor = {
        **compact_record(records[anchor_slug]),
        "id": anchor_slug,
        "record_origin": "generated_wiki_record",
        "atlas_anchor": atlas_anchor(anchor_slug, coordinates),
    }
    components = [
        generated_component(item, records, coordinates)
        for item in spec["components"]
    ] + [manual_component(item) for item in spec.get("manual_components", [])]
    component_names = {item["name"] for item in components}
    raw_names = {item["name"] for item in raw_api}

    contract = {
        "schema_version": 2,
        "id": spec["id"],
        "label": spec["label"],
        "entity_type": spec["entity_type"],
        "priority": spec["priority"],
        "contract_status": "ready_for_system_sketch",
        "identity": {
            "anchor": anchor,
            "components": components,
        },
        "relationships": spec["relationships"],
        "topology": {
            "summary": spec["topology_summary"],
            "sources": spec["topology_sources"],
            "exact_distances": "unknown",
            "exact_bearings": "partially_known_or_unknown",
            "layout_mode": "relationship_graph_not_atlas_jitter",
        },
        "chapter_logic": {
            "base_reveal_chapter": records[anchor_slug].get("debut_chapter"),
            "temporal_variants": spec["temporal_variants"],
            "event_scenes": spec["event_scenes"],
            "default_rule": "Render the latest verified state whose reveal chapter is less than or equal to the reader chapter.",
            "unknown_gate_rule": "Do not render a chapter_to_verify state until its exact gate is confirmed.",
        },
        "coordinate_policy": coordinate_policy,
        "api_coverage": {
            "raw_api_matches": sorted(component_names & raw_names),
            "raw_api_missing_or_nested": sorted(component_names - raw_names),
            "generated_component_count": sum(item["record_origin"] == "generated_wiki_record" for item in components),
            "manual_topology_node_count": sum(item["record_origin"] == "cited_manual_topology_node" for item in components),
        },
        "visual_program": {
            "master_scene": "One Blender master scene with addressable collections for topology nodes, chapter states, event actors, atmosphere, and runtime LODs.",
            "must_show": spec["must_show"],
            "must_not_show": spec["must_not_show"],
            "collection_pattern": [
                "00_TOPOLOGY",
                "10_LANDMARKS",
                "20_EVENT_STATES",
                "30_ATMOSPHERE_FX",
                "40_RUNTIME_LOD",
            ],
            "runtime_handoff": "Export static environment and event-state collections separately; MapLibre controls anchor, visibility, route progress, and chapter gate.",
        },
        "unresolved": spec["unresolved"],
        "evidence": [
            evidence(GENERATED),
            evidence(RAW_API),
            evidence(COORDS),
            evidence(OVERRIDES),
            evidence(SCHEMA),
        ],
    }
    if "route_network" in spec:
        contract["route_network"] = spec["route_network"]
    return contract


def main() -> int:
    generated = read(GENERATED)
    records = {item["slug"]: item for item in generated}
    raw_api = read(RAW_API)
    coordinates = {item["slug"]: item for item in read(COORDS)["islands"]}
    overrides = read(OVERRIDES)
    OUT.mkdir(parents=True, exist_ok=True)

    contracts = []
    for spec in overrides["systems"]:
        contract = build_contract(
            spec,
            records,
            raw_api,
            coordinates,
            overrides["coordinate_policy"],
        )
        path = OUT / f"{contract['id']}.visual.json"
        path.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        contracts.append(contract)
        print(f"wrote {path}")

    index = {
        "schema_version": 2,
        "generator": "scripts/build_narrative_scene_contracts.py",
        "contract_count": len(contracts),
        "contracts": [
            {
                "id": contract["id"],
                "label": contract["label"],
                "entity_type": contract["entity_type"],
                "priority": contract["priority"],
                "state": contract["contract_status"],
                "path": f"contracts/{contract['id']}.visual.json",
            }
            for contract in contracts
        ],
    }
    index_path = OUT / "narrative-scene-index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
