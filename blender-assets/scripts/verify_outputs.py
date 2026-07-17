#!/usr/bin/env python3
"""Verify the plate package without touching the atlas repo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest_path = ROOT / "manifests/island-plates.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plate = manifest["plates"][0]
    png_path = ROOT / plate["raster"]
    preview_path = ROOT / plate["preview"]
    blend_path = ROOT / plate["source_blend"]
    geometry_path = ROOT / plate["coastline"]

    image = Image.open(png_path).convert("RGBA")
    assert list(image.size) == plate["pixel_size"] == [2048, 2048]
    alpha = image.getchannel("A")
    assert alpha.getbbox() is not None, "plate is fully transparent"
    assert alpha.getextrema() == (0, 255), "plate needs transparent exterior and opaque interior"

    west, north = plate["coordinates"][0]
    east, south = plate["coordinates"][2]
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    ring = geometry["features"][0]["geometry"]["coordinates"][0]
    projected = [
        ((lng - west) / (east - west) * image.width,
         (north - lat) / (north - south) * image.height)
        for lng, lat in ring
    ]
    expected = Image.new("L", image.size, 0)
    ImageDraw.Draw(expected).polygon(projected, fill=255)
    expected_one_px = expected.filter(ImageFilter.MaxFilter(3))
    actual = alpha.point(lambda value: 255 if value > 64 else 0)
    outside = ImageChops.subtract(actual, expected_one_px)
    assert outside.getbbox() is None, "visible alpha escapes the coastline by more than one pixel"

    build = manifest["build"]
    assert sha256_file(png_path) == build["raster_sha256"]
    assert sha256_file(preview_path) == build["preview_sha256"]
    assert sha256_file(blend_path) == build["blend_sha256"]
    assert manifest["repo_write_contract"] == "read-only"
    assert manifest["integration_status"].startswith("asset-only")

    print("PASS fish-man-island")
    print(f"  plate: {image.width}x{image.height} RGBA")
    print(f"  alpha bbox: {alpha.getbbox()}")
    print("  coastline: within one antialias pixel")
    print(f"  raster sha256: {build['raster_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
