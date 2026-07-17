#!/usr/bin/env python3
"""Join GLB sidecars with vertical-transition integration metadata."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("skypiea-knock-up-stream", "wano-waterfall-ascent")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    transition_manifest = read(ROOT / "manifests/vertical-transitions.json")
    transitions = {item["id"]: item for item in transition_manifest["transitions"]}
    models = []
    for model_id in TARGETS:
        sidecar = read(ROOT / f"runtime/{model_id}.model.json")
        transition = transitions[model_id]
        models.append({
            "id": model_id,
            "glb": f"runtime/{model_id}.glb",
            "fallback_raster": transition["raster"],
            "fallback_preview": transition["preview"],
            "source_blend": transition["source_blend"],
            "integration": transition["integration"],
            "runtime_policy": {
                "default": "fallback_raster",
                "enable_glb_when": "feature flag on, close zoom, supported projection, chapter gate open",
                "unload_when_hidden": True,
                "ship_motion_owner": "atlas runtime; preview proxy is excluded from GLB",
            },
            "stats": sidecar["stats"],
            "build": sidecar["build"],
        })
    registry = {
        "schema_version": 1,
        "asset_class": "maplibre-runtime-3d",
        "repo_write_contract": "read-only asset production; integration happens in Claude Code",
        "feature_flag": "NEXT_PUBLIC_RUNTIME_3D_TRANSITIONS",
        "models": models,
    }
    out = ROOT / "manifests/runtime-3d.json"
    out.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"REGISTRY={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
