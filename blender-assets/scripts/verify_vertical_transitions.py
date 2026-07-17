#!/usr/bin/env python3
"""Verify portrait vertical-transition assets and their manifest hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("skypiea-knock-up-stream", "wano-waterfall-ascent")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads((ROOT / "manifests/vertical-transitions.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in manifest["transitions"]}
    for transition_id in TARGETS:
        entry = by_id[transition_id]
        png_path = ROOT / entry["raster"]
        preview_path = ROOT / entry["preview"]
        blend_path = ROOT / entry["source_blend"]
        image = Image.open(png_path).convert("RGBA")
        assert list(image.size) == entry["pixel_size"] == [1024, 2048]
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)
        bbox = alpha.getbbox()
        assert bbox and bbox[0] > 0 and bbox[1] > 0 and bbox[2] < image.width and bbox[3] < image.height
        build = entry["build"]
        assert sha256_file(png_path) == build["raster_sha256"]
        assert sha256_file(preview_path) == build["preview_sha256"]
        assert sha256_file(blend_path) == build["blend_sha256"]
        assert entry["animation_reference"]["frames"] == [1, 120]
        print(f"PASS {transition_id}: {image.size}, alpha={bbox}, mode={entry['integration']['mode']}")
    assert manifest["repo_write_contract"] == "read-only"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
