#!/usr/bin/env python3
"""Build the complete Blender -> MapLibre runtime registry.

The registry joins validated GLB sidecars, transparent fallbacks, visual
contracts, and chapter gates. It never guesses an unknown chapter: unresolved
components are present as default-hidden glTF nodes and listed explicitly.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

TRANSITIONS = ("skypiea-knock-up-stream", "wano-waterfall-ascent")
RUNTIME_SCENES = (
    "fish-man-island",
    "totto-land",
    "world-government-tarai-system",
    "conomi-arlong-park",
    "arabasta-kingdom",
    "cactus-island-whisky-peak",
    "dressrosa-green-bit",
    "zou-zunesha",
    "amazon-lily",
    "mary-geoise-red-line",
    "sabaody-grove-network",
    "skypiea-sky-system",
    "loguetown-roger-execution",
    "water-7-sea-train-network",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> list[int]:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"Not a PNG: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        if handle.read(4) != b"IHDR" or length < 8:
            raise RuntimeError(f"PNG has no IHDR: {path}")
        return list(struct.unpack(">II", handle.read(8)))


def fallback_info(path: str) -> dict:
    absolute = ROOT / path
    return {
        "path": path,
        "bytes": absolute.stat().st_size,
        "sha256": sha(absolute),
        "pixel_size": png_size(absolute),
        "alpha": True,
    }


def runtime_policy(feature_flag: str) -> dict:
    return {
        "feature_flag": feature_flag,
        "default": "fallback_raster",
        "enable_glb_when": "feature flag on, close zoom, mercator projection, chapter gate open",
        "unload_when_hidden": True,
        "dispose_on_remove": ["geometries", "materials", "textures"],
        "globe_policy": "transparent fallback; do not apply a naive mercator model matrix on globe",
        "node_gate_policy": "read component_id, reveal_chapter, gate_confidence, and default_hidden from glTF node extras",
    }


def anchor_from_contract(contract: dict) -> dict:
    identity = contract.get("identity", {})
    if identity.get("anchor"):
        value = identity["anchor"].get("atlas_anchor")
        if value:
            return value
    if identity.get("central"):
        return identity["central"]["atlas_anchor"]
    # The connected Tarai system is a local relational scene. Use the current
    # itself only as an entry point; never project its triangle onto the globe.
    for component in identity.get("components", []):
        if component.get("slug") == "tarai-current":
            return component["atlas_anchor"]
    raise RuntimeError(f"No scene entry anchor for {contract['id']}")


def narrative_components(contract: dict) -> list[dict]:
    rows = []
    for component in contract["identity"]["components"]:
        reveal = component.get("debut_chapter")
        rows.append({
            "id": component.get("id") or component.get("slug"),
            "role": component.get("role"),
            "reveal_chapter": reveal,
            "verification": "verified" if reveal is not None else "chapter_to_verify",
            "default_hidden": reveal is None,
        })
    return rows


def totto_components(contract: dict) -> list[dict]:
    identity = contract["identity"]
    rows = [
        {"id": identity["central"]["slug"], "role": "central_main_island",
         "reveal_chapter": identity["central"]["debut_chapter"], "verification": "verified", "default_hidden": False},
        {"id": identity["nested_landmark"]["slug"], "role": "nested_landmark",
         "reveal_chapter": identity["nested_landmark"]["debut_chapter"], "verification": "verified", "default_hidden": False},
    ]
    for item in identity["subsidiaries"]:
        reveal = item.get("debut_chapter")
        rows.append({
            "id": item["slug"],
            "role": item["role"],
            "theme_hint": item["theme_hint"]["theme"],
            "reveal_chapter": reveal,
            "verification": "verified" if reveal is not None else "chapter_to_verify",
            "default_hidden": reveal is None,
            "relative_placement": item["relative_placement"],
        })
    return rows


def tarai_components(contract: dict) -> list[dict]:
    rows = []
    for item in contract["identity"]["components"]:
        rows.append({
            "id": item["slug"], "role": item["role"],
            "reveal_chapter": item["debut_chapter"],
            "verification": "verified", "default_hidden": False,
        })
    return rows


def scene_model(asset_id: str, builds: dict) -> dict:
    sidecar = read(ROOT / f"runtime/{asset_id}.model.json")
    feature_flag = "NEXT_PUBLIC_RUNTIME_3D_ASSETS"
    if asset_id == "fish-man-island":
        plate = next(x for x in read(ROOT / "manifests/island-plates.json")["plates"] if x["id"] == asset_id)
        integration = {
            "mode": "maplibre_custom_3d_layer",
            "fallback_mode": "maplibre_image_source",
            "anchor": plate["center"],
            "coordinates": plate["coordinates"],
            "anchor_confidence": "derived",
            "chapter_beats": {
                "base_reveal": plate["spoiler_gate"]["debut_chapter"],
                "dive": plate["descent_contract"]["chapters"],
                "safe_full_scene": plate["spoiler_gate"]["debut_chapter"],
            },
            "component_gates": [{"id": asset_id, "reveal_chapter": plate["spoiler_gate"]["debut_chapter"],
                                 "verification": "verified", "default_hidden": False}],
            "layout_status": "exact_deterministic_hero_ring_footprint",
            "projection_support": ["mercator_closeup"],
        }
        fallback = plate["raster"]
        label = plate["label"]
        source = plate["source_blend"]
        contract_ref = None
        maturity = "runtime_3d_blockout_from_approved_plate"
    else:
        contract = read(ROOT / f"contracts/{asset_id}.visual.json")
        anchor = anchor_from_contract(contract)
        build = builds.get(asset_id, {})
        if asset_id == "totto-land":
            components = totto_components(contract)
            base = contract["identity"]["central"]["debut_chapter"]
            safe = build["safe_full_scene_chapter"]
            withheld = [x["id"] for x in components if x["verification"] == "chapter_to_verify"]
        elif asset_id == "world-government-tarai-system":
            components = tarai_components(contract)
            base = 522  # cited Tarai Current debut; the connected topology is not shown before it
            safe = build["safe_full_scene_chapter"]
            withheld = []
        else:
            components = narrative_components(contract)
            logic = contract["chapter_logic"]
            base = logic["base_reveal_chapter"]
            safe = build.get("safe_full_scene_chapter")
            if safe is None:
                safe = 1 if asset_id == "loguetown-roger-execution" else 657
            withheld = [x["id"] for x in logic["temporal_variants"]
                        if x.get("verification") == "chapter_to_verify" or x.get("reveal_chapter") is None]
            withheld += [x["id"] for x in logic["event_scenes"]
                         if x.get("verification") == "chapter_to_verify" or x.get("reveal_chapter") is None]
        integration = {
            "mode": "maplibre_custom_3d_layer",
            "fallback_mode": "screen_space_html_marker" if asset_id in {
                "world-government-tarai-system", "zou-zunesha", "mary-geoise-red-line",
                "water-7-sea-train-network"} else "maplibre_image_source_or_inset",
            "anchor": [anchor["lng"], anchor["lat"]],
            "anchor_confidence": anchor["confidence"],
            "anchor_usage": anchor["usage"],
            "anchor_warning": anchor["warning"],
            "chapter_beats": {"base_reveal": base, "safe_full_scene": safe},
            "component_gates": components,
            "withheld_variants": sorted(set(withheld)),
            "layout_status": build.get("layout_status", "contract_relationship_graph"),
            "projection_support": ["mercator_closeup"],
            "scale_policy": {"mode": "visual_fit_not_canon_scale", "use_model_bounds": True},
        }
        if asset_id == "zou-zunesha":
            integration["anchor_policy"] = "moving_entity_chapter_local; atlas anchor is entry camera only"
        if asset_id in {"world-government-tarai-system", "water-7-sea-train-network"}:
            integration["route_policy"] = "local relationship schematic; never project local bearings as canon globe geometry"
        fallback = f"renders/runtime/{asset_id}.png"
        label = contract["label"]
        source = f"source/{asset_id}.blend"
        contract_ref = f"contracts/{asset_id}.visual.json"
        maturity = "runtime_blockout_v1"
    return {
        "id": asset_id,
        "label": label,
        "maturity": maturity,
        "glb": f"runtime/{asset_id}.glb",
        # String alias retained for the app's existing raster sync script.
        "fallback_raster": fallback,
        "fallback": fallback_info(fallback),
        "source_blend": source,
        "contract": contract_ref,
        "integration": integration,
        "runtime_policy": runtime_policy(feature_flag),
        "stats": sidecar["stats"],
        "build": sidecar["build"],
    }


def main() -> int:
    transition_manifest = read(ROOT / "manifests/vertical-transitions.json")
    transitions = {item["id"]: item for item in transition_manifest["transitions"]}
    scene_build_path = ROOT / "manifests/runtime-scene-builds.json"
    builds = {x["id"]: x for x in read(scene_build_path)["assets"]}
    models = []
    for model_id in TRANSITIONS:
        sidecar = read(ROOT / f"runtime/{model_id}.model.json")
        transition = transitions[model_id]
        models.append({
            "id": model_id,
            "label": transition["label"],
            "maturity": "runtime_3d_pilot",
            "glb": f"runtime/{model_id}.glb",
            "fallback_raster": transition["raster"],
            "fallback": fallback_info(transition["raster"]),
            "fallback_preview": transition["preview"],
            "source_blend": transition["source_blend"],
            "contract": None,
            "integration": transition["integration"],
            "runtime_policy": runtime_policy("NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS") | {
                "ship_motion_owner": "atlas runtime; preview proxy is excluded from GLB"
            },
            "stats": sidecar["stats"],
            "build": sidecar["build"],
        })
    models.extend(scene_model(asset_id, builds) for asset_id in RUNTIME_SCENES)
    registry = {
        "schema_version": 2,
        "asset_class": "maplibre-runtime-3d",
        "repo_write_contract": "asset production only; application integration happens in the app-owning session",
        "feature_flags": {
            "vertical_transitions": "NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS",
            "runtime_scenes": "NEXT_PUBLIC_RUNTIME_3D_ASSETS",
        },
        # Backward compatibility for the existing raster sync pilot.
        "feature_flag": "NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS",
        "counts": {"models": len(models), "transitions": len(TRANSITIONS), "runtime_scenes": len(RUNTIME_SCENES)},
        "models": models,
    }
    out = ROOT / "manifests/runtime-3d.json"
    out.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REGISTRY={out}")
    print(json.dumps(registry["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
