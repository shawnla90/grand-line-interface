#!/usr/bin/env python3
"""Verify hashes, dimensions, contracts, and queue states for the first v2 blockouts."""

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
    assert {item["id"] for item in manifest["assets"]} == {
        "loguetown-roger-execution",
        "water-7-sea-train-network",
    }
    for item in manifest["assets"]:
        blend = ROOT / item["blend"]
        render = ROOT / item["render"]
        contract = ROOT / item["contract"]
        assert blend.read_bytes()[:7] == b"BLENDER"
        assert blend.stat().st_size > 100_000
        assert png_dimensions(render) == (1400, 900)
        assert item["blend_sha256"] == sha(blend)
        assert item["render_sha256"] == sha(render)
        assert item["contract_sha256"] == sha(contract)
        assert item["maturity"] == "3d_blockout_not_final_art"
        assert item["runtime_export"] is False
        assert item["frame_end"] == 120

    queue = json.loads((ROOT / "queue/asset-requests.json").read_text(encoding="utf-8"))
    queued = {item["id"]: item for item in queue["assets"]}
    for asset_id in ("loguetown-roger-execution", "water-7-sea-train-network"):
        assert queued[asset_id]["state"] == "scene_3d"
        assert queued[asset_id]["maturity"] == "3d_blockout_not_final_art"
        assert (ROOT / queued[asset_id]["blend"]).exists()
        assert (ROOT / queued[asset_id]["review_render"]).exists()

    water7 = json.loads((ROOT / "contracts/water-7-sea-train-network.visual.json").read_text(encoding="utf-8"))
    assert water7["route_network"]["track_elevation"] == "just_below_ocean_surface"
    assert water7["chapter_logic"]["temporal_variants"][0]["reveal_chapter"] == 322
    assert water7["chapter_logic"]["temporal_variants"][2]["reveal_chapter"] == 656
    print("priority narrative Blender blockouts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
