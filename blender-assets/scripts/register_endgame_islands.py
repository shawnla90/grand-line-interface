#!/usr/bin/env python3
"""Register the endgame island batch without rebuilding unrelated runtime rows."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDS = (
    "egghead-future-island-system",
    "wano-onigashima-country-system",
    "elbaph-adam-world-system",
)


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
    "dispose_on_remove": ["geometries", "materials", "textures"],
    "globe_policy": "transparent fallback; do not apply a naive mercator model matrix on globe",
    "node_gate_policy": "read component_id, reveal_chapter, gate_confidence, default_hidden, and verified state windows from glTF extras",
}


SCENES = {
    "egghead-future-island-system": {
        "label": "Egghead Future Island system",
        "anchor": [149.0991, -0.4304],
        "base": 1061,
        "safe": 1066,
        "layout": "vertical_phase_stack_relative_topology",
        "withheld": ["punk-records-detached", "egghead-damaged-state"],
        "gates": [
            ("egghead", "winter_island_base", 1061, "verified", False),
            ("egghead-winter-sea", "cold_ocean_and_ice_boundary", 1061, "verified", False),
            ("fabriophase", "lower_factory_city_phase", 1061, "cited_summary", False),
            ("future-city", "climate_modified_city", 1061, "cited_summary", False),
            ("central-factory", "lower_phase_factory", 1061, "cited_summary", False),
            ("scrapyard", "lower_phase_material_yard", 1061, "cited_summary", False),
            ("cloud-plant", "island_cloud_generator", 1065, "cited_summary", False),
            ("labophase", "upper_research_phase", 1065, "cited_summary", False),
            ("frontier-dome", "upper_phase_defense_boundary", 1065, "cited_summary", False),
            ("lab-building-a", "upper_lab_structure", 1065, "cited_summary", False),
            ("lab-building-b", "upper_lab_structure", 1065, "cited_summary", False),
            ("lab-building-c", "upper_lab_structure", 1065, "cited_summary", False),
            ("punk-records-attached", "records_attached_state", 1066, "verified_state_window", False),
        ],
    },
    "wano-onigashima-country-system": {
        "label": "Wano Country and Onigashima system",
        "anchor": [118.2306, 7.5751],
        "base": 793,
        "safe": 978,
        "layout": "regional_bowl_and_local_offshore_fortress_chapter_shifted",
        "withheld": ["onigashima-raid-state", "old-wano-submerged"],
        "animation_plan": {
            "clock": "chapter_entry_elapsed_ms",
            "reduced_motion": "geography remains chapter-sampled; no autonomous repaint loop",
            "chapter_states": [],
            "geographic_tracks": [{
                "channel": "onigashima_geography",
                "name": "onigashima_geographic_shift",
                "hold_before": True,
                "hold_after": True,
                "keyframes": [
                    {"chapter": 793, "progress": 0.0, "state": "offshore"},
                    {"chapter": 996, "progress": 0.0, "state": "offshore_pre_liftoff"},
                    {"chapter": 997, "progress": 0.17266187, "state": "lifted_by_flame_clouds"},
                    {"chapter": 1027, "progress": 0.49640288, "state": "approaching_flower_capital"},
                    {"chapter": 1039, "progress": 0.64028777, "state": "redirected_away_by_momonosuke"},
                    {"chapter": 1049, "progress": 0.78417266, "state": "landed_outside_flower_capital"},
                    {"chapter": 1108, "progress": 0.85611511, "state": "landing_state_held"},
                    {"chapter": 1109, "progress": 1.0, "state": "returned_to_wano_sea_and_sunk"},
                ],
            }],
        },
        "named_clips": ["onigashima_geographic_shift"],
        "gates": [
            ("wano-country", "high_walled_country", 793, "verified", False),
            ("wano-walls", "colossal_country_bowl", 793, "cited_summary", False),
            ("wano-inland-sea", "regional_water_system", 909, "cited_summary", False),
            ("mount-fuji", "central_mountain", 909, "cited_summary", False),
            ("flower-capital", "central_capital", 909, "cited_summary", False),
            ("kuri", "country_region", 909, "cited_summary", False),
            ("udon", "country_region", 909, "cited_summary", False),
            ("kibi", "country_region", 909, "cited_summary", False),
            ("hakumai", "country_region", 909, "cited_summary", False),
            ("ringo", "country_region", 909, "cited_summary", False),
            ("onigashima", "nearby_fortress_island", 793, "verified", False),
            ("skull-dome", "fortress_silhouette", 978, "cited_summary", False),
            ("onigashima-port", "fortress_approach", 978, "cited_summary", False),
            ("giant-katana", "fortress_scale_landmark", 978, "cited_summary", False),
            ("onigashima-roads", "mountain_approach_network", 978, "cited_summary", False),
            ("onigashima-flame-clouds", "verified_flight_support_clouds", 997, "verified_state_window", True),
            ("old-wano-submerged", "historical_depth_state", 1055, "cited_summary", True),
        ],
    },
    "elbaph-adam-world-system": {
        "label": "Elbaph Treasure Tree Adam world system",
        "anchor": [154.2701, -7.171],
        "base": 865,
        "safe": 1132,
        "layout": "vertical_world_tree_canon_relationships_theory_overlay_excluded",
        "withheld": ["heaven-world", "chapter-1188-current-state", "nine-world-theory-overlay"],
        "gates": [
            ("elbaph", "giant_nation_identity", 865, "verified", False),
            ("sleep-mist-route", "fogged_sea_approach", 1127, "cited_summary", False),
            ("elbaph-underworld", "snowy_root_region", 1130, "cited_summary", False),
            ("roads-castle", "underworld_castle", 1130, "cited_summary", False),
            ("giant-fauna-layer", "giant_ecology", 1130, "cited_summary", False),
            ("idas-bar", "underworld_landmark", 1131, "cited_summary", False),
            ("treasure-tree-adam", "vertical_world_connector", 1132, "cited_summary", False),
            ("sun-world", "branch_world", 1132, "cited_summary", False),
            ("warland-settlement", "giant_scale_settlement", 1132, "cited_summary", False),
            ("heaven-world", "upper_cloud_region", None, "chapter_to_verify", True),
            ("chapter-1188-current-state", "current_event_overlay", None, "chapter_to_verify", True),
        ],
    },
}


def gate(row):
    ident, role, chapter, verification, hidden = row
    result = {"id": ident, "role": role, "reveal_chapter": chapter,
              "verification": verification, "default_hidden": hidden}
    if ident == "punk-records-attached":
        result["active_through_chapter"] = 1124.999
    if ident == "onigashima-flame-clouds":
        result["active_through_chapter"] = 1048.999
    return result


def model(asset_id: str) -> dict:
    scene = SCENES[asset_id]
    glb = ROOT / f"runtime/{asset_id}.glb"
    fallback = ROOT / f"renders/runtime/{asset_id}.png"
    sidecar = read(ROOT / f"runtime/{asset_id}.model.json")
    if sha(glb) != sidecar["build"]["glb_sha256"]:
        raise RuntimeError(f"{asset_id}: sidecar hash mismatch")
    integration = {
        "mode": "maplibre_custom_3d_layer",
        "fallback_mode": "maplibre_image_source_or_inset",
        "anchor": scene["anchor"],
        "anchor_confidence": "derived",
        "anchor_usage": "scene_entry_anchor_only",
        "anchor_warning": "Local topology is contract-driven; never infer it from the deterministic atlas point.",
        "chapter_beats": {"base_reveal": scene["base"], "safe_full_scene": scene["safe"]},
        "component_gates": [gate(row) for row in scene["gates"]],
        "withheld_variants": scene["withheld"],
        "layout_status": scene["layout"],
        "projection_support": ["mercator_closeup"],
        "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
        "theory_policy": "separate_overlay_only; never mutate canon base geometry",
    }
    if scene.get("animation_plan"):
        integration["animation_plan"] = scene["animation_plan"]
        integration["named_clips"] = scene["named_clips"]
        integration["geographic_motion_owner"] = "chapter-sampled runtime track; actual GLB root transform"
    return {
        "id": asset_id,
        "label": scene["label"],
        "maturity": "runtime_blockout_v1",
        "glb": f"runtime/{asset_id}.glb",
        "fallback_raster": f"renders/runtime/{asset_id}.png",
        "fallback": {"path": f"renders/runtime/{asset_id}.png", "bytes": fallback.stat().st_size,
                     "sha256": sha(fallback), "pixel_size": png_size(fallback), "alpha": True},
        "source_blend": f"source/{asset_id}.blend",
        "contract": f"contracts/{asset_id}.visual.json",
        "integration": integration,
        "runtime_policy": POLICY,
        "stats": sidecar["stats"],
        "build": sidecar["build"],
    }


def main() -> int:
    manifest_path = ROOT / "manifests/runtime-3d.json"
    manifest = read(manifest_path)
    incoming = {asset_id: model(asset_id) for asset_id in IDS}
    manifest["models"] = [row for row in manifest["models"] if row["id"] not in incoming]
    manifest["models"].extend(incoming[asset_id] for asset_id in IDS)
    transitions = int(manifest["counts"].get("transitions", 2))
    manifest["counts"] = {
        "models": len(manifest["models"]),
        "transitions": transitions,
        "runtime_scenes": len(manifest["models"]) - transitions,
    }
    write(manifest_path, manifest)

    queue_path = ROOT / "queue/asset-requests.json"
    queue = read(queue_path)
    by_id = {row["id"]: row for row in queue["assets"]}
    for asset_id in IDS:
        row = by_id.get(asset_id)
        values = {
            "id": asset_id,
            "kind": "endgame_runtime_island_system",
            "priority": 1,
            "state": "integration_ready",
            "maturity": "runtime_blockout_v1",
            "contract": f"contracts/{asset_id}.visual.json",
            "blend": f"source/{asset_id}.blend",
            "review_render": f"renders/runtime/{asset_id}.png",
            "runtime_glb": f"runtime/{asset_id}.glb",
            "fallback": f"renders/runtime/{asset_id}.png",
            "runtime_manifest": "manifests/runtime-3d.json",
            "next": "app_runtime_chapter_loader_and_close_zoom_proof",
        }
        if row is None:
            queue["assets"].append(values)
        else:
            row.update(values)
    write(queue_path, queue)
    print(f"registered {len(IDS)} endgame islands; {len(manifest['models'])} total runtime models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
