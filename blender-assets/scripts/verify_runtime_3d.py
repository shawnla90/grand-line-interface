#!/usr/bin/env python3
"""Validate every runtime GLB, fallback, hash, queue gate, and spoiler rule."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 6 * 1024 * 1024
EXPECTED = {
    "skypiea-knock-up-stream", "wano-waterfall-ascent", "fish-man-island",
    "totto-land-food-geography", "punk-hazard-geographic-system",
    "world-government-tarai-system", "conomi-arlong-park",
    "arabasta-kingdom", "cactus-island-whisky-peak", "dressrosa-green-bit",
    "zou-zunesha", "amazon-lily", "mary-geoise-red-line",
    "sabaody-grove-network", "skypiea-sky-system",
    "loguetown-roger-execution", "water-7-sea-train-network",
    "reverse-mountain-twin-cape-voyage",
    "egghead-future-island-system", "wano-onigashima-country-system",
    "elbaph-adam-world-system", "fish-man-red-line-descent",
}
STUDIES = {"whole-cake-island", "impel-down", "sabaody-archipelago"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        magic, version, declared = struct.unpack("<4sII", handle.read(12))
        assert magic == b"glTF" and version == 2
        assert declared == path.stat().st_size
        length, chunk_type = struct.unpack("<II", handle.read(8))
        assert chunk_type == 0x4E4F534A
        return json.loads(handle.read(length).decode("utf-8").rstrip(" \t\r\n\x00"))


def png_alpha(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:26]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert data[25] in {4, 6}, f"{path}: PNG is not grayscale/RGBA alpha"
    return width, height


def main() -> int:
    registry = json.loads((ROOT / "manifests/runtime-3d.json").read_text(encoding="utf-8"))
    by_id = {model["id"]: model for model in registry["models"]}
    assert set(by_id) == EXPECTED
    assert registry["schema_version"] == 2
    assert registry["counts"] == {"models": 22, "transitions": 3, "runtime_scenes": 19}

    gltf_docs = {}
    for model_id in sorted(EXPECTED):
        model = by_id[model_id]
        path = ROOT / model["glb"]
        assert path.stat().st_size < MAX_BYTES
        assert sha(path) == model["build"]["glb_sha256"]
        doc = glb_json(path)
        gltf_docs[model_id] = doc
        fallback = ROOT / model["fallback"]["path"]
        assert sha(fallback) == model["fallback"]["sha256"]
        assert list(png_alpha(fallback)) == model["fallback"]["pixel_size"]
        for gate in (model.get("integration") or {}).get("component_gates", []):
            if gate.get("verification") == "chapter_to_verify":
                assert gate.get("reveal_chapter") is None
                assert gate.get("default_hidden") is True
        print(f"PASS {model_id:34} {path.stat().st_size / 1024:7.1f} KiB")

    # Procedural scenes export component-aware glTF extras for the app loader.
    for model_id in {
        "totto-land-food-geography", "punk-hazard-geographic-system",
        "world-government-tarai-system", "conomi-arlong-park",
        "arabasta-kingdom", "cactus-island-whisky-peak", "dressrosa-green-bit",
        "zou-zunesha", "amazon-lily", "mary-geoise-red-line",
        "sabaody-grove-network", "skypiea-sky-system",
        "reverse-mountain-twin-cape-voyage",
        "egghead-future-island-system", "wano-onigashima-country-system",
        "elbaph-adam-world-system", "fish-man-red-line-descent",
    }:
        assert any((node.get("extras") or {}).get("component_id")
                   for node in gltf_docs[model_id].get("nodes", [])), model_id

    assert "totto-land" not in by_id
    totto = by_id["totto-land-food-geography"]
    assert len(totto["integration"]["component_gates"]) == 10
    assert totto["integration"]["replacement_policy"].startswith("Replaces old totto-land")
    totto_doc = gltf_docs["totto-land-food-geography"]
    assert {x.get("name") for x in totto_doc.get("animations", [])} == {"totto_land_food_route_cycle"}
    totto_route = [x for x in totto_doc["nodes"]
                   if (x.get("extras") or {}).get("component_id") == "totto-land-sea-route"]
    assert totto_route
    assert all((x["extras"].get("default_hidden") is True and
                x["extras"].get("gate_confidence") == "verified_state_window" and
                x["extras"].get("active_through_chapter") == 829.999)
               for x in totto_route)
    sabaody_names = [node.get("name", "") for node in gltf_docs["sabaody-grove-network"].get("nodes", [])]
    assert len([name for name in sabaody_names if name.startswith("Grove ") and name.endswith(" root island")]) == 79
    assert "relational_triangle" in by_id["world-government-tarai-system"]["integration"]["layout_status"]
    assert by_id["zou-zunesha"]["integration"]["anchor_policy"].startswith("moving_entity")

    queue = json.loads((ROOT / "queue/asset-requests.json").read_text(encoding="utf-8"))
    queued = {x["id"]: x for x in queue["assets"]}
    for model_id in EXPECTED:
        assert queued[model_id]["state"] == "integration_ready"
    for study in STUDIES:
        assert queued[study]["state"] == "study_only"
    assert by_id["elbaph-adam-world-system"]["integration"]["theory_policy"].startswith("separate_overlay_only")
    assert "chapter-1188-current-state" in by_id["elbaph-adam-world-system"]["integration"]["withheld_variants"]
    assert by_id["wano-onigashima-country-system"]["integration"]["anchor"] == [118.2306, 7.5751]
    wano_doc = gltf_docs["wano-onigashima-country-system"]
    assert {x.get("name") for x in wano_doc.get("animations", [])} == {"onigashima_geographic_shift"}
    wano_root = next(x for x in wano_doc["nodes"] if x.get("name") == "Onigashima geographic root")
    assert len(wano_root.get("children", [])) >= 35
    flame_nodes = [x for x in wano_doc["nodes"]
                   if (x.get("extras") or {}).get("component_id") == "onigashima-flame-clouds"]
    assert len(flame_nodes) == 14
    assert all((x["extras"].get("active_through_chapter") == 1048.999 and
                x["extras"].get("gate_confidence") == "verified_state_window")
               for x in flame_nodes)
    geography = by_id["wano-onigashima-country-system"]["integration"]["animation_plan"]["geographic_tracks"][0]
    assert [x["chapter"] for x in geography["keyframes"]] == [793, 996, 997, 1027, 1039, 1049, 1108, 1109]
    fishman = by_id["fish-man-island"]
    assert fishman["contract"] == "contracts/fish-man-island.visual.json"
    assert fishman["integration"]["chapter_beats"]["base_reveal"] == 608
    assert fishman["integration"]["chapter_beats"]["safe_full_scene"] == 608
    assert fishman["integration"]["component_gates"][0]["reveal_chapter"] == 608

    water = by_id["water-7-sea-train-network"]
    water_doc = gltf_docs["water-7-sea-train-network"]
    assert {x.get("name") for x in water_doc.get("animations", [])} == {
        "water7_puffing_tom_route_cycle", "water7_rocketman_route_state",
        "water7_aqua_laguna_tide_state", "water7_enies_waterfall_cycle",
    }
    water_gates = {x["id"]: x for x in water["integration"]["component_gates"]}
    for component, reveal, through in (
        ("aqua-laguna", 363, 367.999), ("rocketman", 365, 378.999),
    ):
        gate = water_gates[component]
        assert gate["verification"] == "verified_state_window"
        assert gate["default_hidden"] is True and gate["reveal_chapter"] == reveal
        assert gate["active_through_chapter"] == through
        nodes = [x for x in water_doc["nodes"]
                 if (x.get("extras") or {}).get("component_id") == component]
        assert nodes
        assert all((x["extras"].get("gate_confidence") == "verified_state_window" and
                    x["extras"].get("default_hidden") is True and
                    x["extras"].get("reveal_chapter") == reveal and
                    x["extras"].get("active_through_chapter") == through)
                   for x in nodes)
    water_tracks = water["integration"]["animation_plan"]
    assert [x["chapter"] for x in water_tracks["geographic_tracks"][0]["keyframes"]] == [362, 363, 364, 365, 366, 367]
    assert [x["chapter"] for x in water_tracks["geographic_tracks"][1]["keyframes"]] == [365, 367, 375, 378]

    mary = by_id["mary-geoise-red-line"]
    mary_doc = gltf_docs["mary-geoise-red-line"]
    assert {x.get("name") for x in mary_doc.get("animations", [])} == {
        "mary_geoise_bondola_cycle", "red_line_cloud_drift",
    }
    mary_gates = {x["id"]: x for x in mary["integration"]["component_gates"]}
    assert mary_gates["red-port-paradise"]["reveal_chapter"] == 905
    assert mary_gates["bondola-route"]["reveal_chapter"] == 905
    assert mary_gates["red-port-new-world"] == {
        "id": "red-port-new-world", "role": "opposite_lower_port",
        "reveal_chapter": None, "verification": "chapter_to_verify", "default_hidden": True,
    }
    new_world_nodes = [x for x in mary_doc["nodes"]
                       if (x.get("extras") or {}).get("component_id") == "red-port-new-world"]
    assert new_world_nodes
    assert all((x["extras"].get("gate_confidence") == "chapter_to_verify" and
                x["extras"].get("default_hidden") is True and
                "reveal_chapter" not in x["extras"])
               for x in new_world_nodes)

    descent = by_id["fish-man-red-line-descent"]
    descent_doc = gltf_docs["fish-man-red-line-descent"]
    assert {x.get("name") for x in descent_doc.get("animations", [])} == {
        "fishman_descent_route_state", "fishman_current_cycle", "fishman_volcanic_cycle",
    }
    assert descent["integration"]["chapter_beats"] == {
        "base_reveal": 496, "coating_yard": 507, "dive": 602,
        "deep": 605, "trench": 607, "safe_full_scene": 507,
    }
    descent_gates = {x["id"]: x for x in descent["integration"]["component_gates"]}
    assert descent_gates["red-line-undersea-route"]["reveal_chapter"] == 496
    assert descent_gates["sabaody-coating-yard"]["reveal_chapter"] == 507
    state_components = {
        "coated-sunny-dive", "undersea-pressure-zone", "downward-plume",
        "kraken-route-hazard", "underworld-sea-creatures",
        "deep-sea-volcanic-region", "red-line-trench-approach",
        "fish-man-island-distant-gate",
    }
    for component in state_components:
        gate = descent_gates[component]
        assert gate["verification"] == "verified_state_window"
        assert gate["default_hidden"] is True
        assert gate["active_through_chapter"] == 607.999
        nodes = [x for x in descent_doc["nodes"]
                 if (x.get("extras") or {}).get("component_id") == component]
        assert nodes
        assert all((x["extras"].get("gate_confidence") == "verified_state_window" and
                    x["extras"].get("default_hidden") is True and
                    x["extras"].get("active_through_chapter") == 607.999)
                   for x in nodes)
    descent_track = descent["integration"]["animation_plan"]["geographic_tracks"][0]
    assert [x["chapter"] for x in descent_track["keyframes"]] == [602, 603, 604, 605, 606, 607]
    assert descent_track["hold_before"] is False and descent_track["hold_after"] is False

    punk = by_id["punk-hazard-geographic-system"]
    punk_doc = gltf_docs["punk-hazard-geographic-system"]
    assert {x.get("name") for x in punk_doc.get("animations", [])} == {
        "punk_hazard_environment_cycle", "punk_hazard_duel_memory_fx",
    }
    assert punk["integration"]["chapter_beats"]["base_reveal"] == 655
    assert punk["integration"]["chapter_beats"]["safe_full_scene"] == 664
    punk_nodes = [x for x in punk_doc["nodes"] if (x.get("extras") or {}).get("component_id")]
    memory_nodes = [x for x in punk_nodes
                    if x["extras"].get("component_id") == "duel-memory-fx"]
    assert memory_nodes
    assert all((x["extras"].get("default_hidden") is True and
                x["extras"].get("gate_confidence") == "verified_state_window" and
                x["extras"].get("active_through_chapter") == 658.999)
               for x in memory_nodes)
    assert all(x["extras"].get("default_hidden") is not True
               for x in punk_nodes if x not in memory_nodes)
    ambient = punk["integration"]["animation_plan"]["ambient_tracks"][0]
    assert ambient["active_from_chapter"] == 657 and "active_through_chapter" not in ambient
    print("22 runtime GLBs and fallbacks verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
