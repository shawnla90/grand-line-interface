#!/usr/bin/env python3
"""Validate every runtime GLB, fallback, hash, queue gate, and spoiler rule."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 6 * 1024 * 1024
EXPECTED = {
    "skypiea-knock-up-stream", "wano-waterfall-ascent", "fish-man-island",
    "totto-land", "world-government-tarai-system", "conomi-arlong-park",
    "arabasta-kingdom", "cactus-island-whisky-peak", "dressrosa-green-bit",
    "zou-zunesha", "amazon-lily", "mary-geoise-red-line",
    "sabaody-grove-network", "skypiea-sky-system",
    "loguetown-roger-execution", "water-7-sea-train-network",
}
STUDIES = {"whole-cake-island", "impel-down", "sabaody-archipelago"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        magic, version, declared = struct.unpack("<4sII", handle.read(12))
        assert magic == b"glTF" and version == 2
        assert declared == path.stat().st_size
        length, chunk_type = struct.unpack("<II", handle.read(8))
        assert chunk_type == 0x4E4F534A
        return json.loads(handle.read(length).decode("utf-8").rstrip(" \t\r\n\x00"))


def png_alpha(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:26]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    assert data[25] in {4, 6}, f"{path}: PNG is not grayscale/RGBA alpha"
    return width, height


def main() -> int:
    registry = json.loads((ROOT / "manifests/runtime-3d.json").read_text(encoding="utf-8"))
    by_id = {model["id"]: model for model in registry["models"]}
    assert set(by_id) == EXPECTED
    assert registry["schema_version"] == 2
    assert registry["counts"] == {"models": 16, "transitions": 2, "runtime_scenes": 14}

    gltf_docs = {}
    for model_id in sorted(EXPECTED):
        model = by_id[model_id]
        path = ROOT / model["glb"]
        assert path.stat().st_size < MAX_BYTES
        assert sha(path) == model["build"]["glb_sha256"]
        doc = glb_json(path)
        gltf_docs[model_id] = doc
        fallback = ROOT / model["fallback"]["path"]
        assert sha(fallback) == model["fallback"]["sha256"]
        assert list(png_alpha(fallback)) == model["fallback"]["pixel_size"]
        for gate in (model.get("integration") or {}).get("component_gates", []):
            if gate.get("verification") == "chapter_to_verify":
                assert gate.get("reveal_chapter") is None
                assert gate.get("default_hidden") is True
        print(f"PASS {model_id:34} {path.stat().st_size / 1024:7.1f} KiB")

    # Procedural scenes export component-aware glTF extras for the app loader.
    for model_id in {
        "totto-land", "world-government-tarai-system", "conomi-arlong-park",
        "arabasta-kingdom", "cactus-island-whisky-peak", "dressrosa-green-bit",
        "zou-zunesha", "amazon-lily", "mary-geoise-red-line",
        "sabaody-grove-network", "skypiea-sky-system",
    }:
        assert any((node.get("extras") or {}).get("component_id")
                   for node in gltf_docs[model_id].get("nodes", [])), model_id

    totto = by_id["totto-land"]
    assert len(totto["integration"]["component_gates"]) == 36  # 35 islands + chateau
    assert any(x["verification"] == "chapter_to_verify" for x in totto["integration"]["component_gates"])
    sabaody_names = [node.get("name", "") for node in gltf_docs["sabaody-grove-network"].get("nodes", [])]
    assert len([name for name in sabaody_names if name.startswith("Grove ") and name.endswith(" root island")]) == 79
    assert "relational_triangle" in by_id["world-government-tarai-system"]["integration"]["layout_status"]
    assert by_id["zou-zunesha"]["integration"]["anchor_policy"].startswith("moving_entity")

    queue = json.loads((ROOT / "queue/asset-requests.json").read_text(encoding="utf-8"))
    queued = {x["id"]: x for x in queue["assets"]}
    for model_id in EXPECTED:
        assert queued[model_id]["state"] == "integration_ready"
    for study in STUDIES:
        assert queued[study]["state"] == "study_only"
    print("16 runtime GLBs and fallbacks verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
