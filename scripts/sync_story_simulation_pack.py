#!/usr/bin/env python3
"""Promote one signed, runtime-verified story pack into the browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

import story_pack_registry


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "blender-assets"
CANON_JSON = ROOT / "data/canon.json"
ATLAS_W, ATLAS_H = 1152, 768
GRID_COLS, GRID_ROWS, CELL_PX = 3, 2, 384


class DataError(Exception):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_file(entry: dict, what: str) -> Path:
    path = ASSETS / entry["path"]
    if not path.exists():
        raise DataError(f"{what}: file missing: {entry['path']}")
    if path.stat().st_size != entry["bytes"]:
        raise DataError(f"{what}: byte count disagrees with the manifest: {entry['path']}")
    if sha256(path) != entry["sha256"]:
        raise DataError(f"{what}: sha256 disagrees with the manifest: {entry['path']}")
    return path


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise DataError(f"{path.name} is not a PNG")
    return struct.unpack(">II", data[16:24])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    args = parser.parse_args()
    pack_id = args.pack

    manifest_path = ASSETS / "manifests/story-simulations" / f"{pack_id}.json"
    anchor_path = ROOT / "canon/story_scene_anchors" / f"{pack_id}.json"
    if not manifest_path.is_file():
        raise DataError(f"unknown story pack {pack_id!r}: {manifest_path.relative_to(ROOT)} is missing")
    if not anchor_path.is_file():
        raise DataError(f"{pack_id}: app-owned anchor table is missing")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("id") != pack_id:
        raise DataError(f"{pack_id}: manifest identity/schema mismatch")
    if manifest.get("state") != "runtime_verified":
        raise DataError(f"{pack_id}: manifest state is not runtime_verified")

    contract_path = signed_file(manifest["contract"], "contract")
    signed_file(manifest["character_index"], "character_index")
    contract = json.loads(contract_path.read_text())
    if contract.get("schema_version") != 1 or contract.get("id") != pack_id:
        raise DataError(f"{pack_id}: contract identity/schema mismatch")

    output_dir = ROOT / "public/art/story-simulations" / pack_id
    output_json = ROOT / "data/generated/story_simulations" / f"{pack_id}.json"
    assets: dict[str, dict] = {}
    atlas_sources: dict[str, Path] = {}
    for character in manifest["characters"]:
        character_id = character["id"]
        atlas_path = signed_file(character["atlas"], f"characters[{character_id}].atlas")
        metadata_path = signed_file(character["metadata"], f"characters[{character_id}].metadata")
        if png_size(atlas_path) != (ATLAS_W, ATLAS_H):
            raise DataError(f"{character_id}: atlas is not {ATLAS_W}x{ATLAS_H}")
        metadata = json.loads(metadata_path.read_text())
        grid = metadata.get("grid") or {}
        if (grid.get("columns"), grid.get("rows"), grid.get("cell_px")) != (GRID_COLS, GRID_ROWS, CELL_PX):
            raise DataError(f"{character_id}: atlas grid disagrees with the runtime contract")
        if metadata.get("atlas_sha256") != character["atlas"]["sha256"]:
            raise DataError(f"{character_id}: metadata atlas hash disagrees with the manifest")
        frames = {}
        for pose, frame in metadata["frames"].items():
            col, row = frame["index"] % GRID_COLS, frame["index"] // GRID_COLS
            if (frame["pixel_rect"]["x"], frame["pixel_rect"]["y"]) != (col * CELL_PX, row * CELL_PX):
                raise DataError(f"{character_id}:{pose}: frame index and pixel rectangle disagree")
            frames[pose] = {"col": col, "row": row, "pivot": frame["pivot"]}
        assets[character_id] = {
            "url": f"/art/story-simulations/{pack_id}/{character_id}/atlas.png",
            "sha256": character["atlas"]["sha256"],
            "kind": character["kind"],
            "variant": character["variant"],
            "map_height": metadata["map_height"],
            "grid": {"columns": GRID_COLS, "rows": GRID_ROWS, "cell_px": CELL_PX},
            "frames": frames,
            "runtime_rules": metadata.get("runtime_rules") or {},
        }
        atlas_sources[character_id] = atlas_path

    anchor_file = json.loads(anchor_path.read_text())
    if anchor_file.get("pack_id") != pack_id:
        raise DataError(f"{pack_id}: anchor table identity mismatch")
    anchors = anchor_file["anchors"]
    canon = json.loads(CANON_JSON.read_text())
    event_positions = {event["slug"]: (event["lng"], event["lat"]) for event in canon["events"]}
    island_positions = {
        island["slug"]: (island["lng"], island["lat"])
        for island in canon["islands"]
        if isinstance(island.get("lng"), (int, float)) and isinstance(island.get("lat"), (int, float))
    }

    def resolve_anchor(scene_id: str) -> dict:
        anchor = anchors.get(scene_id)
        if anchor is None:
            raise DataError(f"{scene_id}: shipped scene has no app-owned anchor")
        note = anchor.get("note")
        if "event" in anchor:
            if anchor["event"] not in event_positions:
                raise DataError(f"{scene_id}: anchor event is absent from canon")
            lng, lat = event_positions[anchor["event"]]
            return {"kind": "event", "ref": anchor["event"], "lng": lng, "lat": lat, "note": note}
        if "island" in anchor:
            if anchor["island"] not in island_positions:
                raise DataError(f"{scene_id}: anchor island has no canon coordinate")
            lng, lat = island_positions[anchor["island"]]
            return {"kind": "island", "ref": anchor["island"], "lng": lng, "lat": lat, "note": note}
        if not isinstance(anchor.get("lng"), (int, float)) or not isinstance(anchor.get("lat"), (int, float)):
            raise DataError(f"{scene_id}: invalid literal anchor")
        return {"kind": "literal", "ref": None, "lng": anchor["lng"], "lat": anchor["lat"], "note": note}

    scenes, refused = [], []
    for scene in contract["scenes"]:
        scene_id = scene["id"]
        if scene.get("readiness") != "runtime_ready":
            refused.append(
                {
                    "id": scene_id,
                    "readiness": scene.get("readiness"),
                    "why": f"readiness is {scene.get('readiness')!r}, not runtime_ready",
                    "missing_assets": scene.get("missing_assets") or [],
                }
            )
            continue
        gate = scene.get("chapter_gate") or {}
        start, end = gate.get("start"), gate.get("end")
        span = contract["chapter_span"]
        if gate.get("verification") != "verified":
            raise DataError(f"{scene_id}: runtime-ready scene has an unverified gate")
        if not (isinstance(start, int) and isinstance(end, int) and span["start"] <= start <= end <= span["end"]):
            raise DataError(f"{scene_id}: gate is outside the pack span")
        for actor in scene["actors"]:
            asset = assets.get(actor["asset_id"])
            if asset is None:
                raise DataError(f"{scene_id}: unknown actor asset {actor['asset_id']!r}")
            last_t = -1
            for keyframe in actor["keyframes"]:
                if keyframe["t"] <= last_t or keyframe["t"] > scene["duration_ms"]:
                    raise DataError(f"{scene_id}:{actor['id']}: invalid keyframe time {keyframe['t']}")
                if keyframe["pose"] not in asset["frames"]:
                    raise DataError(f"{scene_id}:{actor['id']}: unknown pose {keyframe['pose']!r}")
                last_t = keyframe["t"]
        for event in scene.get("events") or []:
            if not 0 <= event["t"] <= scene["duration_ms"]:
                raise DataError(f"{scene_id}: FX event is outside the duration")
        row = {
            key: scene[key]
            for key in (
                "id", "label", "arc_id", "type", "priority", "chapter_gate",
                "place", "duration_ms", "actors", "events",
            )
        }
        if scene.get("visual_treatment") is not None:
            row["visual_treatment"] = scene["visual_treatment"]
        row["anchor"] = resolve_anchor(scene_id)
        scenes.append(row)

    metrics = manifest["metrics"]
    if len(scenes) != metrics["runtime_ready_scenes"] or len(refused) != metrics["non_ready_scenes"]:
        raise DataError(f"{pack_id}: scene readiness split disagrees with the signed manifest")

    output_dir.mkdir(parents=True, exist_ok=True)
    for character_id, source in atlas_sources.items():
        destination = output_dir / character_id / "atlas.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    payload = {
        "_meta": {
            "generator": "scripts/sync_story_simulation_pack.py",
            "schema_version": contract["schema_version"],
            "pack_id": pack_id,
            "chapter_span": contract["chapter_span"],
            "source_manifest_sha256": sha256(manifest_path),
            "integration_ready": manifest.get("integration_ready", False),
            "feature_flag": "NEXT_PUBLIC_STORY_SIMULATION_PACKS",
            "note": "Only runtime-ready scenes with verified chapter gates ship; the new pack remains disabled unless explicitly allowlisted.",
            "counts": {"scenes": len(scenes), "refused": len(refused), "assets": len(assets)},
        },
        "arcs": contract["arcs"],
        "runtime_policy": contract["runtime_policy"],
        "scenes": scenes,
        "refused": refused,
        "assets": assets,
        "supersedes_visible_art": manifest.get("supersedes_visible_art") or [],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    for scene in scenes:
        gate = scene["chapter_gate"]
        print(f"  scene {scene['id']:42} ch {gate['start']:>3}-{gate['end']:<3} {len(scene['actors'])} actors {len(scene['events'])} fx")
    print(f"\n{len(scenes)} scenes, {len(refused)} refused, {len(assets)} atlases -> {output_json.relative_to(ROOT)}")
    if story_pack_registry.emit():
        print(f"registry re-emitted -> {story_pack_registry.REGISTRY_TS.relative_to(ROOT)}")
    if not manifest.get("integration_ready"):
        print("pack is runtime_verified but disabled by default pending the real-map browser proof")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DataError as error:
        print(f"\nsync_story_simulation_pack: {error}\n", file=sys.stderr)
        raise SystemExit(1)
