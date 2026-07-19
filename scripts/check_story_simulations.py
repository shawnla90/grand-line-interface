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

import story_pack_registry


ROOT = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--require-promoted", action="store_true")
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
    promotion_consistent = (
        meta["integration_ready"] == manifest["integration_ready"]
        and bool(manifest.get("web_proof")) == manifest["integration_ready"]
    )
    check("promotion_state_consistent", promotion_consistent)
    if args.require_promoted:
        check("web_proof_promoted", manifest["integration_ready"] is True)
    check("signed_manifest_receipt", meta["source_manifest_sha256"] == sha256(manifest_path))

    scenes = artifact["scenes"]
    ids = {scene["id"] for scene in scenes}
    pack_gates = {
        "arabasta-saga-2d-v1": {
            "whisky-peak-zoro-vs-bounty-hunters": (107, 108),
            "robin-miss-all-sunday-arrival": (114, 114),
            "ace-blocks-smoker-at-nanohana": (158, 158),
            "ace-fire-fist-destroys-billions-fleet": (159, 159),
            "arabasta-luffy-vs-crocodile-round-one": (176, 179),
            "arabasta-sanji-vs-bon-clay": (187, 189),
            "arabasta-nami-vs-miss-doublefinger": (190, 193),
            "arabasta-zoro-vs-mr-one": (194, 195),
            "arabasta-luffy-vs-crocodile-round-two": (198, 201),
            "arabasta-luffy-vs-crocodile-final": (203, 210),
        },
        "skypiea-saga-2d-v1": {"skypiea-luffy-vs-enel": (279, 302)},
        "enies-lobby-saga-2d-v1": {
            "enies-lobby-luffy-vs-blueno": (387, 388),
            "enies-lobby-sanji-vs-jabra": (415, 415),
            "enies-lobby-zoro-vs-kaku": (416, 417),
            "enies-lobby-luffy-vs-rob-lucci": (418, 427),
        },
    }
    expected_gates = pack_gates.get(pack_id)
    check("known_pack_contract", expected_gates is not None)
    if expected_gates is None:
        expected_gates = {}
    check("scene_set", ids == set(expected_gates), ", ".join(sorted(ids)))
    gates_ok = all(
        (scene["chapter_gate"]["start"], scene["chapter_gate"]["end"]) == expected_gates[scene["id"]]
        and scene["chapter_gate"]["verification"] == "verified"
        for scene in scenes
    )
    check("verified_scene_gates", gates_ok)
    if pack_id == "arabasta-saga-2d-v1":
        ace = next(scene for scene in scenes if scene["id"] == "ace-blocks-smoker-at-nanohana")
        check("ace_smoker_claim_is_truthful", "versus" not in ace["label"].lower() and "intervenes" in ace["label"].lower())
        fleet = next(scene for scene in scenes if scene["id"] == "ace-fire-fist-destroys-billions-fleet")
        check("fire_fist_targets_are_truthful", "billions" in fleet["label"].lower() and "marine" not in fleet["label"].lower())
        crocodile = next(scene for scene in scenes if scene["id"] == "arabasta-luffy-vs-crocodile-round-one")
        check(
            "crocodile_round_one_supersedes_faceless_blockout",
            "arabasta-luffy-crocodile-sand-study" in artifact.get("supersedes_visible_art", [])
            and {actor["asset_id"] for actor in crocodile["actors"]}
            == {"crocodile-arabasta-sand", "monkey-d-luffy-crocodile-round-one"},
        )
        sanji = next(scene for scene in scenes if scene["id"] == "arabasta-sanji-vs-bon-clay")
        check("arabasta_sanji_has_no_diable_jambe_leak", all("diable" not in frame["pose"].lower() for actor in sanji["actors"] for frame in actor["keyframes"]))
        nami = next(scene for scene in scenes if scene["id"] == "arabasta-nami-vs-miss-doublefinger")
        check(
            "arabasta_nami_uses_first_clima_tact_only",
            all(forbidden not in frame["pose"].lower() for actor in nami["actors"] for frame in actor["keyframes"] for forbidden in ("perfect", "zeus")),
        )
        trilogy = [next(scene for scene in scenes if scene["id"] == scene_id) for scene_id in (
            "arabasta-luffy-vs-crocodile-round-one",
            "arabasta-luffy-vs-crocodile-round-two",
            "arabasta-luffy-vs-crocodile-final",
        )]
        trilogy_casts = [{actor["asset_id"] for actor in scene["actors"]} for scene in trilogy]
        check("crocodile_trilogy_has_distinct_actor_variants", len({frozenset(cast) for cast in trilogy_casts}) == 3)
        check(
            "crocodile_countermeasure_progression_is_separate",
            any("water" in frame["pose"] for actor in trilogy[1]["actors"] for frame in actor["keyframes"])
            and not any("water" in frame["pose"] for actor in trilogy[2]["actors"] for frame in actor["keyframes"])
            and any("blood" in frame["pose"] for actor in trilogy[2]["actors"] for frame in actor["keyframes"]),
        )
    elif pack_id == "skypiea-saga-2d-v1":
        scene = scenes[0]
        poses = {frame["pose"] for actor in scene["actors"] for frame in actor["keyframes"]}
        events = {event["type"] for event in scene["events"]}
        check("rubber_immunity_is_authored", "lightning-immunity-laugh" in poses and "rubber-immunity-pulse" in events)
        check("gold_ball_and_bell_finish_are_distinct", {"gold-ball-burden", "golden-rifle-launch", "bell-ring-victory"} <= poses and "golden-bell-impact" in events)
        check("enel_identity_states_are_complete", {"lightning-discharge", "amaru-thunder-form", "golden-bell-defeat"} <= poses)
    elif pack_id == "enies-lobby-saga-2d-v1":
        by_id = {scene["id"]: scene for scene in scenes}
        blueno = by_id["enies-lobby-luffy-vs-blueno"]
        blueno_poses = {frame["pose"] for actor in blueno["actors"] for frame in actor["keyframes"]}
        blueno_events = {event["type"] for event in blueno["events"]}
        check(
            "first_gear_second_is_authored",
            {"gear-second-activation", "jet-pistol-rush", "jet-bazooka-impact"} <= blueno_poses
            and {"door-door-ripple", "gear-second-steam", "jet-bazooka-impact"} <= blueno_events,
        )
        sanji = by_id["enies-lobby-sanji-vs-jabra"]
        sanji_poses = {frame["pose"] for actor in sanji["actors"] for frame in actor["keyframes"]}
        sanji_events = {event["type"] for event in sanji["events"]}
        check(
            "first_diable_jambe_is_authored",
            {"diable-jambe-ignite", "flambage-shot", "diable-jambe-impact"} <= sanji_poses
            and {"diable-jambe-ignite", "flambage-impact"} <= sanji_events,
        )
        zoro = by_id["enies-lobby-zoro-vs-kaku"]
        zoro_poses = {frame["pose"] for actor in zoro["actors"] for frame in actor["keyframes"]}
        zoro_events = {event["type"] for event in zoro["events"]}
        check(
            "asura_and_four_sword_style_are_authored",
            {"four-sword-style", "asura-manifestation", "nine-sword-asura-strike"} <= zoro_poses
            and {"four-sword-rush", "asura-aura", "nine-sword-impact"} <= zoro_events,
        )
        lucci = by_id["enies-lobby-luffy-vs-rob-lucci"]
        lucci_poses = {frame["pose"] for actor in lucci["actors"] for frame in actor["keyframes"]}
        lucci_events = {event["type"] for event in lucci["events"]}
        check("gear_progression_is_authored", {"gear-second-guard", "gear-third-giant-arm"} <= lucci_poses)
        check("jet_gatling_is_authored", "jet-gatling-barrage" in lucci_poses and "jet-gatling-defeat" in lucci_poses and "jet-gatling" in lucci_events)
        check("lucci_rokushiki_states_are_authored", {"soru-rush", "finger-pistol", "tempest-kick", "rokuogan-shockwave"} <= lucci_poses)

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
    registry_before = story_pack_registry.REGISTRY_TS.read_bytes()
    result = subprocess.run(
        [sys.executable, "scripts/sync_story_simulation_pack.py", "--pack", pack_id],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    check("sync_rerun_succeeds", result.returncode == 0, result.stderr.strip())
    check("sync_is_deterministic", before == artifact_path.read_bytes())
    # The generated TS registry (pack ids, aliases, chapter gates, import
    # thunks) must be exactly what the artifacts on disk derive — the
    # geo_artifacts_fresh posture applied to the pack socket.
    check(
        "registry_matches_artifacts",
        story_pack_registry.render_ts(story_pack_registry.derive_rows())
        == story_pack_registry.REGISTRY_TS.read_text(),
    )
    check("registry_is_deterministic", registry_before == story_pack_registry.REGISTRY_TS.read_bytes())

    print(f"\n{passes}/{passes + failures} checks pass")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
