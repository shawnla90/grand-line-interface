#!/usr/bin/env python3
"""Build the deterministic, engine-neutral East Blue bundle for Unreal.

The source manifests remain authoritative. This script only promotes verified,
runtime-ready story scenes and copies already-produced runtime derivatives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
from pathlib import Path
from typing import Any


ASSET_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ASSET_ROOT / "manifests/east-blue-2d.json"
SOURCE_CONTRACT = ASSET_ROOT / "contracts/east-blue-saga.simulation.json"
SOURCE_SCHEMA = ASSET_ROOT / "contracts/east-blue-saga-simulation.schema.json"
RUNTIME_MANIFEST = ASSET_ROOT / "manifests/runtime-3d.json"
VERTICAL_SLICE_MANIFEST = ASSET_ROOT / "manifests/unreal-vertical-slice-assets.json"
DEFAULT_OUTPUT = ASSET_ROOT / "exports/unreal/east-blue-v1"
LOGUETOWN_ENVIRONMENT_ID = "loguetown-roger-execution"


class BundleError(RuntimeError):
    """Raised when a source contract is unsafe or has drifted."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError(f"Cannot read valid JSON: {path}: {exc}") from exc


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_receipt(path: Path, receipt: dict[str, Any], label: str) -> None:
    if not path.is_file():
        raise BundleError(f"Missing {label}: {path}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != receipt.get("bytes"):
        raise BundleError(
            f"{label} byte drift: expected {receipt.get('bytes')}, found {size}: {path}"
        )
    if digest != receipt.get("sha256"):
        raise BundleError(
            f"{label} hash drift: expected {receipt.get('sha256')}, found {digest}: {path}"
        )


def copy_file(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {
        "path": destination.as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def assert_glb(path: Path) -> None:
    with path.open("rb") as handle:
        header = handle.read(12)
    if len(header) != 12:
        raise BundleError(f"Truncated GLB: {path}")
    magic, version, declared_length = struct.unpack("<4sII", header)
    if magic != b"glTF" or version != 2 or declared_length != path.stat().st_size:
        raise BundleError(f"Invalid GLB header or length: {path}")


def ensure_safe_relative(path_value: str, label: str) -> Path:
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        raise BundleError(f"Unsafe {label} path: {path_value}")
    return path


def build_bundle(output: Path) -> dict[str, Any]:
    source_manifest = read_json(SOURCE_MANIFEST)
    source_contract = read_json(SOURCE_CONTRACT)
    runtime_manifest = read_json(RUNTIME_MANIFEST)

    if source_manifest.get("state") != "runtime_verified":
        raise BundleError("East Blue source manifest is not runtime_verified")
    if source_manifest.get("schema_version") != 1 or source_contract.get("schema_version") != 1:
        raise BundleError("Only East Blue schema version 1 is supported")

    validate_receipt(SOURCE_CONTRACT, source_manifest["contract"], "saga contract")
    character_index_path = ASSET_ROOT / ensure_safe_relative(
        source_manifest["character_index"]["path"], "character index"
    )
    validate_receipt(
        character_index_path, source_manifest["character_index"], "character index"
    )

    character_ids: set[str] = set()
    characters: list[dict[str, Any]] = []
    for source_character in source_manifest.get("characters", []):
        character_id = source_character.get("id")
        if not character_id or character_id in character_ids:
            raise BundleError(f"Missing or duplicate character id: {character_id!r}")
        character_ids.add(character_id)

        source_atlas = ASSET_ROOT / ensure_safe_relative(
            source_character["atlas"]["path"], f"{character_id} atlas"
        )
        source_metadata = ASSET_ROOT / ensure_safe_relative(
            source_character["metadata"]["path"], f"{character_id} metadata"
        )
        validate_receipt(source_atlas, source_character["atlas"], f"{character_id} atlas")
        validate_receipt(
            source_metadata, source_character["metadata"], f"{character_id} metadata"
        )
        metadata = read_json(source_metadata)
        if metadata.get("id") != character_id:
            raise BundleError(f"Character metadata id mismatch: {source_metadata}")
        if len(metadata.get("frames", {})) != source_character.get("pose_count"):
            raise BundleError(f"Pose count drift for {character_id}")

        atlas_destination = output / "characters" / character_id / "atlas.png"
        metadata_destination = output / "characters" / character_id / "character.json"
        copy_file(source_atlas, atlas_destination)
        copy_file(source_metadata, metadata_destination)
        characters.append(
            {
                "id": character_id,
                "kind": source_character["kind"],
                "variant": source_character["variant"],
                "pose_count": source_character["pose_count"],
                "atlas": f"characters/{character_id}/atlas.png",
                "metadata": f"characters/{character_id}/character.json",
                "source_maturity": "runtime_verified",
                "unreal_import_status": "pending",
            }
        )

    ready_scenes: list[dict[str, Any]] = []
    excluded_scenes: list[dict[str, str]] = []
    scene_ids: set[str] = set()
    for scene in source_contract.get("scenes", []):
        scene_id = scene.get("id")
        if not scene_id or scene_id in scene_ids:
            raise BundleError(f"Missing or duplicate scene id: {scene_id!r}")
        scene_ids.add(scene_id)
        gate = scene.get("chapter_gate", {})
        if scene.get("readiness") != "runtime_ready":
            excluded_scenes.append(
                {"id": scene_id, "reason": f"readiness:{scene.get('readiness', 'missing')}"}
            )
            continue
        if gate.get("verification") != "verified":
            raise BundleError(f"Runnable scene has an unverified chapter gate: {scene_id}")
        for actor in scene.get("actors", []):
            asset_id = actor.get("asset_id")
            if asset_id not in character_ids:
                raise BundleError(f"Scene {scene_id} references missing asset {asset_id}")
        ready_scenes.append(scene)

    if len(ready_scenes) != source_manifest["metrics"]["runtime_ready_scenes"]:
        raise BundleError("Runtime-ready scene count drift")
    if len(excluded_scenes) != source_manifest["metrics"]["art_partial_scenes"]:
        raise BundleError("Excluded scene count drift")

    filtered_contract = dict(source_contract)
    filtered_contract["id"] = "east-blue-saga-2d-unreal-v1"
    filtered_contract["source_contract_id"] = source_contract["id"]
    filtered_contract["scenes"] = ready_scenes
    contract_destination = output / "contracts/east-blue-saga.simulation.json"
    contract_destination.parent.mkdir(parents=True, exist_ok=True)
    contract_destination.write_bytes(canonical_json_bytes(filtered_contract))
    schema_destination = output / "contracts/east-blue-saga-simulation.schema.json"
    shutil.copyfile(SOURCE_SCHEMA, schema_destination)

    environments: list[dict[str, Any]] = []
    vehicles: list[dict[str, Any]] = []
    runtime_models = {model["id"]: model for model in runtime_manifest.get("models", [])}
    source_environment = runtime_models.get(LOGUETOWN_ENVIRONMENT_ID)
    if not source_environment:
        raise BundleError(f"Missing runtime model: {LOGUETOWN_ENVIRONMENT_ID}")
    if source_environment.get("maturity") != "runtime_blockout_v1":
        raise BundleError("Loguetown environment maturity changed")
    source_glb = ASSET_ROOT / ensure_safe_relative(
        source_environment["glb"], "Loguetown GLB"
    )
    assert_glb(source_glb)
    if sha256_file(source_glb) != source_environment["build"]["glb_sha256"]:
        raise BundleError("Loguetown GLB hash drift")
    environment_destination = output / "environments/loguetown-roger-execution.glb"
    copy_file(source_glb, environment_destination)
    environments.append(
        {
            "id": LOGUETOWN_ENVIRONMENT_ID,
            "path": "environments/loguetown-roger-execution.glb",
            "place_id": "loguetown",
            "scene_ids": ["roger-execution-prologue", "luffy-near-execution"],
            "source_maturity": source_environment["maturity"],
            "unreal_import_status": "pending",
            "sha256": sha256_file(environment_destination),
            "bytes": environment_destination.stat().st_size,
        }
    )

    vertical_slice_manifest = read_json(VERTICAL_SLICE_MANIFEST)
    if vertical_slice_manifest.get("schema_version") != 1:
        raise BundleError("Unsupported Unreal vertical-slice asset manifest")
    vertical_asset_ids: set[str] = set()
    for source_asset in vertical_slice_manifest.get("assets", []):
        asset_id = source_asset.get("id")
        kind = source_asset.get("kind")
        if not asset_id or asset_id in vertical_asset_ids:
            raise BundleError(f"Missing or duplicate vertical-slice asset id: {asset_id!r}")
        vertical_asset_ids.add(asset_id)
        if kind not in {"environment", "vehicle"}:
            raise BundleError(f"Unsupported vertical-slice asset kind: {asset_id}: {kind}")
        if source_asset.get("maturity") != "unreal_vertical_slice_blockout_v1":
            raise BundleError(f"Vertical-slice asset is not export-ready: {asset_id}")
        rights = source_asset.get("rights", {})
        if not rights.get("original_prototype_geometry"):
            raise BundleError(f"Vertical-slice asset is not original prototype geometry: {asset_id}")
        if rights.get("franchise_logos_included") or rights.get("exact_production_mesh_copy"):
            raise BundleError(f"Vertical-slice asset has unsafe rights metadata: {asset_id}")
        source_glb = ASSET_ROOT / ensure_safe_relative(
            source_asset["runtime_glb"], f"{asset_id} GLB"
        )
        assert_glb(source_glb)
        if sha256_file(source_glb) != source_asset["build"]["glb_sha256"]:
            raise BundleError(f"Vertical-slice GLB hash drift: {asset_id}")
        folder = "environments" if kind == "environment" else "vehicles"
        destination = output / folder / f"{asset_id}.glb"
        copy_file(source_glb, destination)
        entry = {
            "id": asset_id,
            "path": f"{folder}/{asset_id}.glb",
            "place_id": source_asset["place_id"],
            "scene_ids": source_asset["scene_ids"],
            "anchors": source_asset["anchors"],
            "source_maturity": source_asset["maturity"],
            "unreal_import_status": "pending",
            "sha256": sha256_file(destination),
            "bytes": destination.stat().st_size,
        }
        (environments if kind == "environment" else vehicles).append(entry)
    if vertical_asset_ids != {
        "baratie-encounter-deck",
        "east-blue-original-ship-proxy",
    }:
        raise BundleError(f"Unexpected vertical-slice asset set: {sorted(vertical_asset_ids)}")

    scene_summaries = [
        {
            "id": scene["id"],
            "arc_id": scene["arc_id"],
            "type": scene["type"],
            "place_id": scene["place"]["id"],
            "arena": scene["place"]["arena"],
            "chapter_gate": scene["chapter_gate"],
            "actor_asset_ids": [actor["asset_id"] for actor in scene.get("actors", [])],
            "duration_ms": scene["duration_ms"],
            "source_maturity": "runtime_ready",
            "unreal_import_status": "pending",
        }
        for scene in ready_scenes
    ]

    bundle_manifest = {
        "schema_version": 1,
        "id": "grand-line-unreal-east-blue-v1",
        "source": {
            "asset_factory": "dead-reckoning/blender-assets",
            "manifest": "manifests/east-blue-2d.json",
            "manifest_sha256": sha256_file(SOURCE_MANIFEST),
            "contract": "contracts/east-blue-saga.simulation.json",
            "contract_sha256": sha256_file(SOURCE_CONTRACT),
            "vertical_slice_manifest": "manifests/unreal-vertical-slice-assets.json",
        },
        "contract": {
            "path": "contracts/east-blue-saga.simulation.json",
            "schema": "contracts/east-blue-saga-simulation.schema.json",
            "sha256": sha256_file(contract_destination),
        },
        "rules": {
            "relative_posix_paths_only": True,
            "runtime_ready_scenes_only": True,
            "verified_chapter_gates_only": True,
            "raw_source_sheets_included": False,
            "generated_assets_rebuildable": True,
        },
        "metrics": {
            "characters": len(characters),
            "poses": sum(character["pose_count"] for character in characters),
            "runnable_scenes": len(scene_summaries),
            "excluded_scenes": len(excluded_scenes),
            "environments": len(environments),
            "vehicles": len(vehicles),
        },
        "characters": characters,
        "scenes": scene_summaries,
        "excluded_scenes": excluded_scenes,
        "environments": environments,
        "vehicles": vehicles,
        "vertical_slice": {
            "smoke_test_scene_id": "roger-execution-prologue",
            "interactive_scene_id": "baratie-zoro-vs-mihawk",
            "baratie_environment_status": "source_art_exported",
            "temporary_ship_proxy_status": "source_art_exported",
        },
    }
    manifest_destination = output / "bundle-manifest.json"
    manifest_destination.write_bytes(canonical_json_bytes(bundle_manifest))

    checksums: list[str] = []
    for path in sorted(candidate for candidate in output.rglob("*") if candidate.is_file()):
        relative = path.relative_to(output).as_posix()
        if relative == "checksums.sha256":
            continue
        checksums.append(f"{sha256_file(path)}  {relative}")
    (output / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return bundle_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Bundle destination (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grand-line-unreal-bundle-", dir=output.parent) as temp:
        staging = Path(temp) / output.name
        staging.mkdir()
        manifest = build_bundle(staging)
        if output.exists():
            if output == Path("/") or len(output.parts) < 4:
                raise BundleError(f"Refusing to replace unsafe output path: {output}")
            shutil.rmtree(output)
        staging.rename(output)
    print(
        "Built {id}: {characters} characters, {scenes} runnable scenes, "
        "{environments} environments, {vehicles} vehicle".format(
            id=manifest["id"],
            characters=manifest["metrics"]["characters"],
            scenes=manifest["metrics"]["runnable_scenes"],
            environments=manifest["metrics"]["environments"],
            vehicles=manifest["metrics"]["vehicles"],
        )
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
