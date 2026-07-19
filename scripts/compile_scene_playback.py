#!/usr/bin/env python3
"""compile_scene_playback.py — resolve the app-owned playback manifest.

canon/story_scene_playback.json is TREATMENT (journey dwell + audio-cue
bindings) for scenes that already shipped in the signed pack artifacts. This
compiler joins that treatment against the packs, canon events, and the audio
registry, resolves every event-relative sound binding to an absolute scene
millisecond, and emits data/generated/story_scene_playback.json — the ONLY
file the app imports. Hard-fails on any contradiction: an unknown scene, a
binding past the scene's end, or a journey hold too short to let the scene
finish are authoring bugs, not warnings.

Byte-stable output (no timestamps) so an unchanged compile is an unchanged
file — the sync_east_blue_2d.py posture.

Run: python3 scripts/compile_scene_playback.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import story_pack_registry

ROOT = Path(__file__).resolve().parent.parent
PLAYBACK = ROOT / "canon/story_scene_playback.json"
CANON_JSON = ROOT / "data/canon.json"
CUES_JSON = ROOT / "data/simulation-audio-cues.json"
OUT = ROOT / "data/generated/story_scene_playback.json"

# The dwell camera must clear the scene-mount zoom gate or the journey would
# stop for a stage that never appears. Mirrors SIM_MIN_ZOOM (east-blue config).
SIM_MIN_ZOOM = 4.6
# The journey camera eases over rampFrac of a dwell window; a hold without
# this allowance would cut the tableau during the ease-out.
RAMP_ALLOWANCE_MS = 1200
# A scene whose events land blows is a FIGHT, and fights have two extra
# contracts (the phase-10 cinematic floor): they may not play silent, and
# their finishing beat must hold on screen past the ramp. Quiet tableaus
# (no matching events) are exempt — silence suits them.
CLIMAX_EVENT_RE = re.compile(r"impact|defeat|victory-pulse")
CLIMAX_MIN_BINDINGS = 2
CLIMAX_SYNC_WINDOW_MS = 600
CLIMAX_TAIL_MS = 800  # held final beat on top of RAMP_ALLOWANCE_MS


class DataError(Exception):
    pass


def load(path: Path) -> dict:
    if not path.is_file():
        raise DataError(f"missing input: {path.relative_to(ROOT)}")
    return json.loads(path.read_text())


def resolve_at(at: dict, scene: dict, where: str) -> int:
    """One binding time → absolute scene-local ms."""
    if "ms" in at:
        if set(at) != {"ms"}:
            raise DataError(f"{where}: literal binding must be exactly {{ms}}, got {sorted(at)}")
        if not isinstance(at["ms"], int):
            raise DataError(f"{where}: ms must be an integer")
        return at["ms"]
    required = {"type", "occurrence", "offset_ms"}
    if set(at) != required:
        raise DataError(f"{where}: event binding must be exactly {sorted(required)}, got {sorted(at)}")
    matches = sorted(
        (e for e in scene["events"] if e["type"] == at["type"]),
        key=lambda e: e["t"],
    )
    if not matches:
        raise DataError(f"{where}: scene has no {at['type']!r} event")
    occ = at["occurrence"]
    if not isinstance(occ, int) or not (0 <= occ < len(matches)):
        raise DataError(
            f"{where}: occurrence {occ!r} out of range — scene has "
            f"{len(matches)} {at['type']!r} event(s)"
        )
    if not isinstance(at["offset_ms"], int):
        raise DataError(f"{where}: offset_ms must be an integer")
    return matches[occ]["t"] + at["offset_ms"]


def main() -> int:
    playback = load(PLAYBACK)
    if playback.get("version") != 1:
        raise DataError(f"playback manifest version {playback.get('version')!r}, expected 1")

    # Every synced pack artifact on disk participates — a new pack reaches the
    # compiler without an edit here (discovery is shared with the registry
    # emitter, so the app and the compiler can never disagree on the roster).
    scenes_by_pack: dict[str, dict[str, dict]] = {}
    for pack_id, artifact in story_pack_registry.discover_artifacts().items():
        doc = load(artifact)
        if doc["_meta"]["pack_id"] != pack_id:
            raise DataError(f"{artifact.name}: _meta.pack_id {doc['_meta']['pack_id']!r} != {pack_id!r}")
        scenes_by_pack[pack_id] = {s["id"]: s for s in doc["scenes"]}

    events = {e["slug"]: e for e in load(CANON_JSON)["events"]}

    # The cue registry is optional until the first audio binding exists; the
    # moment any row binds a cue, the registry becomes a required input.
    cue_ids: set[str] | None = None
    if CUES_JSON.is_file():
        cue_ids = {c["id"] for c in load(CUES_JSON)["cues"]}

    rows = playback["scenes"]
    seen: set[str] = set()
    compiled = []
    for row in rows:
        sid = row["scene_id"]
        where = f"scene {sid!r}"
        if sid in seen:
            raise DataError(f"{where}: duplicate row")
        seen.add(sid)

        pack_id = row["pack_id"]
        if pack_id not in scenes_by_pack:
            raise DataError(f"{where}: unknown pack {pack_id!r}")
        scene = scenes_by_pack[pack_id].get(sid)
        if scene is None:
            raise DataError(f"{where}: not a runtime-ready scene of {pack_id!r}")

        journey = row["journey"]
        enabled = journey["enabled"]
        hold_ms = journey["hold_ms"]
        duration = scene["duration_ms"]
        if enabled:
            ev_slug = row.get("event")
            if not ev_slug:
                raise DataError(f"{where}: journey-enabled but no canon event slug")
            ev = events.get(ev_slug)
            if ev is None:
                raise DataError(f"{where}: unknown canon event {ev_slug!r}")
            chapter = scene["chapter_gate"]["start"]
            if ev["occurred_chapter"] > chapter:
                raise DataError(
                    f"{where}: event {ev_slug!r} occurs at ch{ev['occurred_chapter']}, "
                    f"after the scene's ch{chapter} gate — the caption would spoil"
                )
            if hold_ms < duration + RAMP_ALLOWANCE_MS:
                raise DataError(
                    f"{where}: hold_ms {hold_ms} < duration {duration} + "
                    f"{RAMP_ALLOWANCE_MS} ramp allowance"
                )
            if journey["zoom"] < SIM_MIN_ZOOM:
                raise DataError(f"{where}: journey zoom {journey['zoom']} below scene-mount gate {SIM_MIN_ZOOM}")

        # Optional one-shot push-in on the dwell clock. Bounded tight: the
        # actors are billboards, so a big zoom delta breaks the stage read,
        # and the move must finish inside the hold it lives in.
        camera = journey.get("camera")
        if camera is not None:
            cwhere = f"{where} journey.camera"
            if not enabled:
                raise DataError(f"{cwhere}: push-in on a journey-disabled row")
            allowed = {"zoom_to", "pitch_to", "at_ms", "duration_ms"}
            if not set(camera) <= allowed or "at_ms" not in camera or "duration_ms" not in camera:
                raise DataError(f"{cwhere}: fields must be at_ms + duration_ms (+ zoom_to/pitch_to), got {sorted(camera)}")
            if "zoom_to" not in camera and "pitch_to" not in camera:
                raise DataError(f"{cwhere}: needs zoom_to and/or pitch_to — an empty move is a typo")
            zoom_to = camera.get("zoom_to")
            if zoom_to is not None:
                if zoom_to < SIM_MIN_ZOOM:
                    raise DataError(f"{cwhere}: zoom_to {zoom_to} below scene-mount gate {SIM_MIN_ZOOM}")
                if abs(zoom_to - journey["zoom"]) > 0.9:
                    raise DataError(f"{cwhere}: |zoom_to - zoom| {abs(zoom_to - journey['zoom']):.2f} > 0.9 — billboards break under big pushes")
            pitch_to = camera.get("pitch_to")
            if pitch_to is not None and not (30 <= pitch_to <= 62):
                raise DataError(f"{cwhere}: pitch_to {pitch_to} outside [30, 62]")
            if not (isinstance(camera["at_ms"], int) and camera["at_ms"] >= 0):
                raise DataError(f"{cwhere}: at_ms must be a non-negative integer")
            if not (isinstance(camera["duration_ms"], int) and camera["duration_ms"] >= 1500):
                raise DataError(f"{cwhere}: duration_ms must be an integer >= 1500 — faster reads as a snap")
            if camera["at_ms"] + camera["duration_ms"] > hold_ms:
                raise DataError(f"{cwhere}: at_ms + duration_ms {camera['at_ms'] + camera['duration_ms']} > hold_ms {hold_ms}")

        bindings = []
        binding_ids: set[str] = set()
        for b in row["audio"]:
            bwhere = f"{where} binding {b.get('id')!r}"
            if cue_ids is None:
                raise DataError(f"{bwhere}: audio bindings exist but {CUES_JSON.name} does not")
            if b["id"] in binding_ids:
                raise DataError(f"{bwhere}: duplicate binding id")
            binding_ids.add(b["id"])
            if b["cue_id"] not in cue_ids:
                raise DataError(f"{bwhere}: unknown cue {b['cue_id']!r}")
            at_ms = resolve_at(b["at"], scene, bwhere)
            if not (0 <= at_ms <= duration):
                raise DataError(f"{bwhere}: resolves to {at_ms}ms, outside [0, {duration}]")
            if not (0.0 <= b["gain"] <= 1.0):
                raise DataError(f"{bwhere}: gain {b['gain']} outside [0, 1]")
            if not (-1.0 <= b["pan"] <= 1.0):
                raise DataError(f"{bwhere}: pan {b['pan']} outside [-1, 1]")
            if not (0.5 <= b["playback_rate"] <= 2.0):
                raise DataError(f"{bwhere}: playback_rate {b['playback_rate']} outside [0.5, 2]")
            bindings.append({
                "id": b["id"],
                "cue_id": b["cue_id"],
                "at_ms": at_ms,
                "gain": b["gain"],
                "pan": b["pan"],
                "playback_rate": b["playback_rate"],
            })

        # The cinematic floor. A fight (climax events present) may not ship
        # silent, and one of its sounds must land ON a blow — the Fire Fist
        # reference reads cinematic because the audio hits the hits.
        climax_ts = sorted(
            e["t"] for e in scene.get("events", []) if CLIMAX_EVENT_RE.search(e["type"])
        )
        if climax_ts:
            if len(bindings) < CLIMAX_MIN_BINDINGS:
                raise DataError(
                    f"{where}: a fight with {len(bindings)} audio binding(s) — "
                    f"climax scenes need >= {CLIMAX_MIN_BINDINGS} (silence is for tableaus)"
                )
            on_blow = any(
                abs(b["at_ms"] - t) <= CLIMAX_SYNC_WINDOW_MS for b in bindings for t in climax_ts
            )
            if not on_blow:
                raise DataError(
                    f"{where}: no binding within {CLIMAX_SYNC_WINDOW_MS}ms of a climax event — "
                    f"the sound must land on the blow"
                )
            if enabled and hold_ms < duration + RAMP_ALLOWANCE_MS + CLIMAX_TAIL_MS:
                raise DataError(
                    f"{where}: climax hold_ms {hold_ms} < duration {duration} + "
                    f"{RAMP_ALLOWANCE_MS} ramp + {CLIMAX_TAIL_MS} held final beat"
                )

        anchor = scene["anchor"]
        compiled.append({
            "scene_id": sid,
            "pack_id": pack_id,
            "event": row.get("event"),
            "label_override": row.get("label_override"),
            "chapter": scene["chapter_gate"]["start"],
            "duration_ms": duration,
            "anchor": {"lng": anchor["lng"], "lat": anchor["lat"]},
            "journey": {
                "enabled": enabled,
                "hold_ms": hold_ms,
                "zoom": journey["zoom"],
                "pitch": journey["pitch"],
                # Emitted only when authored — un-pushed rows stay byte-identical.
                **({"camera": camera} if camera is not None else {}),
            },
            "audio": bindings,
        })

    # Coverage is a contract: every runtime-ready scene gets a row, even a
    # disabled one — a missing row is indistinguishable from a forgotten scene.
    all_ids = {sid for pack in scenes_by_pack.values() for sid in pack}
    missing = sorted(all_ids - seen)
    if missing:
        raise DataError(f"runtime-ready scenes without a playback row: {', '.join(missing)}")

    out = {
        "_meta": {
            "generator": "scripts/compile_scene_playback.py",
            "schema_version": 1,
            "counts": {
                "scenes": len(compiled),
                "journey_enabled": sum(1 for r in compiled if r["journey"]["enabled"]),
                "audio_bindings": sum(len(r["audio"]) for r in compiled),
            },
        },
        "scenes": compiled,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    c = out["_meta"]["counts"]
    print(
        f"story_scene_playback: {c['scenes']} scenes, {c['journey_enabled']} journey stops, "
        f"{c['audio_bindings']} audio bindings — wrote {OUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as err:
        print(f"DATA ERROR: {err}", file=sys.stderr)
        sys.exit(1)
