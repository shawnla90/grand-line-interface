#!/usr/bin/env python3
"""Promote verified runtime scene outputs into the queue and blockout manifest.

This script only changes asset-track metadata. The app remains untouched and
must still opt in through its loader and feature flags.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue/asset-requests.json"
BLOCKOUTS = ROOT / "manifests/narrative-blockouts.json"

RUNTIME_SCENES = (
    "fish-man-island", "totto-land", "world-government-tarai-system",
    "conomi-arlong-park", "arabasta-kingdom", "cactus-island-whisky-peak",
    "dressrosa-green-bit", "zou-zunesha", "amazon-lily",
    "mary-geoise-red-line", "sabaody-grove-network", "skypiea-sky-system",
    "loguetown-roger-execution", "water-7-sea-train-network",
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    runtime = read(ROOT / "manifests/runtime-3d.json")
    models = {x["id"]: x for x in runtime["models"]}
    builds = {x["id"]: x for x in read(ROOT / "manifests/runtime-scene-builds.json")["assets"]}
    prior_blockouts = {x["id"]: x for x in read(BLOCKOUTS)["assets"]}

    # Refuse promotion unless every declared byte exists and matches its sidecar.
    for asset_id in RUNTIME_SCENES:
        model = models[asset_id]
        glb = ROOT / model["glb"]
        fallback = ROOT / model["fallback"]["path"]
        if not glb.exists() or not fallback.exists():
            raise RuntimeError(f"{asset_id}: missing GLB or fallback")
        if sha(glb) != model["build"]["glb_sha256"]:
            raise RuntimeError(f"{asset_id}: GLB hash mismatch")
        if sha(fallback) != model["fallback"]["sha256"]:
            raise RuntimeError(f"{asset_id}: fallback hash mismatch")

    queue = read(QUEUE)
    by_id = {x["id"]: x for x in queue["assets"]}
    missing = sorted(set(RUNTIME_SCENES) - set(by_id))
    if missing:
        raise RuntimeError(f"Queue is missing: {missing}")
    for asset_id in RUNTIME_SCENES:
        row = by_id[asset_id]
        row["state"] = "integration_ready"
        row["next"] = "claude_code_runtime_loader"
        row["maturity"] = models[asset_id]["maturity"]
        row["runtime_glb"] = models[asset_id]["glb"]
        row["fallback"] = models[asset_id]["fallback"]["path"]
        row["runtime_manifest"] = "manifests/runtime-3d.json"
    # Superseded component studies remain non-integrable by design.
    for study in ("whole-cake-island", "impel-down", "sabaody-archipelago"):
        if by_id[study]["state"] != "study_only":
            raise RuntimeError(f"{study}: superseded study was accidentally promoted")
    write(QUEUE, queue)

    narrative_index = read(ROOT / "contracts/narrative-scene-index.json")
    narrative_ids = [x["id"] for x in narrative_index["contracts"]]
    assets = []
    for asset_id in narrative_ids:
        model = models[asset_id]
        prior = prior_blockouts.get(asset_id, {})
        build = builds.get(asset_id, {})
        contract = ROOT / f"contracts/{asset_id}.visual.json"
        blend = ROOT / model["source_blend"]
        render = ROOT / model["fallback"]["path"]
        assets.append({
            "id": asset_id,
            "blend": model["source_blend"],
            "render": model["fallback"]["path"],
            "runtime_glb": model["glb"],
            "runtime_model": f"runtime/{asset_id}.model.json",
            "frame_end": prior.get("frame_end", 120),
            "collections": build.get("collections", prior.get("collections", [
                "00_TOPOLOGY", "10_LANDMARKS", "20_EVENT_STATES", "30_ATMOSPHERE_FX", "40_RUNTIME_LOD"
            ])),
            "contract": f"contracts/{asset_id}.visual.json",
            "contract_sha256": sha(contract),
            "maturity": model["maturity"],
            "runtime_export": True,
            "safe_full_scene_chapter": model["integration"]["chapter_beats"]["safe_full_scene"],
            "layout_status": model["integration"].get("layout_status"),
            "blend_sha256": sha(blend),
            "render_sha256": sha(render),
            "glb_sha256": sha(ROOT / model["glb"]),
            "model_sha256": sha(ROOT / f"runtime/{asset_id}.model.json"),
        })
    payload = {
        "schema_version": 2,
        "generator": "scripts/finalize_runtime_scene_batch.py",
        "definition": "loader-ready runtime blockouts with per-component chapter metadata; not final cinematic art",
        "assets": assets,
    }
    write(BLOCKOUTS, payload)
    print(f"promoted {len(RUNTIME_SCENES)} runtime scenes")
    print(f"marked {len(assets)} narrative blockouts runtime_export=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
