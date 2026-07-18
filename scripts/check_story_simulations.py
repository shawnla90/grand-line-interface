#!/usr/bin/env python3
"""Deterministic browser-artifact checks for a generic story pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    args = parser.parse_args()
    pack_id = args.pack
    artifact_path = ROOT / "data/generated/story_simulations" / f"{pack_id}.json"
    manifest_path = ROOT / "blender-assets/manifests/story-simulations" / f"{pack_id}.json"
    artifact = json.loads(artifact_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    passes = 0
    failures = 0

    def check(name: str, ok: bool, detail: str = ""):
        nonlocal passes, failures
        mark = "PASS" if ok else "FAIL"
        print(f"  {mark:4}  {name}" + (f"  {detail}" if detail else ""))
        if ok:
            passes += 1
        else:
            failures += 1

    meta = artifact["_meta"]
    check("pack_identity", meta["pack_id"] == manifest["id"] == pack_id)
    check(
        "disabled_by_default",
        meta["feature_flag"] == "NEXT_PUBLIC_STORY_SIMULATION_PACKS"
        and not os.environ.get("NEXT_PUBLIC_STORY_SIMULATION_PACKS"),
    )
    check("web_proof_promoted", manifest["integration_ready"] is True and meta["integration_ready"] is True)
    check("web_proof_receipt", isinstance(manifest.get("web_proof"), dict) and manifest["web_proof"]["sha256"])
    check("signed_manifest_receipt", meta["source_manifest_sha256"] == sha256(manifest_path))

    scenes = artifact["scenes"]
    ids = {scene["id"] for scene in scenes}
    check("scene_set", ids == {
        "whisky-peak-zoro-vs-bounty-hunters",
        "robin-miss-all-sunday-arrival",
        "ace-blocks-smoker-at-nanohana",
    }, ", ".join(sorted(ids)))
    expected_gates = {
        "whisky-peak-zoro-vs-bounty-hunters": (107, 108),
        "robin-miss-all-sunday-arrival": (114, 114),
        "ace-blocks-smoker-at-nanohana": (158, 158),
    }
    gates_ok = all(
        (scene["chapter_gate"]["start"], scene["chapter_gate"]["end"]) == expected_gates[scene["id"]]
        and scene["chapter_gate"]["verification"] == "verified"
        for scene in scenes
    )
    check("verified_scene_gates", gates_ok)
    ace = next(scene for scene in scenes if scene["id"] == "ace-blocks-smoker-at-nanohana")
    check("ace_smoker_claim_is_truthful", "versus" not in ace["label"].lower() and "intervenes" in ace["label"].lower())

    assets = artifact["assets"]
    referenced = {actor["asset_id"] for scene in scenes for actor in scene["actors"]}
    check("runtime_cast_is_complete", referenced == set(assets), f"{len(referenced)} referenced / {len(assets)} signed")
    signed = {character["id"]: character["atlas"]["sha256"] for character in manifest["characters"]}
    bytes_ok = True
    for asset_id, asset in assets.items():
        served = ROOT / "public" / asset["url"].lstrip("/")
        bytes_ok = bytes_ok and served.is_file() and sha256(served) == asset["sha256"] == signed[asset_id]
    check("served_atlases_are_signed", bytes_ok, f"{len(assets)} atlases")

    keyframes_ok = True
    for scene in scenes:
        for actor in scene["actors"]:
            times = [frame["t"] for frame in actor["keyframes"]]
            keyframes_ok = keyframes_ok and times == sorted(set(times))
            keyframes_ok = keyframes_ok and all(frame["pose"] in assets[actor["asset_id"]]["frames"] for frame in actor["keyframes"])
    check("keyframes_are_well_formed", keyframes_ok)

    anchors_ok = all(
        scene["anchor"]["kind"] in {"event", "island", "literal"}
        and isinstance(scene["anchor"]["lng"], (int, float))
        and isinstance(scene["anchor"]["lat"], (int, float))
        for scene in scenes
    )
    check("anchors_are_resolved", anchors_ok)

    before = artifact_path.read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/sync_story_simulation_pack.py", "--pack", pack_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    check("sync_rerun_succeeds", result.returncode == 0, result.stderr.strip())
    check("sync_is_deterministic", before == artifact_path.read_bytes())

    print(f"\n{passes}/{passes + failures} checks pass")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
