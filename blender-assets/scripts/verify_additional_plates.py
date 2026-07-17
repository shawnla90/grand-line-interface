#!/usr/bin/env python3
"""Verify Whole Cake, Impel Down, and Sabaody plate packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("whole-cake-island", "impel-down", "sabaody-archipelago")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def geometry_rings(geometry: dict):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [polygon[0] for polygon in geometry["coordinates"]]
    raise ValueError(geometry["type"])


def main() -> int:
    manifest = json.loads((ROOT / "manifests/island-plates.json").read_text(encoding="utf-8"))
    by_id = {plate["id"]: plate for plate in manifest["plates"]}
    for slug in TARGETS:
        plate = by_id[slug]
        png_path = ROOT / plate["raster"]
        preview_path = ROOT / plate["preview"]
        blend_path = ROOT / plate["source_blend"]
        geometry_path = ROOT / plate["coastline"]
        image = Image.open(png_path).convert("RGBA")
        assert list(image.size) == plate["pixel_size"] == [2048, 2048]
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)

        west, north = plate["coordinates"][0]
        east, south = plate["coordinates"][2]
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))["features"][0]["geometry"]
        expected = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(expected)
        for ring in geometry_rings(geometry):
            projected = [
                ((lng - west) / (east - west) * image.width,
                 (north - lat) / (north - south) * image.height)
                for lng, lat in ring
            ]
            draw.polygon(projected, fill=255)
        tolerance = expected.filter(ImageFilter.MaxFilter(3))
        visible = alpha.point(lambda value: 255 if value > 64 else 0)
        outside = ImageChops.subtract(visible, tolerance)
        assert outside.getbbox() is None, f"{slug}: alpha escapes coastline"
        missing = ImageChops.subtract(expected, alpha.point(lambda value: 255 if value > 2 else 0))
        assert missing.getbbox() is None, f"{slug}: coastline has transparent holes"

        build = plate["build"]
        assert sha256_file(png_path) == build["raster_sha256"]
        assert sha256_file(preview_path) == build["preview_sha256"]
        assert sha256_file(blend_path) == build["blend_sha256"]
        assert sha256_file(geometry_path) == build["geometry_sha256"]
        print(f"PASS {slug}: {geometry['type']}, alpha={alpha.getbbox()}")
    assert manifest["repo_write_contract"] == "read-only"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
