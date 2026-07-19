#!/usr/bin/env python3
"""Focused validation for the Totto Land food-geography upgrade package."""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT.parent
ASSET_ID = "totto-land-food-geography"
CONTRACT = ROOT / "contracts" / f"{ASSET_ID}.visual.json"
EVIDENCE = ROOT / "research" / f"{ASSET_ID}.evidence.json"
SOURCE = ROOT / "source" / f"{ASSET_ID}.blend"
GLB = ROOT / "runtime" / f"{ASSET_ID}.glb"
SIDECAR = ROOT / "runtime" / f"{ASSET_ID}.model.json"
MASTER_RENDER = ROOT / "renders" / "runtime" / f"{ASSET_ID}.png"
CONTACT_SHEET = ROOT / "renders" / f"{ASSET_ID}-contact-sheet.png"


def read(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def glb_payload(path: Path) -> tuple[dict, int]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack("<4sII", data[:12])
    assert magic == b"glTF"
    assert version == 2
    assert declared_length == len(data)
    chunk_length, chunk_type = struct.unpack("<II", data[12:20])
    assert chunk_type == 0x4E4F534A
    payload = json.loads(data[20 : 20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\0"))
    return payload, declared_length


def main() -> int:
    contract = read(CONTRACT)
    evidence = read(EVIDENCE)
    sidecar = read(SIDECAR)
    chapters = {item["id"]: item for item in read(APP_ROOT / "data" / "raw" / "chapters.json")}
    payload, declared_length = glb_payload(GLB)

    assert contract["id"] == ASSET_ID
    assert contract["contract_status"] == "built_pending_runtime_integration"
    assert contract["baseline_audit"]["existing_asset_id"] == "totto-land"
    assert contract["baseline_audit"]["upgrade_strategy"].endswith("same anchor.")
    assert contract["runtime_handoff"]["replacement_policy"].startswith("Integration owner replaces/removes")
    assert contract["topology"]["exact_distances"] == "unknown"
    assert "atlas jitter" in contract["topology"]["atlas_policy"]

    resolution = {row["remembered_item"]: row for row in contract["recollection_resolution"]}
    assert resolution["Biscuit island"]["canonical_local_name"] == "Biscuits Island"
    assert resolution["Chocolate Town"]["resolution"] == "partially_supported"
    assert resolution["river island / juice river / chocolate river / canal"]["build_decision"] == "Omitted. No literal inland liquid route was modeled."
    assert resolution["100% Island juice theme"]["gate"] is None
    assert resolution["Seducing Woods"]["canonical_local_name"] == "Forest of Temptation"
    contract_route = next(
        component for component in contract["identity"]["components"]
        if component["id"] == "totto-land-sea-route"
    )
    assert contract_route["verification"] == "verified_state_window"
    assert contract_route["gate_confidence"] == "verified_state_window"
    assert contract_route["default_hidden"] is True
    assert contract_route["reveal_chapter"] == 829
    assert contract_route["active_through_chapter"] == 829.999

    assert sidecar["id"] == ASSET_ID
    assert sidecar["build"]["glb_sha256"] == sha256(GLB)
    assert sidecar["stats"]["bytes"] == declared_length
    assert sidecar["stats"]["objects"] == 333
    assert sidecar["stats"]["vertices_input"] == 19114
    assert sidecar["stats"]["triangles_input"] == 36884
    assert sidecar["stats"]["materials"] == 18
    assert sidecar["stats"]["triangles_input"] < 60000
    assert declared_length < 4_000_000
    assert sidecar["export"]["named_clips"] == [
        {"name": "totto_land_food_route_cycle", "duration_seconds": 5.0417}
    ]

    assert len(payload.get("nodes", [])) == sidecar["stats"]["objects"]
    assert len(payload.get("meshes", [])) == sidecar["stats"]["objects"]
    assert [animation.get("name") for animation in payload.get("animations", [])] == [
        "totto_land_food_route_cycle"
    ]

    expected_gates = {
        "totto-land-food-geography": 651,
        "whole-cake-island": 651,
        "whole-cake-chateau": 651,
        "cacao-island": 827,
        "cacao-chocolate-settlement": 827,
        "pudding-home-cacao": 827,
        "biscuits-island": 828,
        "sweet-city": 829,
        "totto-land-sea-route": 829,
        "seducing-woods": 831,
    }
    counts: Counter[str] = Counter()
    gates: dict[str, set[int]] = defaultdict(set)
    hidden_components: set[str] = set()
    route_node = None
    for node in payload["nodes"]:
        assert "mesh" in node, f"unexpected non-mesh runtime node: {node.get('name')}"
        extras = node.get("extras", {})
        for key in ("component_id", "reveal_chapter", "gate_confidence", "default_hidden", "visual_status"):
            assert key in extras, f"{node.get('name')} missing {key}"
        component = extras["component_id"]
        counts[component] += 1
        gates[component].add(extras["reveal_chapter"])
        if extras["default_hidden"]:
            hidden_components.add(component)
        if component == "totto-land-sea-route":
            assert extras["default_hidden"] is True
            assert extras["gate_confidence"] == "verified_state_window"
            assert extras["active_through_chapter"] == 829.999
        else:
            assert extras["default_hidden"] is False
            assert extras["gate_confidence"] == "verified"
            assert "active_through_chapter" not in extras
        if component == "totto-land-sea-route" and "route_claim" in extras:
            route_node = node

    assert set(counts) == set(expected_gates)
    assert hidden_components == {"totto-land-sea-route"}
    assert {component: next(iter(values)) for component, values in gates.items()} == expected_gates
    assert counts["whole-cake-island"] >= 20
    assert counts["whole-cake-chateau"] >= 8
    assert counts["sweet-city"] >= 40
    assert counts["seducing-woods"] >= 50
    assert counts["cacao-island"] >= 70
    assert counts["cacao-chocolate-settlement"] >= 30
    assert counts["biscuits-island"] >= 55
    assert counts["totto-land-sea-route"] >= 10

    assert route_node is not None
    route_extras = route_node["extras"]
    assert route_extras["route_claim"] == "ordinary open sea path indicated by Pudding in chapter 829"
    assert route_extras["not_a_claim"] == "not a juice river, chocolate river, canal, or exact canon bearing"
    assert route_extras["clip:totto_land_food_route_cycle"] == "ambient_loop"

    forbidden_node_terms = ("chocolate town", "100% island", "juice river", "chocolate river", "canal", "candy waterfall")
    for node in payload["nodes"]:
        name = node.get("name", "").lower()
        component = node.get("extras", {}).get("component_id", "").lower()
        assert not any(term in name or term in component for term in forbidden_node_terms), node.get("name")

    chapter_rows = {row["chapter"]: row for row in evidence["chapter_evidence"]}
    assert set(chapter_rows) == {651, 827, 828, 829, 831}
    for chapter_id, row in chapter_rows.items():
        chapter = chapters[chapter_id]
        assert row["title"] == chapter["title"]
        assert row["description_sha256"] == sha256_text(chapter["description"])

    claims = {row["claim"]: row for row in evidence["claim_resolution"]}
    assert claims["Chocolate Town"]["status"] == "unverified_proper_label"
    assert claims["juice river / chocolate river / canal / candy waterfall"]["build"] == "omitted"
    assert claims["100% Island juice geography"]["gate"] is None
    assert claims["navigable open sea path"]["gate"] == 829
    assert claims["navigable open sea path"]["status"] == "verified_state_window"
    assert claims["navigable open sea path"]["active_through_chapter"] == 829.999
    assert claims["navigable open sea path"]["default_hidden"] is True

    for item in evidence["source_files"] + evidence["artifacts"]:
        path = Path(item["path"])
        assert path.exists(), path
        assert len(item["sha256"]) == 64
        assert sha256(path) == item["sha256"], f"hash drift: {path}"

    assert SOURCE.stat().st_size > 1_000_000
    master = Image.open(MASTER_RENDER)
    assert master.mode == "RGBA"
    assert master.size == (1600, 1050)
    alpha = master.getchannel("A")
    assert alpha.getextrema() == (0, 255)
    assert alpha.getpixel((0, 0)) == 0
    assert alpha.getpixel((master.width - 1, 0)) == 0
    contact = Image.open(CONTACT_SHEET)
    assert contact.size == (1800, 1220)

    old_glb = ROOT / "runtime" / "totto-land.glb"
    old_sidecar = ROOT / "runtime" / "totto-land.model.json"
    assert sha256(old_glb) == evidence["baseline"]["glb_sha256"]
    assert sha256(old_sidecar) == evidence["baseline"]["sidecar_sha256"]

    print("Totto Land food geography verified")
    print(f"  runtime id: {ASSET_ID}")
    print(f"  objects: {sidecar['stats']['objects']}")
    print(f"  triangles: {sidecar['stats']['triangles_input']}")
    print(f"  GLB bytes: {declared_length}")
    print(f"  components: {len(expected_gates)}")
    print("  chapter gates: 651, 827, 828, 829, 831")
    print("  clip: totto_land_food_route_cycle (5.0417s)")
    print("  state window: totto-land-sea-route only (829-829.999, default hidden)")
    print("  unsupported liquid geography: omitted")
    print(f"  artifact hashes verified: {len(evidence['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
