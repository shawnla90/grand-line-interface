#!/usr/bin/env python3
"""Register Water 7, Mary Geoise, and the Fish-Man descent runtime systems."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATER = "water-7-sea-train-network"
MARY = "mary-geoise-red-line"
DESCENT = "fish-man-red-line-descent"
IDS = (WATER, MARY, DESCENT)


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


def gate(
    ident: str,
    role: str,
    reveal: int | None,
    verification: str = "verified",
    hidden: bool = False,
    through: float | None = None,
) -> dict:
    row = {
        "id": ident,
        "role": role,
        "reveal_chapter": reveal,
        "verification": verification,
        "default_hidden": hidden,
    }
    if through is not None:
        row["active_through_chapter"] = through
    return row


WATER_GATES = [
    gate("subsurface-sea-rails", "route_geometry", 322),
    gate("puffing-tom", "commercial_sea_train", 322),
    gate("san-faldo", "connected_island", 322),
    gate("shift-station", "intermediate_station_and_lighthouse", 322),
    gate("blue-station", "water_7_station", 322),
    gate("water-7", "network_hub_city", 323),
    gate("enies-lobby", "never_night_government_terminus_over_waterfall_void", 358),
    gate("aqua-laguna", "temporary_water_7_flood_and_route_hazard", 363, "verified_state_window", True, 367.999),
    gate("rocketman", "temporary_prototype_train_pursuit", 365, "verified_state_window", True, 378.999),
    gate("day-station", "enies_lobby_station", 375),
    gate("st-poplar", "connected_island", 496),
    gate("puffing-ice", "post_timeskip_train", 656),
    gate("pucci", "connected_island", 657),
]

MARY_GATES = [
    gate("mary-geoise", "summit_city", 142),
    gate("pangaea-castle", "central_castle_exterior", 142),
    gate("red-line-summit", "irregular_world_continent_cross_section", 142),
    gate("red-port-paradise", "lower_port_where_original_ships_remain", 905),
    gate("bondola-route", "people_carrying_vertical_transit", 905),
    gate("red-port-new-world", "opposite_lower_port", None, "chapter_to_verify", True),
]


def artifact(asset_id: str, label: str, integration: dict) -> dict:
    glb = ROOT / f"runtime/{asset_id}.glb"
    sidecar = read(ROOT / f"runtime/{asset_id}.model.json")
    fallback = ROOT / f"renders/runtime/{asset_id}.png"
    if sha(glb) != sidecar["build"]["glb_sha256"]:
        raise RuntimeError(f"{asset_id}: GLB sidecar hash mismatch")
    return {
        "id": asset_id,
        "label": label,
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
        "contract": f"contracts/{asset_id}.visual.json",
        "integration": integration,
        "runtime_policy": POLICY,
        "stats": sidecar["stats"],
        "build": sidecar["build"],
    }


def water_model() -> dict:
    return artifact(WATER, "Water 7, Aqua Laguna, and Sea Train network", {
        "mode": "maplibre_custom_3d_layer",
        "fallback_mode": "maplibre_image_source_or_inset",
        "anchor": [-73.7901, 3.1588],
        "anchor_confidence": "derived",
        "anchor_usage": "scene_entry_anchor_only",
        "anchor_warning": "The atlas point opens a local relationship graph; rail bearings and distances are not canon survey geometry.",
        "chapter_beats": {
            "network_reveal": 322,
            "base_reveal": 322,
            "water_7_arrival": 323,
            "aqua_laguna_reaches_city": 363,
            "rocketman_departure": 365,
            "enies_arrival": 375,
            "safe_full_scene": 657,
        },
        "component_gates": WATER_GATES,
        "named_clips": [
            "water7_puffing_tom_route_cycle",
            "water7_rocketman_route_state",
            "water7_aqua_laguna_tide_state",
            "water7_enies_waterfall_cycle",
        ],
        "animation_plan": {
            "clock": "chapter_entry_elapsed_ms",
            "reduced_motion": "freeze Puffing Tom and the permanent waterfall; retain chapter-sampled Aqua Laguna and Rocketman positions",
            "chapter_states": [],
            "geographic_tracks": [
                {
                    "channel": "water7_aqua_laguna",
                    "name": "water7_aqua_laguna_tide_state",
                    "keyframes": [
                        {"chapter": 362, "progress": 0.0},
                        {"chapter": 363, "progress": 0.2},
                        {"chapter": 364, "progress": 0.45},
                        {"chapter": 365, "progress": 0.65},
                        {"chapter": 366, "progress": 0.82},
                        {"chapter": 367, "progress": 1.0},
                    ],
                    "hold_before": False,
                    "hold_after": False,
                },
                {
                    "channel": "water7_rocketman",
                    "name": "water7_rocketman_route_state",
                    "keyframes": [
                        {"chapter": 365, "progress": 0.0},
                        {"chapter": 367, "progress": 0.18},
                        {"chapter": 375, "progress": 0.82},
                        {"chapter": 378, "progress": 1.0},
                    ],
                    "hold_before": False,
                    "hold_after": False,
                },
            ],
            "ambient_tracks": [
                {
                    "channel": "water7_puffing_tom",
                    "name": "water7_puffing_tom_route_cycle",
                    "active_from_chapter": 322,
                    "duration_ms": 5042,
                    "loop": True,
                },
                {
                    "channel": "water7_enies_waterfall",
                    "name": "water7_enies_waterfall_cycle",
                    "active_from_chapter": 375,
                    "duration_ms": 4208,
                    "loop": True,
                },
            ],
        },
        "withheld_variants": [],
        "layout_status": "dynamic_relationship_graph_not_canon_bearings",
        "projection_support": ["mercator_closeup"],
        "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
        "route_policy": "Sea Train branches are cited relationships rendered as a local schematic; do not project them as literal globe bearings.",
        "flood_policy": "Aqua Laguna floods Water 7 and the approach waters only; Enies Lobby retains its permanent daylight waterfall-void geography.",
    })


def mary_model() -> dict:
    return artifact(MARY, "Mary Geoise, Red Port, and Bondola ascent", {
        "mode": "maplibre_custom_3d_layer",
        "fallback_mode": "maplibre_image_source_or_inset",
        "anchor": [-2.7363, -9.3782],
        "anchor_confidence": "derived",
        "anchor_usage": "scene_entry_anchor_only",
        "anchor_warning": "The local vertical cross-section is contract-driven; its irregular coastline is stylized rather than survey geometry.",
        "chapter_beats": {"base_reveal": 142, "red_port_and_bondola": 905, "safe_full_scene": 905},
        "component_gates": MARY_GATES,
        "named_clips": ["mary_geoise_bondola_cycle", "red_line_cloud_drift"],
        "animation_plan": {
            "clock": "chapter_entry_elapsed_ms",
            "reduced_motion": "freeze the summit cloud bank and Bondola at their authored rest poses",
            "chapter_states": [],
            "ambient_tracks": [
                {
                    "channel": "red_line_clouds",
                    "name": "red_line_cloud_drift",
                    "active_from_chapter": 142,
                    "duration_ms": 5042,
                    "loop": True,
                },
                {
                    "channel": "mary_geoise_bondola",
                    "name": "mary_geoise_bondola_cycle",
                    "active_from_chapter": 905,
                    "active_through_chapter": 1125,
                    "duration_ms": 5042,
                    "loop": True,
                },
            ],
        },
        "withheld_variants": ["red-port-new-world", "late-interior-reveals"],
        "layout_status": "vertical_cross_section_with_irregular_stylized_coastline",
        "projection_support": ["mercator_closeup"],
        "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
        "transport_policy": "Bondola carries people. Their original ships remain at Red Port; the lift does not haul those ships over the Red Line.",
        "coastline_policy": "Map and GLB silhouettes are deterministic art direction; the exact jagged Red Line coastline is not asserted as canon survey data.",
    })


def descent_model() -> dict:
    contract = read(ROOT / "contracts/fish-man-red-line-descent.visual.json")
    return artifact(DESCENT, "Sabaody coating and Fish-Man descent", {
        "mode": "maplibre_custom_3d_layer",
        "fallback_mode": "maplibre_image_source_or_inset",
        "anchor": [-48.2843, 2.9],
        "anchor_confidence": "derived",
        "anchor_usage": "local_transition_stage_only",
        "anchor_warning": "This anchor opens an explanatory vertical theatre and does not claim a literal horizontal undersea route.",
        "chapter_beats": {"base_reveal": 496, "coating_yard": 507, "dive": 602, "deep": 605, "trench": 607, "safe_full_scene": 507},
        "component_gates": contract["components"],
        "named_clips": ["fishman_descent_route_state", "fishman_current_cycle", "fishman_volcanic_cycle"],
        "animation_plan": {
            "clock": "chapter_entry_elapsed_ms",
            "reduced_motion": "retain the chapter-sampled Sunny depth and freeze currents and volcanic vent motion",
            "chapter_states": [],
            **contract["animation_plan"],
        },
        "withheld_variants": [],
        "layout_status": "local_undersea_cross_section_not_survey_geometry",
        "projection_support": ["mercator_closeup"],
        "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
        "route_policy": "The vertical depth sequence is chapter-verified; horizontal bearings, distances, and wall proportions are explanatory art direction.",
        "destination_policy": "The descent stops at a distant gate in chapter 607. The separate fish-man-island asset owns the full destination from chapter 608.",
    })


def queue_values(asset_id: str) -> dict:
    kind = "undersea_runtime_transition" if asset_id == DESCENT else "dynamic_runtime_geographic_system"
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
        "next": "close-zoom chapter scrub browser proof and LOD0 art pass",
    }


def update_build_manifests(models: dict[str, dict]) -> None:
    """Keep editable-source inventories aligned with the signed runtime rows."""
    collections = ["00_TOPOLOGY", "10_LANDMARKS", "20_EVENT_STATES", "30_ATMOSPHERE_FX", "40_RUNTIME_LOD"]
    runtime_path = ROOT / "manifests/runtime-scene-builds.json"
    runtime = read(runtime_path)
    runtime_by_id = {row["id"]: row for row in runtime.get("assets", [])}
    narrative_path = ROOT / "manifests/narrative-blockouts.json"
    narrative = read(narrative_path)
    narrative_by_id = {row["id"]: row for row in narrative.get("assets", [])}
    for asset_id, model in models.items():
        integration = model["integration"]
        base = {
            "id": asset_id,
            "blend": f"source/{asset_id}.blend",
            "render": f"renders/runtime/{asset_id}.png",
            "contract": f"contracts/{asset_id}.visual.json",
            "maturity": "runtime_blockout_v1",
            "runtime_export": True,
            "safe_full_scene_chapter": integration["chapter_beats"]["safe_full_scene"],
            "layout_status": integration["layout_status"],
            "collections": collections,
            "component_ids": sorted(gate["id"] for gate in integration["component_gates"]),
            "objects": model["stats"]["objects"],
            "blend_sha256": sha(ROOT / f"source/{asset_id}.blend"),
            "render_sha256": model["fallback"]["sha256"],
            "contract_sha256": sha(ROOT / f"contracts/{asset_id}.visual.json"),
        }
        runtime_by_id[asset_id] = base
        narrative_by_id[asset_id] = {
            **base,
            "runtime_glb": f"runtime/{asset_id}.glb",
            "runtime_model": f"runtime/{asset_id}.model.json",
            "frame_end": 121,
            "glb_sha256": model["build"]["glb_sha256"],
            "model_sha256": sha(ROOT / f"runtime/{asset_id}.model.json"),
        }
    runtime["assets"] = [runtime_by_id[key] for key in sorted(runtime_by_id)]
    narrative["assets"] = [narrative_by_id[key] for key in sorted(narrative_by_id)]
    write(runtime_path, runtime)
    write(narrative_path, narrative)


def main() -> int:
    manifest_path = ROOT / "manifests/runtime-3d.json"
    manifest = read(manifest_path)
    models = {WATER: water_model(), MARY: mary_model(), DESCENT: descent_model()}
    incoming = dict(models)
    replaced = set(incoming)
    ordered = []
    for row in manifest["models"]:
        if row["id"] in replaced:
            ordered.append(incoming.pop(row["id"]))
        else:
            ordered.append(row)
    ordered.extend(incoming.values())
    manifest["models"] = ordered
    manifest["counts"] = {"models": len(ordered), "transitions": 3, "runtime_scenes": len(ordered) - 3}
    write(manifest_path, manifest)

    queue_path = ROOT / "queue/asset-requests.json"
    queue = read(queue_path)
    by_id = {row["id"]: row for row in queue["assets"]}
    for asset_id in IDS:
        values = queue_values(asset_id)
        if asset_id in by_id:
            by_id[asset_id].update(values)
        else:
            queue["assets"].append(values)
    write(queue_path, queue)
    update_build_manifests(models)
    print(f"registered {', '.join(IDS)}; {len(ordered)} runtime models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
