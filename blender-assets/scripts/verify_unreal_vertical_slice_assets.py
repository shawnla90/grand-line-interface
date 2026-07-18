#!/usr/bin/env python3
"""Verify hashes, GLB structure, node anchors, and prototype rights metadata."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/unreal-vertical-slice-assets.json"


class VerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(f"Unsafe manifest path: {value}")
    return ROOT / relative


def glb_json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if len(payload) < 20:
        raise VerificationError(f"Truncated GLB: {path}")
    magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(payload):
        raise VerificationError(f"Invalid GLB header: {path}")
    chunk_length, chunk_type = struct.unpack_from("<II", payload, 12)
    if chunk_type != 0x4E4F534A:
        raise VerificationError(f"First GLB chunk is not JSON: {path}")
    return json.loads(payload[20:20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\x00"))


def main() -> int:
    manifest = read_json(MANIFEST)
    if manifest.get("schema_version") != 1:
        raise VerificationError("Unsupported vertical-slice manifest")
    ids: set[str] = set()
    total_anchors = 0
    for asset in manifest.get("assets", []):
        asset_id = asset.get("id")
        if not asset_id or asset_id in ids:
            raise VerificationError(f"Missing or duplicate asset id: {asset_id}")
        ids.add(asset_id)
        if asset.get("maturity") != "unreal_vertical_slice_blockout_v1":
            raise VerificationError(f"Unexpected maturity: {asset_id}")
        rights = asset.get("rights", {})
        if not rights.get("original_prototype_geometry"):
            raise VerificationError(f"Asset is not marked as original: {asset_id}")
        if rights.get("franchise_logos_included") or rights.get("exact_production_mesh_copy"):
            raise VerificationError(f"Unsafe rights metadata: {asset_id}")
        for path_key, hash_key in (
            ("runtime_glb", "glb_sha256"),
            ("source_blend", "source_sha256"),
            ("preview", "preview_sha256"),
        ):
            path = safe_path(asset[path_key])
            if not path.is_file() or sha256_file(path) != asset["build"][hash_key]:
                raise VerificationError(f"Missing or drifted {path_key}: {asset_id}")
        gltf = glb_json(safe_path(asset["runtime_glb"]))
        exported_anchors = {
            node.get("name")
            for node in gltf.get("nodes", [])
            if node.get("extras", {}).get("runtime_role") == "anchor"
        }
        required_anchors = set(asset.get("anchors", []))
        if exported_anchors != required_anchors:
            raise VerificationError(
                f"Anchor mismatch for {asset_id}: exported={sorted(exported_anchors)}, "
                f"required={sorted(required_anchors)}"
            )
        if asset["stats"]["anchors"] != len(required_anchors):
            raise VerificationError(f"Anchor metric drift: {asset_id}")
        if asset["stats"]["bytes"] != safe_path(asset["runtime_glb"]).stat().st_size:
            raise VerificationError(f"Byte metric drift: {asset_id}")
        total_anchors += len(required_anchors)
    expected_ids = {"baratie-encounter-deck", "east-blue-original-ship-proxy"}
    if ids != expected_ids:
        raise VerificationError(f"Unexpected asset set: {sorted(ids)}")
    print(f"Verified Unreal vertical-slice assets: {len(ids)} GLBs, {total_anchors} anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
