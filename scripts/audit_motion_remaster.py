#!/usr/bin/env python3
"""Verify the first choreography remasters use existing art with denser timing."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "baratie-zoro-vs-mihawk": ROOT / "data/generated/east_blue_simulations.json",
    "enies-lobby-luffy-vs-rob-lucci": ROOT
    / "data/generated/story_simulations/enies-lobby-saga-2d-v1.json",
}


def main() -> int:
    failures: list[str] = []
    report: dict[str, dict] = {}
    for scene_id, path in TARGETS.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        scene = next(scene for scene in payload["scenes"] if scene["id"] == scene_id)
        event_times = [event["t"] for event in scene["events"]]
        actor_rows = []
        all_key_times: set[int] = set()
        for actor in scene["actors"]:
            keyframes = actor["keyframes"]
            times = [keyframe["t"] for keyframe in keyframes]
            all_key_times.update(times)
            short_contact_segments = sum(
                33 <= following["t"] - previous["t"] <= 120
                for previous, following in zip(keyframes, keyframes[1:])
            )
            reused_pose_segments = sum(
                previous["pose"] == following["pose"]
                for previous, following in zip(keyframes, keyframes[1:])
            )
            if len(keyframes) < 14:
                failures.append(f"{scene_id}:{actor['id']} has only {len(keyframes)} keyframes")
            if short_contact_segments < 3:
                failures.append(
                    f"{scene_id}:{actor['id']} has only {short_contact_segments} contact/hit-stop segments"
                )
            if reused_pose_segments < 3:
                failures.append(
                    f"{scene_id}:{actor['id']} does not reuse poses for transform-only motion"
                )
            actor_rows.append(
                {
                    "id": actor["id"],
                    "keyframes": len(keyframes),
                    "short_contact_segments": short_contact_segments,
                    "reused_pose_segments": reused_pose_segments,
                    "longest_segment_ms": max(b - a for a, b in zip(times, times[1:])),
                }
            )
        unbracketed = [
            event_time
            for event_time in event_times
            if min(abs(event_time - key_time) for key_time in all_key_times) > 120
        ]
        if unbracketed:
            failures.append(f"{scene_id}: FX without a nearby choreography key: {unbracketed}")
        report[scene_id] = {
            "actors": actor_rows,
            "fx_events": len(event_times),
            "fx_without_nearby_key": unbracketed,
        }

    print(json.dumps({"scenes": report, "failures": failures, "ok": not failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
