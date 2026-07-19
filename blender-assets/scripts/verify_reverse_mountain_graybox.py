#!/usr/bin/env python3
"""Verify the promoted Reverse Mountain LOD1 graybox and its runtime contract."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "reverse-mountain-twin-cape-voyage"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glb_json(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, declared = struct.unpack("<4sII", data[:12])
    assert magic == b"glTF" and version == 2 and declared == len(data)
    length, chunk_type = struct.unpack("<II", data[12:20])
    assert chunk_type == 0x4E4F534A
    return json.loads(data[20 : 20 + length].decode("utf-8").rstrip(" \t\r\n\x00"))


def png(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()[:26]
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    return width, height, data[25]


def contract_clips(contract: dict) -> set[str]:
    clips: set[str] = set(contract["named_clips"]["fx"])
    for group in ("going_merry", "laboon", "crocus_2_5d"):
        clips.update(item["name"] for item in contract["named_clips"][group])
    return clips


def main() -> int:
    contract = read(ROOT / "contracts" / f"{ASSET_ID}.visual.json")
    manifest = read(ROOT / "manifests" / "runtime-3d.json")
    sidecar = read(ROOT / "runtime" / f"{ASSET_ID}.model.json")
    queue = {item["id"]: item for item in read(ROOT / "queue" / "asset-requests.json")["assets"]}
    model = next(item for item in manifest["models"] if item["id"] == ASSET_ID)
    glb_path = ROOT / model["glb"]
    doc = glb_json(glb_path)

    assert queue[ASSET_ID]["state"] == "integration_ready"
    assert model["maturity"] == "runtime_animated_graybox_v1"
    assert sidecar["lod"]["built"] == "LOD1_LOCAL_THEATRE"
    assert sidecar["stats"]["triangles_input"] <= 70000
    assert glb_path.stat().st_size < 6 * 1024 * 1024
    assert sha(glb_path) == model["build"]["glb_sha256"] == sidecar["build"]["glb_sha256"]

    expected_components = {item["id"] for item in contract["identity"]["components"]}
    tagged = {
        (node.get("extras") or {}).get("component_id")
        for node in doc.get("nodes", [])
        if (node.get("extras") or {}).get("component_id")
    }
    assert tagged == expected_components, f"component mismatch: expected {expected_components - tagged}; extra {tagged - expected_components}"

    expected_clips = contract_clips(contract)
    exported_clips = {item.get("name") for item in doc.get("animations", [])}
    declared_clips = set(model["integration"]["named_clips"])
    assert len(expected_clips) == 21
    assert exported_clips == expected_clips == declared_clips
    assert all(item["duration_seconds"] > 0 for item in sidecar["export"]["named_clips"])

    gates = {item["id"]: item for item in model["integration"]["component_gates"]}
    assert gates["reverse-mountain-massif"]["reveal_chapter"] == 101
    assert gates["twin-cape"]["reveal_chapter"] == 102
    assert gates["laboon"]["reveal_chapter"] == 103
    assert gates["crocus"]["reveal_chapter"] == 103
    interior = gates["laboon-interior-theatre"]
    assert interior["default_hidden"] is True
    assert interior["verification"] == "verified_state_window"
    assert interior["active_through_chapter"] == 103.999
    whirlpool = gates["local-whirlpool-emitter"]
    assert whirlpool["reveal_chapter"] is None
    assert whirlpool["verification"] == "chapter_to_verify"
    assert whirlpool["default_hidden"] is True

    fallback = ROOT / model["fallback"]["path"]
    assert sha(fallback) == model["fallback"]["sha256"]
    width, height, color_type = png(fallback)
    assert [width, height] == model["fallback"]["pixel_size"]
    assert color_type in {4, 6}

    contract_masks = {item["id"] for item in contract["fx_masks"]}
    manifest_masks = {item["id"] for item in model["integration"]["fx_masks"]}
    assert contract_masks == manifest_masks and len(manifest_masks) == 5
    for mask in model["integration"]["fx_masks"]:
        path = ROOT / mask["path"]
        assert path.exists() and sha(path) == mask["sha256"]
        assert png(path)[:2] == (256, 256)
    assert next(item for item in model["integration"]["fx_masks"] if item["id"] == "whirlpool-control-rgba")["default_hidden"] is True

    states = model["integration"]["animation_plan"]["chapter_states"]
    assert [state["chapter"] for state in states] == [101, 102, 103, 104, 105]
    used = {clip["name"] for state in states for clip in state["clips"]}
    assert used <= exported_clips
    assert "whirlpool_loop_default_hidden" not in used
    for state in states:
        duration = state["duration_ms"]
        channels: dict[str, list[tuple[int, int]]] = {}
        for item in state["clips"]:
            start = item["start_ms"]
            end = start + item["duration_ms"]
            assert 0 <= start < end <= duration
            channels.setdefault(item["channel"], []).append((start, end))
        for channel, spans in channels.items():
            spans.sort()
            assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), f"{state['chapter']} {channel} overlaps"

    print("Reverse Mountain animated graybox verified")
    print(f"  components: {len(tagged)}")
    print(f"  named clips: {len(exported_clips)}")
    print(f"  FX masks: {len(manifest_masks)}")
    print(f"  triangles: {sidecar['stats']['triangles_input']:,}")
    print(f"  GLB: {glb_path.stat().st_size / 1024:.1f} KiB")
    print("  chapters: 101-105; whirlpool remains dark")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
