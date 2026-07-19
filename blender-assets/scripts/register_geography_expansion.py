#!/usr/bin/env python3
"""Promote Punk Hazard and the close-detail Totto Land replacement.

This script owns only the shared registry/queue merge. The Blender generators
remain standalone so rerunning either art lane cannot silently publish bytes.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUNK_ID = "punk-hazard-geographic-system"
TOTTO_ID = "totto-land-food-geography"
REPLACED_ID = "totto-land"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> list[int]:
    data = path.read_bytes()[:26]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError(f"Invalid PNG: {path}")
    return list(struct.unpack(">II", data[16:24]))


POLICY = {
    "feature_flag": "NEXT_PUBLIC_RUNTIME_3D_ASSETS",
    "default": "fallback_raster",
    "enable_glb_when": "feature flag on, close zoom, mercator projection, chapter gate open",
    "unload_when_hidden": True,
    "dispose_on_remove": ["geometries", "materials", "textures", "animation_actions"],
    "globe_policy": "transparent fallback; close-detail GLB is Mercator-only",
    "node_gate_policy": "read component_id, reveal_chapter, gate_confidence, default_hidden, and verified state windows from glTF extras",
}


def artifact_fields(asset_id: str, contract: str) -> dict:
    glb = ROOT / "runtime" / f"{asset_id}.glb"
    sidecar = read(ROOT / "runtime" / f"{asset_id}.model.json")
    fallback = ROOT / "renders" / "runtime" / f"{asset_id}.png"
    if sha(glb) != sidecar["build"]["glb_sha256"]:
        raise RuntimeError(f"{asset_id}: GLB and sidecar hash disagree")
    return {
        "id": asset_id,
        "maturity": "runtime_blockout_v1",
        "glb": f"runtime/{asset_id}.glb",
        "fallback_raster": f"renders/runtime/{asset_id}.png",
        "fallback": {
            "path": f"renders/runtime/{asset_id}.png",
            "bytes": fallback.stat().st_size,
            "sha256": sha(fallback),
            "pixel_size": png_size(fallback),
            "alpha": True,
        },
        "source_blend": f"source/{asset_id}.blend",
        "contract": contract,
        "runtime_policy": POLICY,
        "stats": sidecar["stats"],
        "build": sidecar["build"],
    }


def punk_model() -> dict:
    package = read(ROOT / "manifests" / "punk-hazard-runtime.json")
    row = artifact_fields(PUNK_ID, "contracts/punk-hazard-geographic-system.visual.json")
    clips = {item["name"]: item for item in package["named_clips"]}
    row.update({
        "label": "Punk Hazard fire-and-ice geographic system",
        "integration": {
            "mode": "maplibre_custom_3d_layer",
            "fallback_mode": "maplibre_image_source_or_inset",
            "anchor": package["integration"]["anchor"],
            "anchor_confidence": "derived",
            "anchor_usage": "atlas_anchor_only",
            "anchor_warning": "Deterministic atlas placement; never use it as canon survey geometry.",
            "chapter_beats": package["chapter_beats"],
            "component_gates": package["component_gates"],
            "named_clips": list(clips),
            "animation_plan": {
                "clock": "chapter_entry_elapsed_ms",
                "reduced_motion": "freeze ambient climate proxies and sample the historical memory FX at its final authored frame",
                "chapter_states": [{
                    "chapter": 658,
                    "duration_ms": 3958,
                    "clips": [{
                        "channel": "punk_hazard_history",
                        "name": "punk_hazard_duel_memory_fx",
                        "start_ms": 0,
                        "duration_ms": 3958,
                        "loop": False,
                    }],
                }],
                "ambient_tracks": [{
                    "channel": "punk_hazard_climate",
                    "name": "punk_hazard_environment_cycle",
                    "active_from_chapter": 657,
                    "duration_ms": 5000,
                    "loop": True,
                }],
            },
            "historical_reconstruction_policy": "Chapter 658 runs abstract magma/ice environmental FX over the already-final island. No characters and no asserted duel choreography.",
            "layout_status": "verified_hot_cold_relationships_with_visual_interpolation_for_dimensions_and_local_bearings",
            "projection_support": ["mercator_closeup"],
            "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
            "withheld_variants": [],
            "route_policy": "Local island theatre; exact coastline, channel, river, harbor, and lab bearings are visual interpolation.",
        },
    })
    return row


TOTTO_ROLES = {
    "totto-land-food-geography": "archipelago_detail_system",
    "whole-cake-island": "central_main_island",
    "whole-cake-chateau": "nested_landmark",
    "cacao-island": "subsidiary_island",
    "cacao-chocolate-settlement": "island_settlement",
    "pudding-home-cacao": "island_landmark",
    "biscuits-island": "subsidiary_island",
    "sweet-city": "island_city",
    "totto-land-sea-route": "verified_state_window_route",
    "seducing-woods": "island_forest",
}


def totto_model() -> dict:
    contract = read(ROOT / "contracts" / "totto-land-food-geography.visual.json")
    gates = []
    for source in contract["chapter_logic"]["component_gates"]:
        gate = {**source, "role": TOTTO_ROLES[source["id"]]}
        if source["id"] != "totto-land-sea-route":
            gate["default_hidden"] = False
        gates.append(gate)
    row = artifact_fields(TOTTO_ID, "contracts/totto-land-food-geography.visual.json")
    row.update({
        "label": "Totto Land food-island hero geography",
        "integration": {
            "mode": "maplibre_custom_3d_layer",
            "fallback_mode": "maplibre_image_source_or_inset",
            "anchor": [72.2778, -2.819],
            "anchor_confidence": "derived",
            "anchor_usage": "atlas_anchor_only",
            "anchor_warning": "The central atlas pin places a close-detail local theatre; it does not measure distances among Totto Land islands.",
            "chapter_beats": {"base_reveal": 651, "safe_full_scene": 831},
            "component_gates": gates,
            "named_clips": ["totto_land_food_route_cycle"],
            "animation_plan": {
                "clock": "chapter_entry_elapsed_ms",
                "reduced_motion": "freeze the ordinary open-sea foam route at its rest pose",
                "chapter_states": [],
                "ambient_tracks": [{
                    "channel": "totto_land_route",
                    "name": "totto_land_food_route_cycle",
                    "active_from_chapter": 829,
                    "active_through_chapter": 829.999,
                    "duration_ms": 5042,
                    "loop": True,
                }],
            },
            "layout_status": "three_close_detail_food_islands_with_verified_identity_and_visually_interpolated_terrain",
            "projection_support": ["mercator_closeup"],
            "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
            "withheld_variants": [],
            "route_policy": "Cacao-to-Whole-Cake foam is a chapter-829 visual interpolation; no juice, chocolate, candy river, or inland canal is asserted.",
            "replacement_policy": "Replaces old totto-land runtime row; never load both at one anchor.",
        },
    })
    return row


def queue_row(asset_id: str, kind: str) -> dict:
    return {
        "id": asset_id,
        "kind": kind,
        "priority": 1,
        "state": "integration_ready",
        "maturity": "runtime_blockout_v1",
        "contract": f"contracts/{asset_id}.visual.json",
        "blend": f"source/{asset_id}.blend",
        "review_render": f"renders/runtime/{asset_id}.png",
        "runtime_glb": f"runtime/{asset_id}.glb",
        "fallback": f"renders/runtime/{asset_id}.png",
        "runtime_manifest": "manifests/runtime-3d.json",
        "next": "close-zoom browser proof and LOD0 sculpt pass",
    }


def main() -> int:
    manifest_path = ROOT / "manifests" / "runtime-3d.json"
    manifest = read(manifest_path)
    incoming = {PUNK_ID: punk_model(), TOTTO_ID: totto_model()}
    removed = {PUNK_ID, TOTTO_ID, REPLACED_ID}
    manifest["models"] = [row for row in manifest["models"] if row["id"] not in removed]
    # Close the audit-discovered Fish-Man spoiler leak as part of the same
    # geography promotion. Chapter 68 is an upstream debut artifact; the full
    # island is entered and shown on the Straw Hats' route at chapter 608.
    fishman = next(row for row in manifest["models"] if row["id"] == "fish-man-island")
    fishman["contract"] = "contracts/fish-man-island.visual.json"
    fishman["integration"]["chapter_beats"]["base_reveal"] = 608
    fishman["integration"]["chapter_beats"]["safe_full_scene"] = 608
    fishman["integration"]["component_gates"][0]["reveal_chapter"] = 608
    manifest["models"].extend(incoming.values())
    transitions = int(manifest["counts"].get("transitions", 2))
    manifest["counts"] = {
        "models": len(manifest["models"]),
        "transitions": transitions,
        "runtime_scenes": len(manifest["models"]) - transitions,
    }
    write(manifest_path, manifest)

    queue_path = ROOT / "queue" / "asset-requests.json"
    queue = read(queue_path)
    by_id = {row["id"]: row for row in queue["assets"]}
    if REPLACED_ID in by_id:
        by_id[REPLACED_ID]["state"] = "superseded"
        by_id[REPLACED_ID]["next"] = f"replaced_by:{TOTTO_ID}"
    for asset_id, kind in ((PUNK_ID, "runtime_geographic_system"), (TOTTO_ID, "runtime_archipelago_detail_replacement")):
        values = queue_row(asset_id, kind)
        if asset_id in by_id:
            by_id[asset_id].update(values)
        else:
            queue["assets"].append(values)
    write(queue_path, queue)

    print(f"registered {PUNK_ID}; replaced {REPLACED_ID} with {TOTTO_ID}; {len(manifest['models'])} total models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
