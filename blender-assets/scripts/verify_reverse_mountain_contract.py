#!/usr/bin/env python3
"""Verify the W1 Reverse Mountain/Twin Cape contract and chapter ledger."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = Path("/Users/shawnos.ai/dead-reckoning")
CONTRACT_PATH = ROOT / "contracts" / "reverse-mountain-twin-cape-voyage.visual.json"
LEDGER_PATH = ROOT / "research" / "story-scenes" / "reverse-mountain-batch-a.json"
SCHEMA_PATH = ROOT / "contracts" / "narrative-scene.schema.json"
CHAPTERS_PATH = APP_ROOT / "data" / "raw" / "chapters.json"


def read(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    contract = read(CONTRACT_PATH)
    ledger = read(LEDGER_PATH)
    schema = read(SCHEMA_PATH)
    chapters = {row["id"]: row for row in read(CHAPTERS_PATH)}

    errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda error: list(error.path))
    assert not errors, "schema validation failed: " + "; ".join(error.message for error in errors)

    assert contract["id"] == "reverse-mountain-twin-cape-voyage"
    assert contract["contract_status"] == "ready_for_system_sketch"
    assert contract["topology"]["exact_distances"] == "unknown"
    assert contract["topology"]["exact_bearings"] == "unknown"
    assert "atlas jitter" in contract["coordinate_policy"]["local_topology"]

    components = {component["id"]: component for component in contract["identity"]["components"]}
    required_components = {
        "reverse-mountain-massif",
        "east-blue-ascent-current",
        "reverse-mountain-crest",
        "grand-line-descent-current",
        "twin-cape",
        "twin-cape-lighthouse",
        "going-merry",
        "laboon-unidentified",
        "laboon",
        "laboon-interior-theatre",
        "crocus",
        "local-whirlpool-emitter",
    }
    assert required_components <= components.keys()
    assert components["local-whirlpool-emitter"]["reveal_chapter"] is None
    assert components["local-whirlpool-emitter"]["default_hidden"] is True
    assert components["local-whirlpool-emitter"]["verification"] == "chapter_to_verify"
    assert components["laboon-unidentified"]["label_policy"] == "Do not display the name Laboon at chapter 102."
    assert components["laboon"]["identity_reveal_chapter"] == 103

    states = contract["chapter_logic"]["temporal_variants"]
    assert [state["reveal_chapter"] for state in states] == [101, 102, 103, 104, 105]
    assert contract["chapter_logic"]["pre_reveal_guard"]["through_chapter"] == 100
    assert contract["chapter_logic"]["base_reveal_chapter"] == 101
    assert all(state["verification"] == "verified" for state in states)

    events = contract["chapter_logic"]["event_scenes"]
    assert [event["reveal_chapter"] for event in events] == [101, 102, 103, 104, 105]
    assert all(event["verification"] == "verified" for event in events)

    routes = {edge["id"]: edge for edge in contract["route_network"]["edges"]}
    assert routes["east-blue-approach"]["runtime_visibility"] == "route_hint_only_no_mountain_geometry"
    assert routes["reverse-mountain-ascent"]["reveal_chapter"] == 101
    assert routes["grand-line-descent"]["reveal_chapter"] == 102
    assert routes["twin-cape-to-whisky-peak"]["reveal_chapter"] == 105

    asset_groups = contract["asset_decomposition"]
    assert {"environment", "landmarks", "routes", "vehicle", "creature", "actors", "event_states"} <= asset_groups.keys()
    assert len(contract["fx_masks"]) == 5
    assert contract["fx_masks"][-1]["id"] == "whirlpool-control-rgba"
    assert contract["fx_masks"][-1]["default_hidden"] is True
    assert len(contract["lod_program"]["tiers"]) == 4
    assert contract["lod_program"]["tiers"][-1]["id"] == "LOD3_FALLBACK"

    all_clips = []
    for group in ("going_merry", "laboon", "crocus_2_5d"):
        clips = contract["named_clips"][group]
        assert all(clip["required"] is True for clip in clips)
        all_clips.extend(clip["name"] for clip in clips)
    all_clips.extend(contract["named_clips"]["fx"])
    assert len(all_clips) == len(set(all_clips)), "named clips must be unique"

    assert set(contract["fallbacks"]) == {
        "reduced_motion",
        "webgl_unavailable",
        "asset_load_failure",
        "audio_unavailable",
        "unverified_geometry",
    }
    assert "MapLibre" in contract["runtime_ownership"]["world_anchor_and_route_state"]
    assert "Three.js" in contract["runtime_ownership"]["local_scene_rendering"]
    assert contract["unreal_reuse"]["unreal_mapping"]["spray_wake_mist"].startswith("Niagara")

    criteria = {item["id"] for item in contract["acceptance_criteria"]}
    assert {
        "AC-CANON-001",
        "AC-GATE-001",
        "AC-GATE-002",
        "AC-GATE-003",
        "AC-GATE-004",
        "AC-ASSET-001",
        "AC-MOTION-001",
        "AC-FX-001",
        "AC-LOD-001",
        "AC-RUNTIME-001",
        "AC-UNREAL-001",
        "AC-FALLBACK-001",
    } <= criteria

    ledger_scenes = ledger["scenes"]
    assert [scene["chapter_gate"]["start"] for scene in ledger_scenes] == list(range(100, 106))
    assert all(scene["chapter_gate"]["start"] == scene["chapter_gate"]["end"] for scene in ledger_scenes)
    assert all(scene["chapter_gate"]["verification"] == "verified_from_local_chapter_summary" for scene in ledger_scenes)

    for scene in ledger_scenes:
        gate = scene["chapter_gate"]
        chapter = chapters[gate["start"]]
        assert gate["local_title"] == chapter["title"]
        assert gate["local_description_sha256"] == sha256_text(chapter["description"])

    ch100 = ledger_scenes[0]
    assert ch100["place"]["anchor_status"] == "must_not_anchor_to_reverse_mountain_before_chapter_101"
    ch102 = ledger_scenes[2]
    assert "unidentified-giant-whale" in ch102["cast"]
    assert "Laboon" not in ch102["outcome_claim"]
    ch103 = ledger_scenes[3]
    assert {"crocus", "laboon"} <= set(ch103["cast"])
    ch104 = ledger_scenes[4]
    assert "extended fight" in ch104["coverage_action"]
    ch105 = ledger_scenes[5]
    assert ch105["place"]["anchor_status"] == "handoff_to_existing_whisky_peak_world_route"

    evidence = contract["evidence"]
    assert len(evidence) == 5
    for item in evidence:
        assert len(item["sha256"]) == 64
        path = Path(item["path"])
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == item["sha256"], f"evidence drift: {path}"

    print("Reverse Mountain W1 contract verified")
    print(f"  schema: narrative-scene v{contract['schema_version']}")
    print(f"  components: {len(components)}")
    print(f"  event scenes: {len(events)}")
    print(f"  chapter ledger: {len(ledger_scenes)} rows ({ledger_scenes[0]['chapter_gate']['start']}-{ledger_scenes[-1]['chapter_gate']['end']})")
    print(f"  named clips: {len(all_clips)}")
    print(f"  FX masks: {len(contract['fx_masks'])}")
    print(f"  LOD tiers: {len(contract['lod_program']['tiers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
