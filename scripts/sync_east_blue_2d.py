#!/usr/bin/env python3
"""sync_east_blue_2d.py — copy the SANCTIONED East Blue 2.5D pack into public/.
MACHINE-OWNED. Pack schema version 1.

THE MANIFEST IS THE BOUNDARY, NOT CHAT HISTORY — same law as
sync_runtime_assets.py. This script reads manifests/east-blue-2d.json, verifies
every byte it ships against the sha256 the asset track signed, and copies
nothing else. The pack being "done" in a conversation is not an input here.

WHAT IT COPIES: the 14 character atlases (atlas.png per slug) into
public/art/east-blue-2d/<slug>/, but ONLY the ones referenced by scenes that
survive the readiness filter — plus every atlas the character-index signs, since
a runtime_ready scene may cast any of them.

WHAT IT EMITS: data/generated/east_blue_simulations.json — the 12 runtime_ready
scenes verbatim (actors, keyframes, FX events, verified chapter gates), the
per-asset frame table the renderer needs (pose -> atlas cell + pivot), and an
explicit `refused` list naming the 2 art_partial scenes and why. The refusal
being IN the artifact is the point: the app can render "story withheld, missing
Morgan/Koby art" instead of silently having no scene, and nobody re-enables
them by accident because check_simulations.py pins the refused set.

WHAT IT REFUSES, hard-failing the whole run rather than skipping:
  - a manifest whose state is not `runtime_verified` (the asset track's own
    promotion gate; we do not outrank it),
  - any file whose bytes or sha256 disagree with the manifest (we serve these
    bytes to a browser; the signature is the gate, not a smell test),
  - a runtime_ready scene with an unverified or out-of-range chapter gate,
    a cast member missing from the character index, or a keyframe pose that
    does not exist in that actor's atlas frames. A signed pack with an
    internal contradiction is the asset track's bug — surfacing it loudly
    here beats shipping a scene that breaks at t=3400ms.

NO TIMESTAMPS in the output — the artifact must be byte-identical across
re-runs (check_scenes.py had to learn to blank generated_at; this file just
never writes one). Provenance is `source_manifest_sha256` instead: the exact
signed manifest these bytes came from.

ANCHORS: each shipped scene is stamped with its map position, resolved from
canon/east_blue_scene_anchors.json (hand-authored wiring) against data/canon.json
at sync time. Event anchors inherit the event's coordinate, island anchors the
island's — so the scene, the /event page and the map can never disagree about
where a thing happened. The no-leak calendar math (scene gate vs event
occurred_chapter vs island debut) is check_simulations.py's job, not ours; we
resolve, it proves.

Inputs   blender-assets/manifests/east-blue-2d.json
         blender-assets/contracts/east-blue-saga.simulation.json
         blender-assets/runtime/east-blue-2d/**
         canon/east_blue_scene_anchors.json + data/canon.json (anchor resolution)
Output   public/art/east-blue-2d/<slug>/atlas.png
         data/generated/east_blue_simulations.json

Run: python3 scripts/sync_east_blue_2d.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "blender-assets"
OUT_DIR = ROOT / "public" / "art" / "east-blue-2d"
OUT_JSON = ROOT / "data" / "generated" / "east_blue_simulations.json"
ANCHORS_JSON = ROOT / "canon" / "east_blue_scene_anchors.json"
CANON_JSON = ROOT / "data" / "canon.json"

ATLAS_W, ATLAS_H = 1152, 768
GRID_COLS, GRID_ROWS, CELL_PX = 3, 2, 384


class DataError(Exception):
    pass


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def signed_file(entry: dict, what: str) -> Path:
    """Resolve a manifest {path, bytes, sha256} entry and verify the signature."""
    p = ASSETS / entry["path"]
    if not p.exists():
        raise DataError(f"{what}: file missing: {entry['path']}")
    size = p.stat().st_size
    if size != entry["bytes"]:
        raise DataError(f"{what}: {entry['path']} is {size} bytes, manifest says {entry['bytes']}")
    if sha256(p) != entry["sha256"]:
        raise DataError(f"{what}: {entry['path']} bytes do not match the manifest's sha256")
    return p


def png_size(p: Path) -> tuple[int, int]:
    """Width/height from the IHDR chunk. We only ever READ these bytes."""
    b = p.read_bytes()
    if b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
        raise DataError(f"{p.name} is not a png")
    w, h = struct.unpack(">II", b[16:24])
    return w, h


def main() -> int:
    manifest_path = ASSETS / "manifests" / "east-blue-2d.json"
    manifest = json.loads(manifest_path.read_text())

    if manifest.get("schema_version") != 1:
        raise DataError(f"east-blue-2d.json is schema_version {manifest.get('schema_version')!r}; this script reads 1")
    if manifest.get("state") != "runtime_verified":
        raise DataError(f"manifest state is {manifest.get('state')!r}, not runtime_verified — the pack is not promoted")

    contract_path = signed_file(manifest["contract"], "contract")
    signed_file(manifest["character_index"], "character_index")
    contract = json.loads(contract_path.read_text())
    if contract.get("schema_version") != 1:
        raise DataError(f"simulation contract is schema_version {contract.get('schema_version')!r}; this script reads 1")

    # Every character package: verify both files, load frame metadata.
    assets: dict[str, dict] = {}
    atlas_sources: dict[str, Path] = {}
    for ch in manifest["characters"]:
        cid = ch["id"]
        atlas_p = signed_file(ch["atlas"], f"characters[{cid}].atlas")
        meta_p = signed_file(ch["metadata"], f"characters[{cid}].metadata")
        w, h = png_size(atlas_p)
        if (w, h) != (ATLAS_W, ATLAS_H):
            raise DataError(f"{cid}: atlas is {w}x{h}, expected {ATLAS_W}x{ATLAS_H}")
        meta = json.loads(meta_p.read_text())
        grid = meta.get("grid") or {}
        if (grid.get("columns"), grid.get("rows"), grid.get("cell_px")) != (GRID_COLS, GRID_ROWS, CELL_PX):
            raise DataError(f"{cid}: grid {grid} is not the {GRID_COLS}x{GRID_ROWS}@{CELL_PX} contract")
        if meta.get("atlas_sha256") != ch["atlas"]["sha256"]:
            raise DataError(f"{cid}: character.json atlas_sha256 disagrees with the manifest")
        frames = {}
        for pose, f in meta["frames"].items():
            col, row = f["index"] % GRID_COLS, f["index"] // GRID_COLS
            # The col/row derivation must agree with the authored pixel_rect —
            # if it ever doesn't, the atlas was packed differently than indexed.
            if (f["pixel_rect"]["x"], f["pixel_rect"]["y"]) != (col * CELL_PX, row * CELL_PX):
                raise DataError(f"{cid}: frame {pose!r} index {f['index']} disagrees with its pixel_rect")
            frames[pose] = {"col": col, "row": row, "pivot": f["pivot"]}
        assets[cid] = {
            "url": f"/art/east-blue-2d/{cid}/atlas.png",
            "sha256": ch["atlas"]["sha256"],
            "kind": ch["kind"],
            "variant": ch["variant"],
            "map_height": meta["map_height"],
            "grid": {"columns": GRID_COLS, "rows": GRID_ROWS, "cell_px": CELL_PX},
            "frames": frames,
            "runtime_rules": meta.get("runtime_rules") or {},
        }
        atlas_sources[cid] = atlas_p

    # Anchor resolution inputs. The anchor table is HAND-AUTHORED (canon/ door);
    # the coordinates it resolves to are canon.json's own.
    anchors = json.loads(ANCHORS_JSON.read_text())["anchors"]
    canon = json.loads(CANON_JSON.read_text())
    ev_pos = {e["slug"]: (e["lng"], e["lat"]) for e in canon["events"]}
    isl_pos = {
        i["slug"]: (i["lng"], i["lat"])
        for i in canon["islands"]
        if isinstance(i.get("lng"), (int, float)) and isinstance(i.get("lat"), (int, float))
    }

    def resolve_anchor(sid: str) -> dict:
        a = anchors.get(sid)
        if a is None:
            raise DataError(f"{sid}: shipped scene has no anchor in canon/east_blue_scene_anchors.json")
        if "event" in a:
            if a["event"] not in ev_pos:
                raise DataError(f"{sid}: anchor event {a['event']!r} is not a canon event")
            lng, lat = ev_pos[a["event"]]
            return {"kind": "event", "ref": a["event"], "lng": lng, "lat": lat}
        if "island" in a:
            if a["island"] not in isl_pos:
                raise DataError(f"{sid}: anchor island {a['island']!r} has no canon coordinate")
            lng, lat = isl_pos[a["island"]]
            return {"kind": "island", "ref": a["island"], "lng": lng, "lat": lat}
        if not isinstance(a.get("lng"), (int, float)) or not isinstance(a.get("lat"), (int, float)):
            raise DataError(f"{sid}: anchor is neither event, island, nor a literal lng/lat")
        return {"kind": "literal", "ref": None, "lng": a["lng"], "lat": a["lat"], "note": a.get("note")}

    # Scenes: runtime_ready ships, everything else is refused BY NAME.
    scenes, refused = [], []
    for sc in contract["scenes"]:
        sid = sc["id"]
        if sc.get("readiness") != "runtime_ready":
            refused.append({
                "id": sid,
                "readiness": sc.get("readiness"),
                "why": f"readiness is {sc.get('readiness')!r}, not runtime_ready",
                "missing_assets": sc.get("missing_assets") or [],
            })
            continue
        gate = sc.get("chapter_gate") or {}
        if gate.get("verification") != "verified":
            raise DataError(f"{sid}: runtime_ready but chapter gate is {gate.get('verification')!r}")
        start, end = gate.get("start"), gate.get("end")
        span = contract["chapter_span"]
        if not (isinstance(start, int) and isinstance(end, int) and span["start"] <= start <= end <= span["end"]):
            raise DataError(f"{sid}: chapter gate {start}..{end} outside the pack span {span}")
        for actor in sc["actors"]:
            asset = assets.get(actor["asset_id"])
            if asset is None:
                raise DataError(f"{sid}: actor {actor['id']!r} casts unknown asset {actor['asset_id']!r}")
            last_t = -1
            for kf in actor["keyframes"]:
                if kf["t"] <= last_t:
                    raise DataError(f"{sid}: actor {actor['id']!r} keyframes not strictly ascending at t={kf['t']}")
                last_t = kf["t"]
                if kf["t"] > sc["duration_ms"]:
                    raise DataError(f"{sid}: actor {actor['id']!r} keyframe t={kf['t']} beyond duration {sc['duration_ms']}")
                if kf["pose"] not in asset["frames"]:
                    raise DataError(f"{sid}: actor {actor['id']!r} pose {kf['pose']!r} not in {actor['asset_id']}'s atlas")
        for ev in sc.get("events") or []:
            if not (0 <= ev["t"] <= sc["duration_ms"]):
                raise DataError(f"{sid}: FX event t={ev['t']} outside 0..{sc['duration_ms']}")
        row = {k: sc[k] for k in (
            "id", "label", "arc_id", "type", "priority", "chapter_gate",
            "place", "duration_ms", "actors", "events",
        )}
        row["anchor"] = resolve_anchor(sid)
        scenes.append(row)

    ready_ids = {s["id"] for s in scenes}
    expected = manifest["metrics"]
    if len(scenes) != expected["runtime_ready_scenes"] or len(refused) != expected["art_partial_scenes"]:
        raise DataError(
            f"scene split {len(scenes)}/{len(refused)} disagrees with the manifest's "
            f"{expected['runtime_ready_scenes']}/{expected['art_partial_scenes']}"
        )

    # Copy the signed atlases. All of them: the cast of a ready scene is the
    # index's business, and a partial-art scene's EXISTING actors still ship
    # (smoker, gol-d-roger appear in ready contexts and future replays).
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for cid, src in atlas_sources.items():
        dst = OUT_DIR / cid / "atlas.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    payload = {
        "_meta": {
            "generator": "scripts/sync_east_blue_2d.py",
            "schema_version": contract["schema_version"],
            "pack_id": contract["id"],
            "chapter_span": contract["chapter_span"],
            "source_manifest_sha256": sha256(manifest_path),
            "integration_ready": manifest.get("integration_ready", False),
            "feature_flag": "NEXT_PUBLIC_EAST_BLUE_2D_SIMULATIONS",
            "note": (
                "Only runtime_ready scenes with verified chapter gates ship. The refused "
                "list is load-bearing: check_simulations.py pins it so an art_partial "
                "scene cannot be re-enabled without new signed art."
            ),
            "counts": {"scenes": len(scenes), "refused": len(refused), "assets": len(assets)},
        },
        "arcs": contract["arcs"],
        "runtime_policy": contract["runtime_policy"],
        "scenes": scenes,
        "refused": refused,
        "assets": assets,
        "supersedes_visible_art": manifest.get("supersedes_visible_art") or [],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    for s in scenes:
        g = s["chapter_gate"]
        print(f"  scene   {s['id']:34} ch {g['start']:>3}  {len(s['actors'])} actors  {len(s['events'])} fx")
    for r in refused:
        print(f"  REFUSED {r['id']:34} {r['why']}  missing: {', '.join(r['missing_assets'])}")
    print(f"\n{len(scenes)} scenes, {len(refused)} refused, {len(assets)} atlases -> {OUT_JSON.relative_to(ROOT)}")
    if ready_ids and not manifest.get("integration_ready"):
        print("pack is runtime_verified but NOT integration_ready — the ch51 proof is the promotion gate")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as e:
        print(f"\nsync_east_blue_2d: {e}\n", file=sys.stderr)
        sys.exit(1)
