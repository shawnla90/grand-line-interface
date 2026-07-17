#!/usr/bin/env python3
"""Validate runtime GLB containers, hashes, budgets, and registry entries."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("skypiea-knock-up-stream", "wano-waterfall-ascent")
MAX_BYTES = 6 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    registry = json.loads((ROOT / "manifests/runtime-3d.json").read_text(encoding="utf-8"))
    by_id = {model["id"]: model for model in registry["models"]}
    for model_id in TARGETS:
        model = by_id[model_id]
        path = ROOT / model["glb"]
        with path.open("rb") as handle:
            magic, version, declared = struct.unpack("<4sII", handle.read(12))
        assert magic == b"glTF" and version == 2
        assert declared == path.stat().st_size
        assert path.stat().st_size < MAX_BYTES
        assert sha256_file(path) == model["build"]["glb_sha256"]
        assert model["runtime_policy"]["ship_motion_owner"].startswith("atlas runtime")
        print(f"PASS {model_id}: {path.stat().st_size / 1024:.1f} KiB, glTF 2.0")
    assert registry["feature_flag"] == "NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
