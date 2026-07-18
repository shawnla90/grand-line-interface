#!/usr/bin/env python3
"""Verify the East Blue Unreal export bundle without requiring Unreal Engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ASSET_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ASSET_ROOT / "exports/unreal/east-blue-v1"


class VerificationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Invalid JSON: {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_glb_json(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    if len(payload) < 20:
        raise VerificationError(f"Truncated GLB: {path}")
    magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(payload):
        raise VerificationError(f"Invalid GLB: {path}")
    chunk_length, chunk_type = struct.unpack_from("<II", payload, 12)
    if chunk_type != 0x4E4F534A:
        raise VerificationError(f"First GLB chunk is not JSON: {path}")
    return json.loads(payload[20:20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\x00"))


def resolve_bundle_path(bundle: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or "\\" in value:
        raise VerificationError(f"Unsafe or non-POSIX bundle path: {value}")
    resolved = (bundle / relative).resolve()
    if bundle.resolve() not in resolved.parents:
        raise VerificationError(f"Path escapes bundle: {value}")
    return resolved


def verify_checksums(bundle: Path) -> int:
    receipt_path = bundle / "checksums.sha256"
    if not receipt_path.is_file():
        raise VerificationError("Missing checksums.sha256")
    expected_paths: set[str] = set()
    for line in receipt_path.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ")
        if not separator or len(digest) != 64 or relative in expected_paths:
            raise VerificationError(f"Malformed or duplicate checksum line: {line}")
        path = resolve_bundle_path(bundle, relative)
        if not path.is_file() or path.is_symlink():
            raise VerificationError(f"Missing or linked checksummed file: {relative}")
        actual = sha256_file(path)
        if actual != digest:
            raise VerificationError(f"Checksum drift: {relative}")
        expected_paths.add(relative)
    actual_paths = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    if actual_paths != expected_paths:
        missing = sorted(actual_paths - expected_paths)
        stale = sorted(expected_paths - actual_paths)
        raise VerificationError(f"Checksum coverage mismatch: missing={missing}, stale={stale}")
    return len(expected_paths)


def verify_bundle(bundle: Path) -> dict[str, int]:
    if not bundle.is_dir():
        raise VerificationError(f"Bundle is missing: {bundle}")
    if any(path.is_symlink() for path in bundle.rglob("*")):
        raise VerificationError("Bundle may not contain symbolic links")
    checksummed_files = verify_checksums(bundle)
    manifest = read_json(bundle / "bundle-manifest.json")
    contract = read_json(resolve_bundle_path(bundle, manifest["contract"]["path"]))
    if manifest.get("schema_version") != 1 or manifest.get("id") != "grand-line-unreal-east-blue-v1":
        raise VerificationError("Unsupported bundle manifest")
    if sha256_file(resolve_bundle_path(bundle, manifest["contract"]["path"])) != manifest[
        "contract"
    ]["sha256"]:
        raise VerificationError("Contract receipt mismatch")

    scenes = contract.get("scenes", [])
    scene_ids = [scene.get("id") for scene in scenes]
    if len(scene_ids) != len(set(scene_ids)):
        raise VerificationError("Duplicate runnable scene ids")
    if any(scene.get("readiness") != "runtime_ready" for scene in scenes):
        raise VerificationError("Non-runtime-ready scene exported as runnable")
    if any(
        scene.get("chapter_gate", {}).get("verification") != "verified" for scene in scenes
    ):
        raise VerificationError("Unverified chapter gate exported as runnable")

    character_frames: dict[str, set[str]] = {}
    for character in manifest.get("characters", []):
        character_id = character["id"]
        atlas = resolve_bundle_path(bundle, character["atlas"])
        metadata_path = resolve_bundle_path(bundle, character["metadata"])
        metadata = read_json(metadata_path)
        if not atlas.is_file() or atlas.stat().st_size < 8:
            raise VerificationError(f"Invalid atlas: {character_id}")
        if atlas.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise VerificationError(f"Atlas is not PNG: {character_id}")
        if metadata.get("id") != character_id:
            raise VerificationError(f"Metadata id mismatch: {character_id}")
        frames = set(metadata.get("frames", {}))
        if len(frames) != character.get("pose_count"):
            raise VerificationError(f"Pose count mismatch: {character_id}")
        character_frames[character_id] = frames

    for scene in scenes:
        for actor in scene.get("actors", []):
            asset_id = actor.get("asset_id")
            if asset_id not in character_frames:
                raise VerificationError(f"Missing actor asset: {asset_id}")
            for keyframe in actor.get("keyframes", []):
                pose = keyframe.get("pose")
                if pose not in character_frames[asset_id]:
                    raise VerificationError(
                        f"Unknown pose {pose!r} for {asset_id} in {scene['id']}"
                    )

    for model in manifest.get("environments", []) + manifest.get("vehicles", []):
        path = resolve_bundle_path(bundle, model["path"])
        with path.open("rb") as handle:
            header = handle.read(12)
        if len(header) != 12:
            raise VerificationError(f"Truncated GLB: {model['id']}")
        magic, version, declared_length = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2 or declared_length != path.stat().st_size:
            raise VerificationError(f"Invalid GLB: {model['id']}")
        if sha256_file(path) != model["sha256"]:
            raise VerificationError(f"GLB receipt mismatch: {model['id']}")
        if model.get("anchors"):
            gltf = read_glb_json(path)
            exported_anchors = {
                node.get("name")
                for node in gltf.get("nodes", [])
                if node.get("extras", {}).get("runtime_role") == "anchor"
            }
            if exported_anchors != set(model["anchors"]):
                raise VerificationError(f"GLB anchor drift: {model['id']}")

    metrics = manifest.get("metrics", {})
    expected = {
        "characters": len(character_frames),
        "poses": sum(len(frames) for frames in character_frames.values()),
        "runnable_scenes": len(scenes),
        "excluded_scenes": len(manifest.get("excluded_scenes", [])),
        "environments": len(manifest.get("environments", [])),
        "vehicles": len(manifest.get("vehicles", [])),
    }
    if metrics != expected:
        raise VerificationError(f"Bundle metrics drift: expected {expected}, found {metrics}")
    if manifest.get("vertical_slice", {}).get("smoke_test_scene_id") not in scene_ids:
        raise VerificationError("Smoke-test scene is not runnable")
    if manifest.get("vertical_slice", {}).get("interactive_scene_id") not in scene_ids:
        raise VerificationError("Interactive scene is not runnable")
    return {**expected, "checksummed_files": checksummed_files}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics = verify_bundle(args.bundle.expanduser().resolve())
    print(
        "Verified Unreal bundle: {characters} characters, {poses} poses, "
        "{runnable_scenes} scenes, {environments} environments, {vehicles} vehicle, "
        "{checksummed_files} checksummed files".format(**metrics)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
