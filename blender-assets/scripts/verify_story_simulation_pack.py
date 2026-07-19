#!/usr/bin/env python3
"""Verify a generic story-simulation pack and write signed manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/story-simulations/story-simulation.schema.json"
INDEX_PATH = ROOT / "manifests/story-simulation-index.json"


def read(path: Path):
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def record(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}


def verify_png(path: Path, expected_size: tuple[int, int] | None = None) -> tuple[int, int]:
    assert path.is_file(), f"Missing PNG: {path}"
    with Image.open(path) as image:
        assert image.format == "PNG", path
        assert image.mode == "RGBA", f"Expected RGBA: {path}"
        if expected_size:
            assert image.size == expected_size, f"Unexpected dimensions: {path} {image.size}"
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255), f"Alpha range failure: {path}"
        bbox = alpha.point(lambda value: 255 if value >= 12 else 0).getbbox()
        assert bbox is not None, f"Empty image: {path}"
        coverage = sum(value >= 12 for value in alpha.get_flattened_data()) / (image.width * image.height)
        assert 0.005 < coverage < 0.92, f"Implausible alpha coverage {coverage:.3f}: {path}"
        return image.size


def video_duration(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def update_index(pack_manifest: dict, manifest_path: Path):
    index = read(INDEX_PATH) if INDEX_PATH.exists() else {"schema_version": 1, "packs": []}
    entry = {
        "id": pack_manifest["id"],
        "chapter_span": pack_manifest["chapter_span"],
        "state": pack_manifest["state"],
        "integration_ready": pack_manifest["integration_ready"],
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": sha256(manifest_path),
    }
    index["packs"] = sorted(
        [current for current in index["packs"] if current["id"] != entry["id"]] + [entry],
        key=lambda current: (current["chapter_span"]["start"], current["id"]),
    )
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--canon-intake", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--web-proof")
    args = parser.parse_args()

    config_path = ROOT / args.config
    contract_path = ROOT / args.contract
    canon_intake_path = ROOT / args.canon_intake
    provenance_path = ROOT / args.provenance
    web_proof_path = ROOT / args.web_proof if args.web_proof else None
    schema = read(SCHEMA_PATH)
    config = read(config_path)
    contract = read(contract_path)
    canon_intake = read(canon_intake_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda error: list(error.path))
    assert not errors, [error.message for error in errors]

    pack_id = contract["id"]
    assert config["pack_id"] == canon_intake["pack_id"] == pack_id
    index_path = ROOT / "runtime/story-simulations" / pack_id / "character-index.json"
    index = read(index_path)
    assert index["pack_id"] == pack_id
    assert index["character_count"] == len(index["characters"]) == len(config["characters"])
    character_by_id = {entry["id"]: entry for entry in index["characters"]}
    assert len(character_by_id) == len(index["characters"])

    atlas_records = []
    total_atlas_bytes = 0
    total_poses = 0
    pose_root = config_path.parent / "characters"
    config_by_id = {entry["id"]: entry for entry in config["characters"]}
    for entry in index["characters"]:
        configured = config_by_id[entry["id"]]
        source_path = ROOT / configured["source_sheet"]
        keyed_path = ROOT / configured["keyed_sheet"]
        assert source_path.is_file() and keyed_path.is_file()
        with Image.open(source_path) as source:
            source_size = source.size
            assert source.format == "PNG"
            assert source.width % config["grid"]["columns"] == 0
            assert source.height % config["grid"]["rows"] == 0
            assert source.width >= 768 and source.height >= 768
        verify_png(keyed_path, source_size)
        metadata_path = ROOT / entry["metadata"]
        atlas_path = ROOT / entry["atlas"]
        metadata = read(metadata_path)
        assert metadata["pack_id"] == pack_id and metadata["id"] == entry["id"]
        verify_png(atlas_path, (1152, 768))
        assert sha256(atlas_path) == entry["atlas_sha256"] == metadata["atlas_sha256"]
        assert len(metadata["frames"]) == len(entry["poses"]) == 6
        for pose in entry["poses"]:
            assert pose in metadata["frames"]
            verify_png(pose_root / entry["id"] / "poses" / f"{pose}.png", (384, 384))
            total_poses += 1
        total_atlas_bytes += atlas_path.stat().st_size
        atlas_records.append(
            {
                "id": entry["id"],
                "kind": entry["kind"],
                "variant": entry["variant"],
                "source": record(source_path),
                "keyed_source": record(keyed_path),
                "atlas": record(atlas_path),
                "metadata": record(metadata_path),
                "pose_count": len(entry["poses"]),
            }
        )

    scene_ids = set()
    runtime_ready = 0
    partial = 0
    actor_tracks = 0
    keyframes = 0
    events = 0
    research_by_id = {scene["id"]: scene for scene in canon_intake["scenes"]}
    for scene in contract["scenes"]:
        assert scene["id"] not in scene_ids
        scene_ids.add(scene["id"])
        assert scene["id"] in research_by_id, f"Missing canon intake for {scene['id']}"
        research = research_by_id[scene["id"]]
        gate = scene["chapter_gate"]
        assert research["status"] == "chapter_verified"
        assert gate["verification"] == "verified"
        assert gate["start"] == research["chapter_gate"]["start"]
        assert gate["end"] == research["chapter_gate"]["end"]
        assert gate["source_url"].startswith("https://")
        if scene["readiness"] == "runtime_ready":
            runtime_ready += 1
            assert not scene.get("missing_assets")
        else:
            partial += 1
            assert scene.get("missing_assets") or scene["readiness"] == "research_hold"
        for actor in scene["actors"]:
            actor_tracks += 1
            assert actor["asset_id"] in character_by_id, f"Unknown asset {actor['asset_id']}"
            poses = set(character_by_id[actor["asset_id"]]["poses"])
            times = [frame["t"] for frame in actor["keyframes"]]
            assert times == sorted(times) and len(times) == len(set(times))
            assert all(0 <= time <= scene["duration_ms"] for time in times)
            for frame in actor["keyframes"]:
                assert frame["pose"] in poses, f"Unknown pose {actor['asset_id']}:{frame['pose']}"
                keyframes += 1
        for event in scene["events"]:
            assert 0 <= event["t"] <= scene["duration_ms"]
            assert event["t"] + event["duration_ms"] <= scene["duration_ms"] + 1000
            events += 1

    review_root = ROOT / "renders/story-simulations" / pack_id
    review_files = [
        review_root / "character-atlas-catalog.png",
        review_root / "scene-board.png",
        review_root / "sampler-poster.png",
        review_root / "sampler.mp4",
    ]
    for path in review_files:
        assert path.is_file(), path
    duration = video_duration(review_files[-1])
    expected_duration = len(contract["scenes"]) * 2.0
    if duration is not None:
        assert abs(duration - expected_duration) < 0.1, (duration, expected_duration)

    web_proof_record = None
    if web_proof_path:
        proof = read(web_proof_path)
        assert proof["pack_id"] == pack_id
        assert proof["status"] == "passed"
        assert proof["runtime_scenes"] == len(contract["scenes"])
        assert proof["artifact_checks"]["passed"] == proof["artifact_checks"]["total"] >= 14
        browser_audit = proof.get("browser_audit") or proof.get("arabasta_browser_audit")
        assert browser_audit is not None
        assert browser_audit["passed"] == browser_audit["total"] >= 12
        assert proof["east_blue_regression_audit"]["passed"] == proof["east_blue_regression_audit"]["total"] >= 12
        assert proof["production_build"] == "passed"
        web_proof_record = record(web_proof_path)

    manifest = {
        "schema_version": 1,
        "id": pack_id,
        "state": "runtime_verified",
        "integration_ready": web_proof_record is not None,
        "supersedes_visible_art": contract.get("supersedes_visible_art", []),
        "chapter_span": contract["chapter_span"],
        "representation": contract["representation"],
        "contract": record(contract_path),
        "character_index": record(index_path),
        "canon_intake": record(canon_intake_path),
        "provenance": record(provenance_path),
        "metrics": {
            "character_packages": len(atlas_records),
            "pose_frames": total_poses,
            "atlas_bytes": total_atlas_bytes,
            "scenes": len(contract["scenes"]),
            "runtime_ready_scenes": runtime_ready,
            "non_ready_scenes": partial,
            "actor_tracks": actor_tracks,
            "movement_keyframes": keyframes,
            "fx_events": events,
            "review_video_seconds": duration,
        },
        "characters": atlas_records,
        "reviews": [record(path) for path in review_files],
        "web_proof": web_proof_record,
        "blockers": [] if web_proof_record else [
            "The pack requires a real-map browser proof before promotion."
        ],
    }
    manifest_path = ROOT / "manifests/story-simulations" / f"{pack_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    update_index(manifest, manifest_path)
    print(
        f"{pack_id} verified: {len(atlas_records)} actors, {total_poses} poses, "
        f"{runtime_ready}/{len(contract['scenes'])} ready scenes, {total_atlas_bytes:,} atlas bytes"
    )
    print(manifest_path.relative_to(ROOT))
    print(INDEX_PATH.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
