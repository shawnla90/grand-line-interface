#!/usr/bin/env python3
"""Verify that every declared asset domain has its required source controls."""

from __future__ import annotations

import glob
import json
from pathlib import Path


ASSET_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ASSET_ROOT.parent
MANIFEST = ASSET_ROOT / "manifests/workspace-ownership.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    roots = {
        "app_checkout": APP_ROOT,
        "embedded_assets": ASSET_ROOT,
        "story_art_factory": Path(data["roots"]["story_art_factory"]),
    }
    failures: list[str] = []
    counts: dict[str, int] = {}

    for domain in data["domains"]:
        root = roots[domain["authoritative_root"]]
        matched = 0
        for pattern in domain["paths"]:
            paths = [Path(path) for path in glob.glob(str(root / pattern), recursive=True)]
            files = [path for path in paths if path.is_file()]
            if not files:
                failures.append(f"{domain['id']}: no files match {root / pattern}")
            matched += len(files)
        counts[domain["id"]] = matched

    embedded_runtime = json.loads((ASSET_ROOT / "manifests/runtime-3d.json").read_text())
    standalone_runtime = json.loads(
        (roots["story_art_factory"] / "manifests/runtime-3d.json").read_text()
    )
    embedded_models = len(embedded_runtime.get("models", []))
    standalone_models = len(standalone_runtime.get("models", []))
    if embedded_models < standalone_models:
        failures.append(
            "runtime-3d ownership reversed: standalone contains more models than embedded"
        )

    report = {
        "schema_version": 1,
        "authoritative_domains": counts,
        "runtime_3d_models": {
            "embedded": embedded_models,
            "standalone_snapshot": standalone_models,
        },
        "failures": failures,
        "ok": not failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
