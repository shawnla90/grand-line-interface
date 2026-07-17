#!/usr/bin/env python3
"""Verify the complete loader-ready narrative Blender batch."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/narrative-blockouts.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    index = json.loads((ROOT / "contracts/narrative-scene-index.json").read_text(encoding="utf-8"))
    expected = {item["id"] for item in index["contracts"]}
    assert {item["id"] for item in manifest["assets"]} == expected
    assert manifest["schema_version"] == 2
    for item in manifest["assets"]:
        blend = ROOT / item["blend"]
        render = ROOT / item["render"]
        contract = ROOT / item["contract"]
        glb = ROOT / item["runtime_glb"]
        model = ROOT / item["runtime_model"]
        assert blend.read_bytes()[:7] == b"BLENDER"
        assert blend.stat().st_size > 100_000
        assert png_dimensions(render) == (1200, 900)
        assert glb.read_bytes()[:4] == b"glTF"
        assert item["blend_sha256"] == sha(blend)
        assert item["render_sha256"] == sha(render)
        assert item["contract_sha256"] == sha(contract)
        assert item["glb_sha256"] == sha(glb)
        assert item["model_sha256"] == sha(model)
        assert item["maturity"] == "runtime_blockout_v1"
        assert item["runtime_export"] is True
        assert item["frame_end"] == 120

    queue = json.loads((ROOT / "queue/asset-requests.json").read_text(encoding="utf-8"))
    queued = {item["id"]: item for item in queue["assets"]}
    for asset_id in expected:
        assert queued[asset_id]["state"] == "integration_ready"
        assert (ROOT / queued[asset_id]["runtime_glb"]).exists()
        assert (ROOT / queued[asset_id]["fallback"]).exists()

    water7 = json.loads((ROOT / "contracts/water-7-sea-train-network.visual.json").read_text(encoding="utf-8"))
    assert water7["route_network"]["track_elevation"] == "just_below_ocean_surface"
    assert water7["chapter_logic"]["temporal_variants"][0]["reveal_chapter"] == 322
    assert water7["chapter_logic"]["temporal_variants"][2]["reveal_chapter"] == 656
    print("11 loader-ready narrative Blender scenes verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
