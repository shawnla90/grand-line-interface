#!/usr/bin/env python3
"""Validate choreography-only edits and refresh their signed manifest receipt.

Pose art, review media, provenance, and browser proof records are not rewritten.
This command is for deterministic keyframe/FX changes after a pack has already
passed the full asset verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def verify_record(entry: dict, label: str, *, allow_factory_only: bool = False) -> None:
    path = ROOT / entry["path"]
    if allow_factory_only and not path.is_file():
        return
    assert path.is_file(), f"{label}: missing {entry['path']}"
    assert path.stat().st_size == entry["bytes"], f"{label}: byte mismatch"
    assert sha256(path) == entry["sha256"], f"{label}: sha256 mismatch"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True, help="east-blue-saga-2d or a story pack id")
    args = parser.parse_args()

    east_blue = args.pack == "east-blue-saga-2d"
    if east_blue:
        manifest_path = ROOT / "manifests/east-blue-2d.json"
        schema_path = ROOT / "contracts/east-blue-saga-simulation.schema.json"
    else:
        manifest_path = ROOT / "manifests/story-simulations" / f"{args.pack}.json"
        schema_path = ROOT / "contracts/story-simulations/story-simulation.schema.json"

    manifest = read(manifest_path)
    contract_path = ROOT / manifest["contract"]["path"]
    contract = read(contract_path)
    schema = read(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]
    assert contract["id"] == args.pack

    verify_record(manifest["character_index"], "character index")
    for character in manifest["characters"]:
        verify_record(character["atlas"], f"{character['id']} atlas")
        verify_record(character["metadata"], f"{character['id']} metadata")
    for review in manifest["reviews"]:
        # East Blue review media remains in the declared story-art factory;
        # choreography promotion does not copy or re-sign those bytes.
        verify_record(review, "review", allow_factory_only=True)
    if manifest.get("web_proof"):
        verify_record(manifest["web_proof"], "web proof")

    character_index = read(ROOT / manifest["character_index"]["path"])
    poses = {character["id"]: set(character["poses"]) for character in character_index["characters"]}
    scene_ids: set[str] = set()
    ready = 0
    not_ready = 0
    actor_tracks = 0
    movement_keyframes = 0
    fx_events = 0

    for scene in contract["scenes"]:
        assert scene["id"] not in scene_ids, f"duplicate scene {scene['id']}"
        scene_ids.add(scene["id"])
        gate = scene["chapter_gate"]
        assert gate["verification"] == "verified"
        assert contract["chapter_span"]["start"] <= gate["start"] <= gate["end"] <= contract["chapter_span"]["end"]
        if scene["readiness"] == "runtime_ready":
            ready += 1
        else:
            not_ready += 1
        for actor in scene["actors"]:
            actor_tracks += 1
            assert actor["asset_id"] in poses, f"unknown asset {actor['asset_id']}"
            times = [keyframe["t"] for keyframe in actor["keyframes"]]
            assert times == sorted(set(times)), f"{scene['id']}:{actor['id']} keyframes are not strictly ascending"
            assert all(0 <= time <= scene["duration_ms"] for time in times)
            assert all(keyframe["pose"] in poses[actor["asset_id"]] for keyframe in actor["keyframes"])
            movement_keyframes += len(actor["keyframes"])
        for event in scene.get("events", []):
            assert 0 <= event["t"] <= scene["duration_ms"]
            fx_events += 1

    manifest["contract"] = record(contract_path)
    manifest["metrics"].update(
        {
            "scenes": len(contract["scenes"]),
            "runtime_ready_scenes": ready,
            ("art_partial_scenes" if east_blue else "non_ready_scenes"): not_ready,
            "actor_tracks": actor_tracks,
            "movement_keyframes": movement_keyframes,
            "fx_events": fx_events,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if not east_blue:
        index_path = ROOT / "manifests/story-simulation-index.json"
        index = read(index_path)
        entry = next(item for item in index["packs"] if item["id"] == args.pack)
        entry["state"] = manifest["state"]
        entry["integration_ready"] = manifest["integration_ready"]
        entry["manifest_sha256"] = sha256(manifest_path)
        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    print(
        f"{args.pack}: {len(contract['scenes'])} scenes, {actor_tracks} actor tracks, "
        f"{movement_keyframes} keyframes, {fx_events} FX; manifest receipt refreshed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
